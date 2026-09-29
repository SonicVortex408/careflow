"""
Week 2 + Week 3 integration acceptance: the full pipeline (OCR extract
-> table reconstruct -> normalize -> convert units -> parse ranges ->
quality check), run end to end on a real generator PDF and compared
against its ground truth.

This is the capstone test for Weeks 2-3: everything below it (router,
text_layer, table_reconstruct, field_extract, normalizer, units,
ref_range, data_quality) is unit-tested elsewhere; this file proves
they work correctly *together*.
"""

import pytest

from app.ocr.pipeline import UnsupportedDocumentError, process_document


class TestProcessDocumentTextLayer:
    def test_recovers_correct_biomarker_and_canonical_value_for_every_row(self, clean_pdf_factory):
        path, ground_truth_rows = clean_pdf_factory(layout="boxed_table", max_rows=6)
        result = process_document(path, document_id="doc-1", patient_id="pat-1")

        assert result.has_text_layer is True
        assert len(result.observations) == len(ground_truth_rows)

        by_value_raw = {obs.value_raw: obs for obs in result.observations}
        for gt_row in ground_truth_rows:
            obs = by_value_raw.get(gt_row.value_raw)
            assert obs is not None, f"no observation recovered for {gt_row.value_raw!r}"

            assert obs.biomarker_key == gt_row.biomarker_key, (
                f"{gt_row.analyte_name_raw!r}: expected {gt_row.biomarker_key}, "
                f"got {obs.biomarker_key} (method={obs.mapping_method})"
            )
            assert obs.loinc_code == gt_row.loinc_code
            # rel=0.01, not tighter: render_pdf.py prints values rounded
            # to 2-3 significant figures (a real report has finite
            # printed precision too), so recovering the *unrounded*
            # internal float exactly is neither possible nor the right
            # bar -- recovering it to within print-rounding error is.
            assert obs.value_canonical == pytest.approx(gt_row.value_canonical, rel=0.01)
            assert obs.unit_canonical == gt_row.unit_canonical
            assert obs.mapping_method != "unmapped"
            # never rejected for clean synthetic data
            assert obs.quality_status in ("ok", "suspect")

    def test_extracts_patient_age_and_sex(self, clean_pdf_factory):
        path, _ = clean_pdf_factory()
        result = process_document(path, document_id="doc-1", patient_id="pat-1")
        assert result.patient_age == "45"
        assert result.patient_sex == "female"

    def test_extracts_lab_provider(self, clean_pdf_factory):
        path, _ = clean_pdf_factory()
        result = process_document(path, document_id="doc-1", patient_id="pat-1")
        assert result.lab_provider == "Meridian Health Labs"

    @pytest.mark.parametrize(
        "layout", ["single_column", "two_column", "borderless_table", "header_heavy", "multi_panel"]
    )
    def test_recovers_all_rows_across_every_layout(self, clean_pdf_factory, layout):
        path, ground_truth_rows = clean_pdf_factory(layout=layout, max_rows=6)
        result = process_document(path, document_id="doc-1", patient_id="pat-1")

        recovered_keys = {obs.biomarker_key for obs in result.observations}
        expected_keys = {r.biomarker_key for r in ground_truth_rows}
        missing = expected_keys - recovered_keys
        assert expected_keys <= recovered_keys, f"{layout}: missing {missing}"

    def test_no_rows_produces_a_warning_not_a_crash(self, tmp_path, clean_pdf_factory):
        # A document with zero data rows (e.g. a cover letter) should
        # process cleanly with an empty observation list and a warning,
        # never raise.
        from bda_engine.generate.render_pdf import render_report_pdf

        path = tmp_path / "empty.pdf"
        render_report_pdf(
            out_path=path, document_id="d", patient_id="p",
            lab_provider_name="Meridian Health Labs", patient_age_years=40.0,
            patient_sex="male", rows=[], layout="single_column", accession_no="A",
        )
        result = process_document(path, document_id="doc-empty", patient_id="pat-1")
        assert result.observations == []
        assert len(result.warnings) > 0


class TestProcessDocumentScanned:
    def test_scanned_document_without_tesseract_raises_unsupported(self, scanned_pdf_factory):
        from app.ocr.tesseract_engine import is_available

        if is_available().available:
            pytest.skip(
                "Tesseract is installed in this environment; "
                "this tests the missing-binary path."
            )

        scanned_path, _, _ = scanned_pdf_factory()
        with pytest.raises(UnsupportedDocumentError, match="Tesseract binary not available"):
            process_document(scanned_path, document_id="doc-s", patient_id="pat-1")

    def test_scanned_document_reports_has_text_layer_false(self, scanned_pdf_factory):
        # Even when it can't fully OCR (no Tesseract in this
        # environment), the router's classification itself is correct
        # and observable before the UnsupportedDocumentError is raised
        # -- verified via app/ocr/router.py directly (see
        # tests/test_ocr_router.py), not re-asserted here.
        from app.ocr.router import inspect_document

        scanned_path, _, _ = scanned_pdf_factory()
        assert inspect_document(scanned_path).has_text_layer is False
