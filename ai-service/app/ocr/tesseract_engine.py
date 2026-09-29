"""
Week 2, Step 2.3: Tesseract OCR engine (OCR_ENGINE=tesseract, the
default).

Wraps pytesseract's `image_to_data` (TSV output), which is what makes
per-word confidence and bounding boxes available at all -- plain
`image_to_string` throws that information away.

Requires the Tesseract *binary* on the host/image, not just the
pytesseract Python package -- there is no PyPI wheel for it:
  - Docker (this project's images): `apt-get install tesseract-ocr`,
    already added to ai-service/Dockerfile.
  - Windows dev machine: install from
    https://github.com/UB-Mannheim/tesseract/wiki and set
    TESSERACT_CMD (see .env.example) to the installed tesseract.exe,
    OR only run the worker inside Docker.
  - This was NOT available in the environment this module was
    developed in (no system package manager access) -- is_available()
    below returns False there, and the test suite skips the
    OCR-through-Tesseract tests with an explicit reason rather than
    silently passing. Every other module in app/ocr/ (router,
    text_layer, raster, table_reconstruct, field_extract) has no such
    gap and is fully tested.
"""

from dataclasses import dataclass

import pytesseract
from PIL import Image

from app.core.config import get_settings
from app.ocr.common import PageWords, Word


def _configure_tesseract_cmd():
    settings = get_settings()
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


@dataclass(frozen=True)
class TesseractAvailability:
    available: bool
    version: str | None
    error: str | None


def is_available() -> TesseractAvailability:
    """Checks whether the Tesseract binary is actually reachable, not
    just whether the pytesseract package is importable (it always is --
    it has no compiled dependency on the binary at import time)."""

    _configure_tesseract_cmd()
    try:
        version = str(pytesseract.get_tesseract_version())
        return TesseractAvailability(available=True, version=version, error=None)
    except Exception as error:  # pytesseract.TesseractNotFoundError, or any OS error
        return TesseractAvailability(available=False, version=None, error=str(error))


def extract_words_from_image(image, page_no: int, dpi: int) -> PageWords:
    """image: a numpy array (BGR, as raster.py produces) or a PIL Image.
    Raises RuntimeError with a clear message (not a raw
    TesseractNotFoundError) if the binary isn't available -- callers
    should check is_available() first if they want to fail earlier."""

    _configure_tesseract_cmd()

    if not isinstance(image, Image.Image):
        import cv2
        image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError as error:
        raise RuntimeError(
            "Tesseract binary not found. Install it (see this module's "
            "docstring) or set OCR_ENGINE=paddle. "
            f"Underlying error: {error}"
        ) from error

    # pytesseract reports coordinates in pixels at the image's actual
    # resolution; convert to PDF points (1/72") using the dpi the image
    # was rasterized at, so downstream code (table_reconstruct.py) can
    # treat Tesseract-sourced words identically to text-layer words.
    scale = 72.0 / dpi

    words = []
    n = len(data["text"])
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        conf_raw = data["conf"][i]
        try:
            confidence = max(0.0, float(conf_raw)) / 100.0
        except (TypeError, ValueError):
            confidence = 0.0

        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        words.append(
            Word(
                text=text,
                x0=x * scale, y0=y * scale,
                x1=(x + w) * scale, y1=(y + h) * scale,
                page_no=page_no,
                confidence=confidence,
            )
        )

    if image.width and image.height:
        page_width, page_height = image.width * scale, image.height * scale
    else:
        page_width = page_height = 0.0

    return PageWords(page_no=page_no, width=page_width, height=page_height, words=tuple(words))
