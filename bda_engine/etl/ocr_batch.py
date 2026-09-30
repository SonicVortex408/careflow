"""Distributed OCR: parse a directory of lab-report PDFs into the lake.

    ETL_ENGINE=spark  -> PDFs are spread over Spark partitions (mapPartitions);
                         each executor runs the shared ingestion pipeline.
    ETL_ENGINE=duckdb -> a local multiprocessing pool does the same work.

Writes lake/extracted/pdf_metadata and lake/extracted/biomarkers (Parquet).
The per-document function is exactly the one the online Celery worker runs, so
batch and per-upload extraction cannot diverge.
"""

from __future__ import annotations

import hashlib
import os
import time
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from bda_engine.config import Settings


def process_pdf(path_str: str) -> tuple[dict, list[dict]]:
    from polymarker_common.pipeline import ingest_document

    path = Path(path_str)
    t0 = time.perf_counter()
    data = path.read_bytes()
    report_id = path.stem
    try:
        out = ingest_document(path)
        error = None
    except Exception as exc:  # noqa: BLE001 - one bad document must not stop the batch
        out, error = None, f"{type(exc).__name__}: {exc}"
    meta = {
        "report_id": report_id,
        "path": str(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "pages": out["ocr"]["pages"] if out else 0,
        "ocr_method": out["ocr"]["method"] if out else "error",
        "mean_confidence": out["ocr"]["mean_confidence"] if out else 0.0,
        "completeness": out["quality"]["completeness"] if out else 0.0,
        "quality_issues": sum(1 for i in out["quality"]["issues"] if i["severity"] != "info")
        if out
        else 0,
        "seconds": round(time.perf_counter() - t0, 3),
        "error": error,
    }
    rows = []
    for b in (out or {}).get("biomarkers", []):
        rows.append(
            {
                "report_id": report_id,
                "marker": b["key"],
                "loinc": b["loinc"],
                "raw_label": b["raw_label"],
                "raw_value": b["raw_value"],
                "raw_unit": b["raw_unit"],
                "value_si": b["value"],
                "unit_si": b["unit"],
                "confidence": b["confidence"],
                "ocr_method": meta["ocr_method"],
            }
        )
    return meta, rows


def _spark_run(paths: list[str], master: str) -> tuple[list[dict], list[dict]]:
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.master(master)
        .appName("polymarker-ocr")
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    n_parts = max(1, min(len(paths), spark.sparkContext.defaultParallelism * 4))
    results = (
        spark.sparkContext.parallelize(paths, n_parts)
        .mapPartitions(lambda it: [process_pdf(p) for p in it])
        .collect()
    )
    spark.stop()
    return [m for m, _ in results], [r for _, rows in results for r in rows]


def run_ocr_batch(s: Settings, limit: int | None = None) -> dict:
    pdf_dir = s.raw_dir / "pdf"
    paths = sorted(str(p) for p in pdf_dir.glob("*.pdf"))[:limit]
    t0 = time.perf_counter()
    if s.etl_engine == "spark":
        metas, rows = _spark_run(paths, s.spark_master)
    else:
        with Pool(processes=os.cpu_count() or 2) as pool:
            results = pool.map(process_pdf, paths, chunksize=4)
        metas = [m for m, _ in results]
        rows = [r for _, rs in results for r in rs]
    elapsed = time.perf_counter() - t0

    out_dir = s.lake_dir / "extracted"
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_df = pd.DataFrame(metas)
    rows_df = pd.DataFrame(rows)
    meta_df.to_parquet(out_dir / "pdf_metadata.parquet", index=False)
    rows_df.to_parquet(out_dir / "biomarkers.parquet", index=False)
    return {
        "engine": s.etl_engine,
        "documents": len(paths),
        "errors": int(meta_df["error"].notna().sum()) if len(meta_df) else 0,
        "rows_extracted": len(rows_df),
        "methods": meta_df["ocr_method"].value_counts().to_dict() if len(meta_df) else {},
        "seconds": round(elapsed, 1),
        "docs_per_second": round(len(paths) / elapsed, 2) if elapsed else None,
    }
