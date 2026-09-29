"""
Week 2, Step 2.3: text-layer extraction path.

For a document router.py has classified as has_text_layer=True. Uses
pdfplumber to pull every word with its bounding box -- no OCR engine
needed, no system binary, near-exact (confidence 1.0 throughout,
there's no recognition uncertainty when the text is already embedded
in the PDF). This is the cheap path that should carry most
digitally-generated lab PDFs.
"""

from pathlib import Path

import pdfplumber

from app.ocr.common import PageWords, Word


def extract_words(pdf_path: Path) -> tuple[PageWords, ...]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            words = tuple(
                Word(
                    text=w["text"],
                    x0=w["x0"],
                    y0=w["top"],
                    x1=w["x1"],
                    y1=w["bottom"],
                    page_no=i,
                    confidence=1.0,
                )
                for w in page.extract_words()
            )
            pages.append(PageWords(page_no=i, width=page.width, height=page.height, words=words))
    return tuple(pages)
