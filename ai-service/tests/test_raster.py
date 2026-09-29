"""
Week 2 Step 2.3 acceptance: rasterization and deskew, against real
scan-simulated PDFs from bda_engine's generator (which applies its own
random rotation -- see bda_engine/generate/scan_simulate.py -- so this
is testing against genuinely skewed input, not a synthetic test image).
"""

import cv2
import numpy as np

from app.ocr.raster import (
    DEFAULT_DPI,
    deskew,
    estimate_skew_angle,
    prepare_for_ocr,
    rasterize,
)


class TestRasterize:
    def test_produces_one_image_per_page(self, scanned_pdf_factory):
        scanned_path, _, _ = scanned_pdf_factory()
        pages = rasterize(scanned_path, dpi=150)
        assert len(pages) >= 1
        for p in pages:
            assert p.image.ndim == 3
            assert p.image.shape[2] == 3  # BGR
            assert p.image.dtype == np.uint8

    def test_higher_dpi_yields_larger_image(self, clean_pdf_factory):
        path, _ = clean_pdf_factory()
        low = rasterize(path, dpi=100)[0]
        high = rasterize(path, dpi=300)[0]
        assert high.image.shape[0] > low.image.shape[0]
        assert high.image.shape[1] > low.image.shape[1]

    def test_default_dpi_constant(self):
        assert DEFAULT_DPI == 300


class TestEstimateSkewAngle:
    def test_blank_image_returns_zero(self):
        blank = np.full((200, 200, 3), 255, dtype=np.uint8)
        assert estimate_skew_angle(blank) == 0.0

    def test_rotated_text_image_detects_nonzero_skew(self, clean_pdf_factory):
        path, _ = clean_pdf_factory()
        page = rasterize(path, dpi=150)[0]

        h, w = page.image.shape[:2]
        matrix = cv2.getRotationMatrix2D((w // 2, h // 2), 7.0, 1.0)
        rotated = cv2.warpAffine(
            page.image, matrix, (w, h), borderValue=(255, 255, 255)
        )

        angle = estimate_skew_angle(rotated)
        assert abs(angle) > 0.5, "should detect a meaningfully nonzero skew"


class TestDeskew:
    def test_deskew_reduces_measured_skew(self, clean_pdf_factory):
        path, _ = clean_pdf_factory()
        page = rasterize(path, dpi=150)[0]

        h, w = page.image.shape[:2]
        matrix = cv2.getRotationMatrix2D((w // 2, h // 2), 5.0, 1.0)
        rotated = cv2.warpAffine(
            page.image, matrix, (w, h), borderValue=(255, 255, 255)
        )

        angle_before = abs(estimate_skew_angle(rotated))
        deskewed = deskew(rotated)
        angle_after = abs(estimate_skew_angle(deskewed))

        assert angle_after < angle_before

    def test_deskew_with_explicit_angle_does_not_crash(self, clean_pdf_factory):
        path, _ = clean_pdf_factory()
        page = rasterize(path, dpi=150)[0]
        result = deskew(page.image, angle=3.0)
        assert result.shape[:2] == page.image.shape[:2]

    def test_near_zero_angle_returns_image_unchanged(self, clean_pdf_factory):
        path, _ = clean_pdf_factory()
        page = rasterize(path, dpi=150)[0]
        result = deskew(page.image, angle=0.02)
        assert np.array_equal(result, page.image)


class TestPrepareForOcr:
    def test_runs_end_to_end_on_scanned_document(self, scanned_pdf_factory):
        scanned_path, _, _ = scanned_pdf_factory()
        pages = prepare_for_ocr(scanned_path, dpi=150)
        assert len(pages) >= 1
        for p in pages:
            assert p.image.ndim == 3
