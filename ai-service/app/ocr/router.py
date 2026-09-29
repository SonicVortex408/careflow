"""
Week 2, Step 2.3: decide text-layer vs scanned per page.

Opens the PDF with PyMuPDF and measures extractable characters per
page. A born-digital PDF (rendered by bda_engine's render_pdf.py, or a
lab's own PDF export) has a real text layer and gets routed to the
cheap, near-exact text_layer.py path. A scanned or photographed report
(bda_engine's scan_simulate.py output, or a real phone photo) has
none, and gets routed to the OCR engine (tesseract_engine.py /
paddle_engine.py, selected by OCR_ENGINE).

A PDF can be mixed (e.g. a scanned cover page + a digitally-generated
results page); has_text_layer is reported per page, and the document
overall is has_text_layer=True only if EVERY page has one -- a single
scanned page still needs the OCR path to be read at all.
"""

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

# A page with fewer than this many extractable characters is treated
# as having no usable text layer -- guards against a PDF that embeds a
# handful of stray/invisible characters (a watermark, a form field)
# but is otherwise a scanned image.
MIN_CHARS_FOR_TEXT_LAYER = 20


@dataclass(frozen=True)
class PageLayerInfo:
    page_no: int  # 1-indexed
    width: float
    height: float
    char_count: int
    has_text_layer: bool


@dataclass(frozen=True)
class DocumentLayerInfo:
    pages: tuple[PageLayerInfo, ...]

    @property
    def has_text_layer(self) -> bool:
        """True only if every page has a usable text layer."""
        return len(self.pages) > 0 and all(p.has_text_layer for p in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)


def inspect_document(pdf_path: Path) -> DocumentLayerInfo:
    doc = fitz.open(pdf_path)
    try:
        pages = []
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            char_count = len(text.strip())
            pages.append(
                PageLayerInfo(
                    page_no=i,
                    width=page.rect.width,
                    height=page.rect.height,
                    char_count=char_count,
                    has_text_layer=char_count >= MIN_CHARS_FOR_TEXT_LAYER,
                )
            )
        return DocumentLayerInfo(pages=tuple(pages))
    finally:
        doc.close()
