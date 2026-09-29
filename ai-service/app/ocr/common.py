"""
Shared types for the OCR pipeline. Every engine (text-layer, Tesseract,
PaddleOCR, LayoutLMv3) emits the same `Word` shape, so
table_reconstruct.py and field_extract.py work identically regardless
of which engine produced the words -- that's what lets the text-layer
path (cheap, near-exact) and the scanned path (Tesseract/Paddle) share
one downstream pipeline instead of two.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page_no: int  # 1-indexed
    confidence: float  # 0.0-1.0; 1.0 for the text-layer engine (no OCR uncertainty)


@dataclass(frozen=True)
class PageWords:
    page_no: int
    width: float
    height: float
    words: tuple[Word, ...]
