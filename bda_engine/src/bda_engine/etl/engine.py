"""
Week 1, Step 1.4: ETL engine facade.

Dispatches table reads/writes to DuckDB (default) or PySpark
(ETL_ENGINE=spark, needs `uv sync --extra spark`), per
ARCHITECTURE.md decision 5: 50k rows does not need a cluster, but a
PySpark path is part of the Big Data brief, so both exist behind one
interface and either can read the other's Parquet output (both write
plain Hive-partitioned Parquet via pyarrow/the Spark Parquet writer --
neither uses an engine-specific format).

DuckDB is the default and the one actually exercised by this project's
test suite; the Spark path is here so the option exists (`pyspark` is
an optional extra, not a core dependency, to keep the default install
light and JVM-free) but is not verified by CI in this environment (no
JVM was available during this build -- see
docs/WEEKS_1-3_STATUS_AND_PLAN.md's verification-environment note).
"""

import os
from pathlib import Path
from typing import Protocol

import duckdb
import pandas as pd


class Engine(Protocol):
    def read_parquet(self, glob_or_path: str) -> pd.DataFrame: ...
    def write_parquet(
        self, df: pd.DataFrame, out_path: Path, partition_cols: list[str] | None = None
    ) -> None: ...


class DuckDBEngine:
    def __init__(self):
        self._con = duckdb.connect()

    def read_parquet(self, glob_or_path: str) -> pd.DataFrame:
        return self._con.execute(
            f"SELECT * FROM read_parquet('{glob_or_path}', hive_partitioning=true)"
        ).df()

    def write_parquet(
        self, df: pd.DataFrame, out_path: Path, partition_cols: list[str] | None = None
    ) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if partition_cols:
            out_path.mkdir(parents=True, exist_ok=True)
            df.to_parquet(out_path, index=False, partition_cols=partition_cols)
        else:
            df.to_parquet(out_path, index=False)


class SparkEngine:
    """Requires `uv sync --extra spark` (pulls PySpark + a JVM
    dependency). Not exercised by this project's test suite -- no JVM
    was available in the environment this was built in. Kept import-
    lazy (pyspark is imported inside __init__, not at module level) so
    importing this module never requires pyspark to be installed."""

    def __init__(self):
        try:
            from pyspark.sql import SparkSession
        except ImportError as e:
            raise ImportError(
                "ETL_ENGINE=spark requires the 'spark' extra: "
                "uv sync --extra spark"
            ) from e

        self._spark = SparkSession.builder.appName("bda_engine").getOrCreate()

    def read_parquet(self, glob_or_path: str) -> pd.DataFrame:
        return self._spark.read.parquet(glob_or_path).toPandas()

    def write_parquet(
        self, df: pd.DataFrame, out_path: Path, partition_cols: list[str] | None = None
    ) -> None:
        spark_df = self._spark.createDataFrame(df)
        writer = spark_df.write.mode("overwrite")
        if partition_cols:
            writer = writer.partitionBy(*partition_cols)
        writer.parquet(str(out_path))


def get_engine(engine_name: str | None = None) -> Engine:
    """engine_name: "duckdb" (default) or "spark". Falls back to the
    ETL_ENGINE env var, then "duckdb"."""

    name = engine_name or os.getenv("ETL_ENGINE", "duckdb")
    if name == "duckdb":
        return DuckDBEngine()
    if name == "spark":
        return SparkEngine()
    raise ValueError(f"Unknown ETL_ENGINE: {name!r} (expected 'duckdb' or 'spark')")
