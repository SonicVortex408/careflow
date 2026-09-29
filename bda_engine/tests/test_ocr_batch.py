import json
import shutil

import pandas as pd
import pytest


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_batch_ocr_matches_ground_truth(small_settings):
    from bda_engine.etl.ocr_batch import run_ocr_batch

    summary = run_ocr_batch(small_settings)
    assert summary["documents"] == 8 and summary["errors"] == 0
    rows = pd.read_parquet(small_settings.lake_dir / "extracted" / "biomarkers.parquet")
    truth = [
        json.loads(line) for line in open(small_settings.holdout_dir / "pdf_ground_truth.jsonl")
    ]
    hits = total = 0
    for doc in truth:
        got = rows[rows["report_id"] == doc["report_id"]].set_index("marker")["value_si"]
        for r in doc["rows"]:
            total += 1
            if (
                r["key"] in got
                and abs(got[r["key"]] - r["value_si"]) <= 0.01 * abs(r["value_si"]) + 1e-6
            ):
                hits += 1
    assert hits / total >= 0.85
