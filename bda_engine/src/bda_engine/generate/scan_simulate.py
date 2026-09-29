"""
Simulate a scanned or phone-photographed lab report from a born-digital
PDF rendered by render_pdf.py.

Without this, every document in the corpus has a clean embedded text
layer and the Week 2 OCR pipeline's actual OCR engines (Tesseract/
PaddleOCR) never get exercised -- only the cheap text-layer path would
ever run. This module is what makes has_text_layer=False documents
exist in the corpus at all.

Degradations applied, each independently randomized:
  - rasterize at 200-300 dpi (a scan/photo has no text layer at all)
  - small rotation (+/- 2 degrees) -- a crooked scan
  - gaussian noise
  - contrast/brightness jitter
  - JPEG re-encoding at a lossy quality -- compression artifacts

Output is a single-page-per-image PDF (each original page rasterized
and re-embedded as a full-page image) so it still round-trips through
"upload a PDF" -- and also, optionally, a raw PNG per page (for
testing an image-upload path once the backend accepts image mimetypes,
see docs/WEEKS_1-3_STATUS_AND_PLAN.md Week 2 gap list).
"""

import io
import random
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageFilter


def rasterize_pdf(pdf_path: Path, dpi: int) -> list[Image.Image]:
    """Render every page of pdf_path to a PIL Image at the given dpi."""

    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        mode = "RGB" if pix.n < 4 else "RGBA"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        if mode == "RGBA":
            img = img.convert("RGB")
        images.append(img)
    doc.close()
    return images


def _add_gaussian_noise(img: Image.Image, rng: random.Random, sigma: float) -> Image.Image:
    arr = np.asarray(img).astype(np.float32)
    noise = np.random.default_rng(rng.randint(0, 2**31 - 1)).normal(0, sigma, arr.shape)
    noisy = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy)


def _jitter_contrast_brightness(img: Image.Image, rng: random.Random) -> Image.Image:
    arr = np.asarray(img).astype(np.float32)
    contrast = rng.uniform(0.85, 1.15)
    brightness = rng.uniform(-15, 15)
    arr = np.clip(arr * contrast + brightness, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def degrade_page(img: Image.Image, rng: random.Random) -> Image.Image:
    """Apply the full randomized degradation pipeline to one page image."""

    angle = rng.uniform(-2.0, 2.0)
    img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255), resample=Image.BICUBIC)

    if rng.random() < 0.6:
        img = _add_gaussian_noise(img, rng, sigma=rng.uniform(3, 10))

    img = _jitter_contrast_brightness(img, rng)

    if rng.random() < 0.3:
        img = img.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.3, 0.8)))

    # JPEG re-encode at a lossy quality -- introduces real compression
    # artifacts, unlike saving as PNG.
    quality = rng.randint(45, 80)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def simulate_scan(
    source_pdf_path: Path,
    out_pdf_path: Path,
    rng: random.Random,
    dpi: int | None = None,
) -> Path:
    """
    Rasterize source_pdf_path, degrade every page, and write a new PDF
    (out_pdf_path) whose pages are full-page images with NO text layer
    -- i.e. has_text_layer=False for the OCR router (app/services or
    ai-service/app/ocr/router.py, Week 2).
    """

    dpi = dpi or rng.randint(200, 300)
    pages = rasterize_pdf(source_pdf_path, dpi=dpi)
    degraded = [degrade_page(p, rng) for p in pages]

    out_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    first, rest = degraded[0], degraded[1:]
    first.save(
        out_pdf_path, format="PDF", save_all=True, append_images=rest,
        resolution=float(dpi),
    )
    return out_pdf_path


def simulate_scan_as_images(
    source_pdf_path: Path,
    out_dir: Path,
    rng: random.Random,
    dpi: int | None = None,
) -> list[Path]:
    """Same degradation pipeline, but writes one PNG per page instead of
    re-wrapping as a PDF -- for testing an image-upload path."""

    dpi = dpi or rng.randint(200, 300)
    pages = rasterize_pdf(source_pdf_path, dpi=dpi)
    degraded = [degrade_page(p, rng) for p in pages]

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, img in enumerate(degraded):
        path = out_dir / f"page_{i + 1}.png"
        img.save(path, format="PNG")
        paths.append(path)
    return paths
