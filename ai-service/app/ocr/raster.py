"""
Week 2, Step 2.3: rasterize + deskew/denoise for the scanned path.

Renders each page of a has_text_layer=False document to an image
(PyMuPDF, 300 dpi default), then straightens it before handing off to
the OCR engine (tesseract_engine.py / paddle_engine.py) -- a few
degrees of rotation measurably hurts OCR accuracy, and a scan/photo
is essentially never perfectly level.
"""

from dataclasses import dataclass

import cv2
import fitz  # PyMuPDF
import numpy as np

DEFAULT_DPI = 300


@dataclass(frozen=True)
class RasterPage:
    page_no: int  # 1-indexed
    image: np.ndarray  # BGR, uint8, HxWx3
    dpi: int


def rasterize(pdf_path, dpi: int = DEFAULT_DPI) -> list[RasterPage]:
    doc = fitz.open(pdf_path)
    try:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pages = []
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=matrix)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            else:
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            pages.append(RasterPage(page_no=i, image=bgr, dpi=dpi))
        return pages
    finally:
        doc.close()


def estimate_skew_angle(image: np.ndarray) -> float:
    """Estimates the rotation (degrees) needed to straighten `image`,
    using the minimum-area bounding rectangle of dark (text) pixels.
    Returns 0.0 for an image with no discernible text mass (e.g. a
    blank page) rather than an arbitrary angle."""

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    coords = cv2.findNonZero(binary)
    if coords is None or len(coords) < 50:
        return 0.0

    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    # cv2.minAreaRect's angle convention: normalize to a small rotation
    # in [-45, 45] rather than the raw [-90, 0) OpenCV returns, since
    # we're correcting a near-level scan, not rotating to an arbitrary
    # orientation.
    if angle < -45:
        angle = 90 + angle
    return float(angle)


def deskew(image: np.ndarray, angle: float | None = None) -> np.ndarray:
    if angle is None:
        angle = estimate_skew_angle(image)
    if abs(angle) < 0.1:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )


def denoise(image: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(
        image, None, h=7, hColor=7, templateWindowSize=7, searchWindowSize=21,
    )


def prepare_for_ocr(pdf_path, dpi: int = DEFAULT_DPI) -> list[RasterPage]:
    """The full pipeline: rasterize -> deskew -> denoise, ready for an
    OCR engine to consume."""

    pages = rasterize(pdf_path, dpi=dpi)
    return [
        RasterPage(page_no=p.page_no, image=denoise(deskew(p.image)), dpi=p.dpi)
        for p in pages
    ]
