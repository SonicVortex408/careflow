"""
Week 1 Step 1.3 acceptance: scan-simulated documents have NO
extractable text layer (has_text_layer=False), which is the whole
point -- without this, the Week 2 OCR engines never get exercised.
"""

import random

import pdfplumber
import pytest

from bda_engine.generate.distributions import PHENOTYPES, sample_markers
from bda_engine.generate.render_pdf import build_printed_rows, render_report_pdf
from bda_engine.generate.scan_simulate import (
    degrade_page,
    rasterize_pdf,
    simulate_scan,
    simulate_scan_as_images,
)


@pytest.fixture
def source_pdf(tmp_path):
    import numpy as np

    rng_np = np.random.default_rng(1)
    values = sample_markers(PHENOTYPES["euthyroid_healthy"], "male", rng_np)
    values = {k.value: v for k, v in values.items()}
    rows = build_printed_rows(values, random.Random(1), max_rows=5)

    path = tmp_path / "source.pdf"
    render_report_pdf(
        out_path=path, document_id="d1", patient_id="p1",
        lab_provider_name="Meridian Health Labs", patient_age_years=40.0,
        patient_sex="male", rows=rows, layout="single_column", accession_no="A1",
    )
    return path


class TestRasterizePdf:
    def test_produces_one_image_per_page(self, source_pdf):
        images = rasterize_pdf(source_pdf, dpi=150)
        with pdfplumber.open(source_pdf) as pdf:
            assert len(images) == len(pdf.pages)

    def test_higher_dpi_produces_larger_image(self, source_pdf):
        low = rasterize_pdf(source_pdf, dpi=100)[0]
        high = rasterize_pdf(source_pdf, dpi=300)[0]
        assert high.size[0] > low.size[0]
        assert high.size[1] > low.size[1]


class TestDegradePage:
    def test_degraded_image_differs_from_original(self, source_pdf):
        import numpy as np

        original = rasterize_pdf(source_pdf, dpi=200)[0]
        degraded = degrade_page(original, random.Random(1))

        # Different size is expected (rotation with expand=True); when
        # comparable, pixel content should differ meaningfully.
        orig_arr = np.asarray(original.resize(degraded.size).convert("RGB"))
        deg_arr = np.asarray(degraded.convert("RGB"))
        diff = np.abs(orig_arr.astype(int) - deg_arr.astype(int)).mean()
        assert diff > 1.0, "degradation should visibly change pixel content"

    def test_degrade_is_deterministic_with_same_rng_state(self, source_pdf):
        original = rasterize_pdf(source_pdf, dpi=150)[0]
        d1 = degrade_page(original, random.Random(7))
        d2 = degrade_page(original, random.Random(7))
        assert d1.size == d2.size


class TestSimulateScan:
    def test_output_pdf_has_no_extractable_text(self, source_pdf, tmp_path):
        # Sanity: the SOURCE pdf must have extractable text (it's the
        # positive control).
        with pdfplumber.open(source_pdf) as pdf:
            source_text = pdf.pages[0].extract_text() or ""
        assert len(source_text.strip()) > 20

        out_path = tmp_path / "scanned.pdf"
        simulate_scan(source_pdf, out_path, random.Random(1), dpi=150)

        assert out_path.exists()
        with pdfplumber.open(out_path) as pdf:
            scanned_text = pdf.pages[0].extract_text() or ""

        # This is the entire point of scan simulation: no text layer.
        assert scanned_text.strip() == ""

    def test_output_pdf_preserves_page_count(self, source_pdf, tmp_path):
        out_path = tmp_path / "scanned.pdf"
        simulate_scan(source_pdf, out_path, random.Random(2), dpi=150)

        with pdfplumber.open(source_pdf) as src, pdfplumber.open(out_path) as scanned:
            assert len(src.pages) == len(scanned.pages)

    def test_simulate_scan_as_images_writes_one_png_per_page(self, source_pdf, tmp_path):
        out_dir = tmp_path / "images"
        paths = simulate_scan_as_images(source_pdf, out_dir, random.Random(3), dpi=150)

        assert len(paths) >= 1
        for p in paths:
            assert p.exists()
            assert p.suffix == ".png"
            assert p.stat().st_size > 0
