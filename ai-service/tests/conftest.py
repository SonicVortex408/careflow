"""
Shared fixtures for the OCR test suite. Uses bda_engine's real
generator (not fixtures/mocks) to produce actual PDFs -- ai-service
does not depend on the bda_engine package at runtime (see
app/services/reference_data.py), but the test suite is free to import
it directly from the sibling project for exactly this purpose: giving
the OCR pipeline tests real, varied documents to run against instead
of a single hand-crafted sample.
"""

import random
import sys
from pathlib import Path

import numpy as np
import pytest

# bda_engine is a sibling project (ai-service/../bda_engine/src), not
# an ai-service dependency -- see the module docstring above.
_BDA_ENGINE_SRC = Path(__file__).resolve().parents[2] / "bda_engine" / "src"
if str(_BDA_ENGINE_SRC) not in sys.path:
    sys.path.insert(0, str(_BDA_ENGINE_SRC))


@pytest.fixture(scope="session")
def clean_pdf_factory(tmp_path_factory):
    """Returns a function that renders one clean (text-layer) PDF and
    returns (path, rows) where rows is the ground-truth PrintedRow list."""

    from bda_engine.generate.distributions import PHENOTYPES, sample_markers
    from bda_engine.generate.render_pdf import build_printed_rows, render_report_pdf

    def _make(
        layout="boxed_table", phenotype_key="overt_hypothyroid_autoimmune",
        seed=1, max_rows=6,
    ):
        np_rng = np.random.default_rng(seed)
        values = sample_markers(PHENOTYPES[phenotype_key], "female", np_rng)
        values = {k.value: v for k, v in values.items()}
        rows = build_printed_rows(values, random.Random(seed), max_rows=max_rows)

        out_dir = tmp_path_factory.mktemp("clean_pdf")
        path = out_dir / "report.pdf"
        render_report_pdf(
            out_path=path, document_id="doc1", patient_id="pat1",
            lab_provider_name="Meridian Health Labs", patient_age_years=45.0,
            patient_sex="female", rows=rows, layout=layout, accession_no="ACC-1",
        )
        return path, rows

    return _make


@pytest.fixture(scope="session")
def scanned_pdf_factory(clean_pdf_factory, tmp_path_factory):
    """Returns a function that renders a clean PDF, then scan-simulates
    it (no text layer). Returns (scanned_path, clean_path, rows)."""

    from bda_engine.generate.scan_simulate import simulate_scan

    def _make(**kwargs):
        clean_path, rows = clean_pdf_factory(**kwargs)
        out_dir = tmp_path_factory.mktemp("scanned_pdf")
        scanned_path = out_dir / "scanned.pdf"
        simulate_scan(clean_path, scanned_path, random.Random(1), dpi=200)
        return scanned_path, clean_path, rows

    return _make


@pytest.fixture(scope="session")
def scanned_png_factory(clean_pdf_factory, tmp_path_factory):
    """Same degradation pipeline as scanned_pdf_factory, but returns a
    raw PNG (no PDF wrapper) -- for the image-upload path
    (backend/src/middleware/uploadMiddleware.js accepts image/png,
    image/jpeg as of Week 2). Returns (png_path, clean_path, rows)."""

    from bda_engine.generate.scan_simulate import simulate_scan_as_images

    def _make(**kwargs):
        clean_path, rows = clean_pdf_factory(**kwargs)
        out_dir = tmp_path_factory.mktemp("scanned_png")
        png_paths = simulate_scan_as_images(clean_path, out_dir, random.Random(1), dpi=200)
        return png_paths[0], clean_path, rows

    return _make
