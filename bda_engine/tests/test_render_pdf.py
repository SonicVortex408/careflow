"""
Week 1 Step 1.3 acceptance: every layout renders a real PDF with
extractable text carrying every printed value, and build_printed_rows
correctly round-trips canonical -> printed-unit -> (implicitly)
recoverable-canonical, which is the ground truth the OCR/normalization
pipeline (Weeks 2-3) will be scored against.
"""

import random

import numpy as np
import pdfplumber
import pytest

from bda_engine.generate.distributions import PHENOTYPES, sample_markers
from bda_engine.generate.render_pdf import LAYOUTS, build_printed_rows, render_report_pdf
from bda_engine.reference_data import load_biomarkers, load_unit_conversions


@pytest.fixture
def sample_values():
    rng = np.random.default_rng(1)
    values = sample_markers(PHENOTYPES["overt_hypothyroid_autoimmune"], "female", rng)
    return {k.value: v for k, v in values.items()}


class TestBuildPrintedRows:
    def test_all_nine_biomarkers_present_by_default(self, sample_values):
        rows = build_printed_rows(sample_values, random.Random(1))
        assert {r.biomarker_key for r in rows} == set(sample_values.keys())

    def test_max_rows_subsets_the_panel(self, sample_values):
        rows = build_printed_rows(sample_values, random.Random(1), max_rows=3)
        assert len(rows) == 3

    def test_printed_value_converts_back_to_canonical(self, sample_values):
        biomarkers = load_biomarkers()
        rows = build_printed_rows(sample_values, random.Random(2))
        conversions = {
            (r.biomarker_key, r.from_unit): r.factor
            for r in load_unit_conversions()
        }
        for row in rows:
            factor = conversions[(row.biomarker_key, row.unit_raw)]
            recovered_canonical = row.value_printed_numeric * factor
            assert recovered_canonical == pytest.approx(row.value_canonical, rel=1e-6)
            assert row.unit_canonical == biomarkers[row.biomarker_key].canonical_unit

    def test_loinc_code_matches_reference_data(self, sample_values):
        biomarkers = load_biomarkers()
        rows = build_printed_rows(sample_values, random.Random(3))
        for row in rows:
            assert row.loinc_code == biomarkers[row.biomarker_key].loinc_code

    def test_reproducible_with_same_random_seed(self, sample_values):
        rows1 = build_printed_rows(sample_values, random.Random(99))
        rows2 = build_printed_rows(sample_values, random.Random(99))
        assert [r.analyte_name_raw for r in rows1] == [r.analyte_name_raw for r in rows2]
        assert [r.unit_raw for r in rows1] == [r.unit_raw for r in rows2]


class TestRenderReportPdf:
    @pytest.mark.parametrize("layout", LAYOUTS)
    def test_every_layout_renders_a_readable_pdf(self, tmp_path, sample_values, layout):
        rows = build_printed_rows(sample_values, random.Random(42), max_rows=6)
        out_path = tmp_path / f"{layout}.pdf"

        pages = render_report_pdf(
            out_path=out_path, document_id="doc-1", patient_id="pat-1",
            lab_provider_name="Meridian Health Labs", patient_age_years=45.0,
            patient_sex="female", rows=rows, layout=layout, accession_no="ACC-1",
        )

        assert out_path.exists()
        assert out_path.stat().st_size > 0
        assert pages >= 1

        with pdfplumber.open(out_path) as pdf:
            assert len(pdf.pages) == pages
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        assert "Meridian Health Labs" in full_text
        # Every printed value must actually be readable on the page --
        # this is the ground-truth contract the OCR pipeline is scored
        # against.
        for row in rows:
            assert row.value_raw in full_text, (
                f"{layout}: {row.value_raw!r} for {row.biomarker_key} not found in extracted text"
            )

    def test_unknown_layout_raises(self, tmp_path, sample_values):
        rows = build_printed_rows(sample_values, random.Random(1), max_rows=2)
        with pytest.raises(ValueError, match="Unknown layout"):
            render_report_pdf(
                out_path=tmp_path / "x.pdf", document_id="d", patient_id="p",
                lab_provider_name="X", patient_age_years=30.0, patient_sex="male",
                rows=rows, layout="not_a_real_layout", accession_no="A",
            )
