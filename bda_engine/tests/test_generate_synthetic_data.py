"""
Week 1 Step 1.3 acceptance (docs/WEEKS_1-3_STATUS_AND_PLAN.md section 3.1):
end-to-end generation at small scale, verified by actually reading the
Parquet back with DuckDB (not just checking files exist) and by
validating the ground-truth JSON schema.

Full-scale (50k patients / 2000 documents) generation is not run in
this test suite -- it would take real wall-clock time and disk. This
suite proves the *pipeline* is correct at n=30; scaling it up is then
just changing --patients.
"""

import json

import duckdb
import pytest

from bda_engine.generate.generate_synthetic_data import generate
from bda_engine.reference_data import load_biomarkers


@pytest.fixture(scope="module")
def small_corpus(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("data_lake")
    summary = generate(patients=30, pdf_count=6, seed=7, out_dir=out_dir, scan_fraction=0.5)
    return out_dir, summary


class TestSummary:
    def test_counts_match_requested_scale(self, small_corpus):
        out_dir, summary = small_corpus
        assert summary["patients"] == 30
        assert summary["biomarker_observations"] == 30 * 9
        assert summary["prom_responses"] == 30
        # documents_rendered >= pdf_count (clean) and can be up to
        # 2x pdf_count (clean + scanned, probabilistic).
        assert 6 <= summary["documents_rendered"] <= 12

    def test_reproducible_with_same_seed(self, tmp_path_factory):
        out_a = tmp_path_factory.mktemp("a")
        out_b = tmp_path_factory.mktemp("b")
        summary_a = generate(patients=10, pdf_count=2, seed=99, out_dir=out_a, scan_fraction=0.5)
        summary_b = generate(patients=10, pdf_count=2, seed=99, out_dir=out_b, scan_fraction=0.5)
        assert summary_a["biomarker_observations"] == summary_b["biomarker_observations"]
        assert summary_a["documents_rendered"] == summary_b["documents_rendered"]


class TestParquetOutput:
    def test_patients_parquet_readable_by_duckdb(self, small_corpus):
        out_dir, _ = small_corpus
        con = duckdb.connect()
        df = con.execute(
            f"SELECT * FROM read_parquet('{out_dir / 'gold' / 'patients.parquet'}')"
        ).df()
        assert len(df) == 30
        assert set(df["sex"].unique()) <= {"male", "female"}
        assert df["is_synthetic"].all()

    def test_biomarker_observations_hive_partitioned_and_complete(self, small_corpus):
        out_dir, _ = small_corpus
        con = duckdb.connect()
        glob = str(out_dir / "gold" / "biomarker_observations" / "**" / "*.parquet")
        df = con.execute(
            f"SELECT * FROM read_parquet('{glob}', hive_partitioning=true)"
        ).df()

        assert len(df) == 30 * 9
        assert set(df["biomarker_key"].unique()) == set(load_biomarkers().keys())
        # Every row must have a real canonical value and unit.
        assert df["value_canonical"].notna().all()
        assert df["unit_canonical"].notna().all()
        assert (df["mapping_confidence"] == 1.0).all()
        assert (df["mapping_method"] == "exact").all()

    def test_prom_responses_parquet_has_all_three_items(self, small_corpus):
        out_dir, _ = small_corpus
        con = duckdb.connect()
        df = con.execute(
            f"SELECT * FROM read_parquet('{out_dir / 'silver' / 'prom_responses.parquet'}')"
        ).df()
        assert len(df) == 30
        for col in ("item_fatigue_severity", "item_brain_fog_frequency", "item_hair_loss"):
            assert col in df.columns
            assert df[col].notna().all()

    def test_raw_documents_has_text_layer_column_stays_boolean(self, small_corpus):
        # Partitioned by ingest_date, not has_text_layer -- a boolean
        # Hive partition value round-trips as the string "true"/"false"
        # (DuckDB and Spark both do this), which would silently change
        # its type. Keeping it a plain column avoids that.
        out_dir, summary = small_corpus
        con = duckdb.connect()
        glob = str(out_dir / "bronze" / "raw_documents" / "**" / "*.parquet")
        df = con.execute(
            f"SELECT * FROM read_parquet('{glob}', hive_partitioning=true)"
        ).df()
        assert len(df) == summary["documents_rendered"]
        assert df["has_text_layer"].dtype == bool
        assert set(df["has_text_layer"].unique()) <= {True, False}
        # At least one scanned (no text layer) doc, given scan_fraction=0.5
        # over 6 clean docs (probabilistically near-certain, seed fixed).
        assert (~df["has_text_layer"]).any()

    def test_raw_documents_partitioned_by_ingest_date(self, small_corpus):
        out_dir, _ = small_corpus
        partitions = list((out_dir / "bronze" / "raw_documents").glob("ingest_date=*"))
        assert len(partitions) >= 1


class TestGroundTruth:
    def test_one_ground_truth_file_per_rendered_document(self, small_corpus):
        out_dir, summary = small_corpus
        gt_dir = out_dir / "bronze" / "ground_truth"
        gt_files = list(gt_dir.glob("*.json"))
        assert len(gt_files) == summary["documents_rendered"]

    def test_ground_truth_json_has_required_fields(self, small_corpus):
        out_dir, _ = small_corpus
        gt_dir = out_dir / "bronze" / "ground_truth"
        biomarkers = load_biomarkers()

        for gt_file in gt_dir.glob("*.json"):
            payload = json.loads(gt_file.read_text(encoding="utf-8"))
            assert payload["document_id"]
            assert payload["patient_id"]
            assert isinstance(payload["has_text_layer"], bool)
            assert len(payload["rows"]) > 0

            for row in payload["rows"]:
                assert row["analyte_name_raw"]
                assert row["value_raw"]
                assert row["unit_raw"]
                key = row["true_biomarker_key"]
                assert key in biomarkers
                assert row["true_loinc_code"] == biomarkers[key].loinc_code
                assert row["true_unit_canonical"] == biomarkers[key].canonical_unit

    def test_scanned_and_clean_ground_truth_share_the_same_row_values(self, small_corpus):
        """A scanned document is a degraded RENDER of the same data, not
        different data -- its ground truth rows must describe exactly
        what the clean version printed."""
        out_dir, _ = small_corpus
        gt_dir = out_dir / "bronze" / "ground_truth"

        scanned_files = [p for p in gt_dir.glob("*S.json")]
        assert len(scanned_files) > 0

        for scanned_path in scanned_files:
            clean_id = scanned_path.stem[:-1]  # strip trailing "S"
            clean_path = gt_dir / f"{clean_id}.json"
            assert clean_path.exists()

            scanned = json.loads(scanned_path.read_text(encoding="utf-8"))
            clean = json.loads(clean_path.read_text(encoding="utf-8"))

            assert scanned["has_text_layer"] is False
            assert clean["has_text_layer"] is True
            scanned_values = [r["value_raw"] for r in scanned["rows"]]
            clean_values = [r["value_raw"] for r in clean["rows"]]
            assert scanned_values == clean_values


class TestRenderedFilesExist:
    def test_every_raw_document_row_points_at_a_real_file(self, small_corpus):
        out_dir, _ = small_corpus
        con = duckdb.connect()
        glob = str(out_dir / "bronze" / "raw_documents" / "**" / "*.parquet")
        df = con.execute(
            f"SELECT stored_uri, size_bytes FROM read_parquet('{glob}', hive_partitioning=true)"
        ).df()

        for _, row in df.iterrows():
            from pathlib import Path
            path = Path(row["stored_uri"])
            assert path.exists(), path
            assert path.stat().st_size == row["size_bytes"]
