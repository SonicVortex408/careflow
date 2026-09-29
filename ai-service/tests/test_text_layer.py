"""
Week 2 Step 2.3 acceptance: the text-layer extractor recovers every
printed word (as bounding-boxed Word objects) from a real generator
PDF, with full confidence since there's no OCR uncertainty.
"""

from app.ocr.text_layer import extract_words


class TestExtractWords:
    def test_extracts_words_with_full_confidence(self, clean_pdf_factory):
        path, rows = clean_pdf_factory()
        pages = extract_words(path)

        assert len(pages) >= 1
        all_words = [w for page in pages for w in page.words]
        assert len(all_words) > 0
        assert all(w.confidence == 1.0 for w in all_words)

    def test_every_printed_value_is_recovered_as_a_word(self, clean_pdf_factory):
        path, rows = clean_pdf_factory(layout="boxed_table")
        pages = extract_words(path)
        all_text = {w.text for page in pages for w in page.words}

        for row in rows:
            assert row.value_raw in all_text, (
                f"{row.value_raw!r} (biomarker={row.biomarker_key}) not found in extracted words"
            )

    def test_word_bounding_boxes_are_well_formed(self, clean_pdf_factory):
        path, _ = clean_pdf_factory()
        pages = extract_words(path)
        for page in pages:
            for w in page.words:
                assert w.x0 < w.x1
                assert w.y0 < w.y1
                assert w.page_no == page.page_no

    def test_scanned_pdf_yields_no_words(self, scanned_pdf_factory):
        # text_layer.py should never be called on a scanned doc in the
        # real pipeline (router.py routes it elsewhere), but confirm
        # the honest failure mode: no text, no words -- not garbage.
        scanned_path, _, _ = scanned_pdf_factory()
        pages = extract_words(scanned_path)
        all_words = [w for page in pages for w in page.words]
        assert len(all_words) == 0
