import json
import shutil

import pandas as pd
import pytest

from polymarker_common.catalog import BIOMARKER_KEYS


def spark_available() -> bool:
    try:
        import pyspark  # noqa: F401
    except ImportError:
        return False
    return shutil.which("java") is not None


def test_raw_zone_is_heterogeneous(small_settings):
    raw = small_settings.raw_dir
    csv_labs = {p.parent.name for p in raw.glob("lab_results/*/*.csv")}
    jsonl_labs = {p.parent.name for p in raw.glob("lab_results/*/*.jsonl")}
    assert len(csv_labs) == 4 and jsonl_labs == {"lab=riverside"}
    northside = pd.read_csv(next(raw.glob("lab_results/lab=northside/*.csv")), dtype=str)
    assert northside["raw_value"].str.contains(",").any()  # decimal commas
    units = pd.concat(pd.read_csv(p, dtype=str) for p in raw.glob("lab_results/*/*.csv"))[
        "raw_unit"
    ]
    assert {"ng/dL", "pmol/L"} <= set(units.dropna())  # conventional and SI
    assert len(list((raw / "pdf").glob("*.pdf"))) == 8


def test_holdout_is_separate_from_raw(small_settings):
    assert (small_settings.holdout_dir / "generator_params.json").exists()
    assert not list(small_settings.raw_dir.rglob("generator_params.json"))


def test_etl_outputs(small_settings, etl_summary):
    s = small_settings
    assert etl_summary["gold_patients"] == 3000
    totals = etl_summary["audit_totals"]
    assert totals["duplicates_removed"] > 0
    assert totals["unit_inferred"] > 0
    silver = pd.read_parquet(s.lake_dir / "silver" / "biomarkers")
    assert set(silver["marker"]) == set(BIOMARKER_KEYS)
    assert not silver.duplicated(["report_id", "marker"]).any()
    ft4 = silver[(silver["marker"] == "FT4") & ~silver["implausible"]]["value_si"]
    assert 8 < ft4.median() < 25  # all converted to pmol/L despite ng/dL sources
    gold = pd.read_parquet(s.lake_dir / "gold" / "patient_features")
    assert gold["patient_id"].is_unique
    answered = gold["fatigue_severity"].dropna()
    assert len(answered) > 0.95 * len(gold) and answered.between(1, 10).all()
    assert set(gold["brain_fog_frequency"].dropna()) <= {
        "never",
        "rarely",
        "sometimes",
        "often",
        "always",
    }
    stats = json.loads((s.lake_dir / "audit" / "population_stats.json").read_text())
    assert set(stats) == set(BIOMARKER_KEYS)


def test_decimal_misreads_are_flagged(small_settings, etl_summary):
    silver = pd.read_parquet(small_settings.lake_dir / "silver" / "biomarkers")
    suspects = silver[silver["decimal_misread_suspect"]]
    injected = json.loads((small_settings.raw_dir / "_generation_summary.json").read_text())[
        "lab_rows"
    ]["decimal_misreads"]
    # most injected x10 misreads are caught (some land inside plausible limits by chance)
    assert len(suspects) >= 0.5 * injected


@pytest.mark.skipif(not spark_available(), reason="pyspark/java not available")
def test_spark_and_duckdb_produce_identical_silver(small_settings, etl_summary, tmp_path):
    from dataclasses import replace

    from bda_engine.etl.engine import get_engine
    from bda_engine.etl.lake import run_etl

    s2 = replace(small_settings, etl_engine="spark", data_dir=tmp_path / "data")
    shutil.copytree(small_settings.raw_dir, s2.raw_dir)
    engine = get_engine("spark")
    try:
        spark_summary = run_etl(engine, s2)
    finally:
        engine.close()
    assert spark_summary["audit_totals"] == etl_summary["audit_totals"]
    cols = ["report_id", "marker", "value_si", "unit_inferred", "implausible"]
    a = (
        pd.read_parquet(small_settings.lake_dir / "silver" / "biomarkers")[cols]
        .sort_values(cols[:2])
        .reset_index(drop=True)
    )
    b = (
        pd.read_parquet(s2.lake_dir / "silver" / "biomarkers")[cols]
        .sort_values(cols[:2])
        .reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(a, b, check_dtype=False, atol=1e-9)
