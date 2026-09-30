"""Pluggable SQL engine: PySpark (distributed) or DuckDB (single node).

The ETL is written once as SQL. The only dialect differences we need are
wrapped in small helpers (``regex_replace_all``, ``quantile``); everything else
(TRY_CAST, window functions, struct field access, regexp_extract, ln/exp) is
portable between Spark SQL 3.5+/4.x and DuckDB 1.x.

    ETL_ENGINE=spark   # Spark local[*] or SPARK_MASTER=spark://...
    ETL_ENGINE=duckdb  # default: fast local dev / CI
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

LAB_COLUMNS = (
    "report_id",
    "patient_id",
    "lab_provider",
    "collected_at",
    "raw_label",
    "raw_value",
    "raw_unit",
    "raw_reference",
    "flag",
)
INTAKE_DDL_SPARK = (
    "form_id STRING, report_id STRING, patient_id STRING, submitted_at STRING, "
    "answers STRUCT<fatigue: STRING, brain_fog: STRING, hair_loss: STRING>"
)
INTAKE_COLUMNS_DUCKDB = {
    "form_id": "VARCHAR",
    "report_id": "VARCHAR",
    "patient_id": "VARCHAR",
    "submitted_at": "VARCHAR",
    "answers": "STRUCT(fatigue VARCHAR, brain_fog VARCHAR, hair_loss VARCHAR)",
}


class Engine(ABC):
    name: str

    @abstractmethod
    def read_csv(self, view: str, pattern: str) -> None: ...

    @abstractmethod
    def read_lab_jsonl(self, view: str, pattern: str) -> None: ...

    @abstractmethod
    def read_intake_jsonl(self, view: str, pattern: str) -> None: ...

    @abstractmethod
    def read_parquet(self, view: str, path: str) -> None: ...

    @abstractmethod
    def register_pandas(self, view: str, df: pd.DataFrame) -> None: ...

    @abstractmethod
    def sql(self, view: str, query: str, *, persist: bool = False) -> None: ...

    @abstractmethod
    def write_parquet(
        self, view: str, path: Path, partition_by: list[str] | None = None
    ) -> None: ...

    @abstractmethod
    def to_pandas(self, query: str) -> pd.DataFrame: ...

    @abstractmethod
    def regex_replace_all(self, expr: str, pattern: str, replacement: str) -> str: ...

    @abstractmethod
    def quantile(self, expr: str, q: float) -> str: ...

    def count(self, view: str) -> int:
        return int(self.to_pandas(f"SELECT COUNT(*) AS n FROM {view}")["n"].iloc[0])

    def close(self) -> None:  # pragma: no cover - trivial
        return None

    @staticmethod
    def _clear(path: Path) -> None:
        if path.exists():
            shutil.rmtree(path)
        path.parent.mkdir(parents=True, exist_ok=True)


class DuckDBEngine(Engine):
    name = "duckdb"

    def __init__(self, threads: int | None = None):
        import duckdb

        self.con = duckdb.connect()
        if threads:
            self.con.execute(f"SET threads={int(threads)}")

    def read_csv(self, view, pattern):
        self.con.execute(
            f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_csv('{pattern}', header=true, "
            "all_varchar=true, union_by_name=true, hive_partitioning=false)"
        )

    def read_lab_jsonl(self, view, pattern):
        cols = ", ".join(f"'{c}': 'VARCHAR'" for c in LAB_COLUMNS)
        self.con.execute(
            f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_json('{pattern}', "
            f"format='newline_delimited', columns={{{cols}}})"
        )

    def read_intake_jsonl(self, view, pattern):
        cols = ", ".join(f"'{k}': '{v}'" for k, v in INTAKE_COLUMNS_DUCKDB.items())
        self.con.execute(
            f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_json('{pattern}', "
            f"format='newline_delimited', columns={{{cols}}})"
        )

    def read_parquet(self, view, path):
        self.con.execute(
            f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet('{path}/**/*.parquet', hive_partitioning=true)"
        )

    def register_pandas(self, view, df):
        self.con.register(f"{view}__df", df)
        self.con.execute(f"CREATE OR REPLACE TABLE {view} AS SELECT * FROM {view}__df")

    def sql(self, view, query, *, persist=False):
        kind = "TABLE" if persist else "VIEW"
        self.con.execute(f"CREATE OR REPLACE {kind} {view} AS {query}")

    def write_parquet(self, view, path, partition_by=None):
        self._clear(path)
        if partition_by:
            cols = ", ".join(partition_by)
            self.con.execute(
                f"COPY (SELECT * FROM {view}) TO '{path}' (FORMAT PARQUET, PARTITION_BY ({cols}))"
            )
        else:
            path.mkdir(parents=True, exist_ok=True)
            self.con.execute(
                f"COPY (SELECT * FROM {view}) TO '{path}/part-0.parquet' (FORMAT PARQUET)"
            )

    def to_pandas(self, query):
        return self.con.execute(query).df()

    def regex_replace_all(self, expr, pattern, replacement):
        return f"regexp_replace({expr}, '{pattern}', '{replacement}', 'g')"

    def quantile(self, expr, q):
        return f"quantile_cont({expr}, {q})"

    def close(self):
        self.con.close()


class SparkEngine(Engine):
    name = "spark"

    def __init__(self, master: str = "local[*]", app_name: str = "polymarker-bda"):
        from pyspark.sql import SparkSession

        self.spark = (
            SparkSession.builder.master(master)
            .appName(app_name)
            .config("spark.ui.enabled", "false")
            .config("spark.ui.showConsoleProgress", "false")
            .config("spark.sql.shuffle.partitions", "16")
            .config("spark.sql.execution.arrow.pyspark.enabled", "true")
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.driver.memory", "3g")
            .getOrCreate()
        )
        self.spark.sparkContext.setLogLevel("ERROR")

    def read_csv(self, view, pattern):
        df = self.spark.read.option("header", True).option("inferSchema", False).csv(pattern)
        df.createOrReplaceTempView(view)

    def read_lab_jsonl(self, view, pattern):
        ddl = ", ".join(f"{c} STRING" for c in LAB_COLUMNS)
        self.spark.read.schema(ddl).json(pattern).createOrReplaceTempView(view)

    def read_intake_jsonl(self, view, pattern):
        self.spark.read.schema(INTAKE_DDL_SPARK).json(pattern).createOrReplaceTempView(view)

    def read_parquet(self, view, path):
        self.spark.read.parquet(str(path)).createOrReplaceTempView(view)

    def register_pandas(self, view, df):
        self.spark.createDataFrame(df).createOrReplaceTempView(view)

    def sql(self, view, query, *, persist=False):
        df = self.spark.sql(query)
        if persist:
            df = df.cache()
        df.createOrReplaceTempView(view)

    def write_parquet(self, view, path, partition_by=None):
        self._clear(path)
        writer = self.spark.table(view).write.mode("overwrite")
        if partition_by:
            writer = writer.partitionBy(*partition_by)
        writer.parquet(str(path))

    def to_pandas(self, query):
        return self.spark.sql(query).toPandas()

    def regex_replace_all(self, expr, pattern, replacement):
        return f"regexp_replace({expr}, '{pattern}', '{replacement}')"

    def quantile(self, expr, q):
        return f"percentile_approx({expr}, {q}, 10000)"

    def close(self):
        self.spark.stop()


def get_engine(name: str, spark_master: str = "local[*]") -> Engine:
    if name == "spark":
        return SparkEngine(spark_master)
    if name == "duckdb":
        return DuckDBEngine()
    raise ValueError(f"Unknown ETL engine: {name}")
