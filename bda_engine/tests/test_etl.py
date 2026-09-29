"""
Week 1 Step 1.4 (ETL engine facade) and Week 3 Step 3.5 (feature
vectors) acceptance, exercised against real generator output.
"""

import duckdb
import pandas as pd
import pytest

from bda_engine.etl.engine import DuckDBEngine, get_engine
from bda_engine.etl.silver_to_gold import BIOMARKER_ORDER, pivot_to_feature_vectors
from bda_engine.generate.generate_synthetic_data import generate
from bda_engine.schemas.common import BiomarkerKey


@pytest.fixture(scope="module")
def observations_df(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("data_lake")
    generate(patients=25, pdf_count=0, seed=11, out_dir=out_dir, scan_fraction=0.0)

    con = duckdb.connect()
    glob = str(out_dir / "gold" / "biomarker_observations" / "**" / "*.parquet")
    return con.execute(f"SELECT * FROM read_parquet('{glob}', hive_partitioning=true)").df()


class TestGetEngine:
    def test_default_engine_is_duckdb(self, monkeypatch):
        monkeypatch.delenv("ETL_ENGINE", raising=False)
        engine = get_engine()
        assert isinstance(engine, DuckDBEngine)

    def test_explicit_duckdb(self):
        assert isinstance(get_engine("duckdb"), DuckDBEngine)

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown ETL_ENGINE"):
            get_engine("not_a_real_engine")

    def test_env_var_selects_engine(self, monkeypatch):
        monkeypatch.setenv("ETL_ENGINE", "duckdb")
        assert isinstance(get_engine(), DuckDBEngine)


class TestDuckDBEngineRoundTrip:
    def test_write_then_read_parquet(self, tmp_path):
        engine = DuckDBEngine()
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        out_path = tmp_path / "test.parquet"

        engine.write_parquet(df, out_path)
        result = engine.read_parquet(str(out_path))

        assert len(result) == 3
        assert set(result["a"]) == {1, 2, 3}

    def test_write_then_read_partitioned(self, tmp_path):
        engine = DuckDBEngine()
        df = pd.DataFrame({"a": [1, 2, 3, 4], "group": ["x", "x", "y", "y"]})
        out_dir = tmp_path / "partitioned"

        engine.write_parquet(df, out_dir, partition_cols=["group"])
        result = engine.read_parquet(str(out_dir / "**" / "*.parquet"))

        assert len(result) == 4
        assert set(result["group"].unique()) == {"x", "y"}


class TestPivotToFeatureVectors:
    def test_output_has_fixed_column_order(self, observations_df):
        result = pivot_to_feature_vectors(observations_df)

        expected_cols = ["patient_id", "observed_month"]
        for key in BIOMARKER_ORDER:
            expected_cols += [f"{key}_value", f"{key}_missing", f"{key}_zscore"]

        assert list(result.columns) == expected_cols

    def test_biomarker_order_matches_enum(self):
        assert BIOMARKER_ORDER == [k.value for k in BiomarkerKey]

    def test_one_row_per_patient_panel(self, observations_df):
        result = pivot_to_feature_vectors(observations_df)
        panels = observations_df[["patient_id", "observed_month"]].drop_duplicates()
        assert len(result) == len(panels)

    def test_no_missing_values_when_all_nine_present(self, observations_df):
        # The direct-synthetic generator always produces all 9 biomarkers
        # per patient (no missingness applied at that stage).
        result = pivot_to_feature_vectors(observations_df)
        for key in BIOMARKER_ORDER:
            assert not result[f"{key}_missing"].any(), key
            assert result[f"{key}_value"].notna().all(), key

    def test_zscore_has_zero_mean_across_cohort(self, observations_df):
        result = pivot_to_feature_vectors(observations_df)
        for key in BIOMARKER_ORDER:
            mean_z = result[f"{key}_zscore"].mean()
            assert abs(mean_z) < 0.5, f"{key}: mean z-score {mean_z} too far from 0"

    def test_missing_biomarker_produces_none_value_and_true_flag(self):
        obs = pd.DataFrame([
            {"patient_id": "P1", "biomarker_key": "TSH", "value_canonical": 2.0,
             "observed_month": "2026-01-01", "quality_status": "ok"},
            {"patient_id": "P1", "biomarker_key": "FT3", "value_canonical": 4.5,
             "observed_month": "2026-01-01", "quality_status": "ok"},
        ])
        result = pivot_to_feature_vectors(obs)
        assert len(result) == 1
        assert result.iloc[0]["TSH_value"] == 2.0
        assert bool(result.iloc[0]["TSH_missing"]) is False
        assert result.iloc[0]["FERRITIN_value"] is None
        assert bool(result.iloc[0]["FERRITIN_missing"]) is True

    def test_suspect_and_rejected_rows_excluded(self):
        obs = pd.DataFrame([
            {"patient_id": "P1", "biomarker_key": "TSH", "value_canonical": 2.0,
             "observed_month": "2026-01-01", "quality_status": "ok"},
            {"patient_id": "P1", "biomarker_key": "FT3", "value_canonical": 9999.0,
             "observed_month": "2026-01-01", "quality_status": "rejected"},
        ])
        result = pivot_to_feature_vectors(obs)
        assert len(result) == 1
        # FT3 was rejected -> must appear as missing, not as 9999.0.
        assert result.iloc[0]["FT3_value"] is None
        assert bool(result.iloc[0]["FT3_missing"]) is True

    def test_missing_required_column_raises(self):
        obs = pd.DataFrame([{"patient_id": "P1"}])
        with pytest.raises(ValueError, match="missing required columns"):
            pivot_to_feature_vectors(obs)

    def test_empty_input_returns_empty_with_correct_columns(self):
        obs = pd.DataFrame(columns=[
            "patient_id", "biomarker_key", "value_canonical", "observed_month", "quality_status",
        ])
        result = pivot_to_feature_vectors(obs)
        assert len(result) == 0
        assert "TSH_value" in result.columns
