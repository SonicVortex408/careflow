"""
Week 2 Step 2.3 acceptance: the router correctly distinguishes a
born-digital PDF (has_text_layer=True) from a scan-simulated one
(has_text_layer=False), against real PDFs from bda_engine's generator
-- not hand-crafted fixtures.
"""

from app.ocr.router import inspect_document


class TestInspectDocument:
    def test_clean_pdf_has_text_layer(self, clean_pdf_factory):
        path, _ = clean_pdf_factory()
        info = inspect_document(path)
        assert info.has_text_layer is True
        assert info.page_count >= 1
        for page in info.pages:
            assert page.has_text_layer is True
            assert page.char_count > 20

    def test_scanned_pdf_has_no_text_layer(self, scanned_pdf_factory):
        scanned_path, _, _ = scanned_pdf_factory()
        info = inspect_document(scanned_path)
        assert info.has_text_layer is False
        for page in info.pages:
            assert page.has_text_layer is False
            assert page.char_count == 0

    def test_page_dimensions_are_positive(self, clean_pdf_factory):
        path, _ = clean_pdf_factory()
        info = inspect_document(path)
        for page in info.pages:
            assert page.width > 0
            assert page.height > 0

    def test_all_layouts_detected_as_text_layer(self, clean_pdf_factory):
        for layout in ("single_column", "two_column", "multi_panel"):
            path, _ = clean_pdf_factory(layout=layout, seed=2)
            info = inspect_document(path)
            assert info.has_text_layer is True, layout

    def test_raw_scanned_image_has_no_text_layer(self, scanned_png_factory):
        # A raw PNG upload (no PDF wrapper) -- the multer allowlist in
        # backend/src/middleware/uploadMiddleware.js accepts image/png
        # and image/jpeg as of Week 2 specifically because PyMuPDF
        # opens an image file directly as a one-page pseudo-document;
        # confirms that actually works, not just for PDFs.
        png_path, _, _ = scanned_png_factory()
        info = inspect_document(png_path)
        assert info.has_text_layer is False
        assert info.page_count == 1
