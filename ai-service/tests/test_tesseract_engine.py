"""
Week 2 Step 2.3 acceptance for the Tesseract engine.

The Tesseract *binary* was not available in the environment this was
developed in (confirmed via is_available() below, not assumed) -- see
app/ocr/tesseract_engine.py's module docstring. Tests that need the
binary to actually run OCR are skipped with an explicit reason rather
than silently passing or being deleted; is_available()'s own behavior
and the error-wrapping path are both tested without needing the
binary at all.
"""

import numpy as np
import pytest

from app.ocr.tesseract_engine import is_available

_availability = is_available()

requires_tesseract = pytest.mark.skipif(
    not _availability.available,
    reason=(
        "Tesseract binary not installed in this environment "
        f"({_availability.error}). Install it per "
        "app/ocr/tesseract_engine.py's docstring to run this test."
    ),
)


class TestIsAvailable:
    def test_returns_a_structured_result_without_raising(self):
        # This must never raise, regardless of whether the binary is
        # present -- it's the thing callers check *before* deciding
        # whether to call extract_words_from_image at all.
        result = is_available()
        assert isinstance(result.available, bool)
        if not result.available:
            assert result.error is not None
            assert result.version is None


class TestExtractWordsErrorHandling:
    @pytest.mark.skipif(
        _availability.available,
        reason="This tests the missing-binary error path specifically.",
    )
    def test_missing_binary_raises_clear_runtime_error(self):
        from app.ocr.tesseract_engine import extract_words_from_image

        blank_image = np.full((100, 100, 3), 255, dtype=np.uint8)
        with pytest.raises(RuntimeError, match="Tesseract binary not found"):
            extract_words_from_image(blank_image, page_no=1, dpi=300)


@requires_tesseract
class TestExtractWordsFromImage:
    """Only runs if a real Tesseract binary is present. Kept here (not
    deleted) so this suite becomes a real end-to-end check the moment
    it's run in Docker or on a machine with Tesseract installed."""

    def test_extracts_words_from_scanned_document(self, scanned_pdf_factory):
        from app.ocr.raster import prepare_for_ocr
        from app.ocr.tesseract_engine import extract_words_from_image

        scanned_path, _, ground_truth_rows = scanned_pdf_factory()
        pages = prepare_for_ocr(scanned_path, dpi=300)

        all_words = []
        for page in pages:
            page_words = extract_words_from_image(page.image, page.page_no, page.dpi)
            all_words.extend(page_words.words)

        assert len(all_words) > 0
        recovered_text = " ".join(w.text for w in all_words)
        # At least some printed values should be recognized (not
        # asserting perfect accuracy -- that's what evaluation/ Phase 4
        # measures against ground truth).
        found = sum(1 for row in ground_truth_rows if row.value_raw in recovered_text)
        assert found > 0
