"""Document text extraction (optional extra: ``polymarker-common[ocr]``).

Strategy, per page:

1. **Text layer** (pypdf, layout mode) for digitally generated PDFs - exact text,
   column spacing preserved, confidence 0.99.
2. **Tesseract** for scanned PDFs / images: pages are rendered with pypdfium2 at
   300 dpi and read with ``image_to_data``. Words are regrouped into lines and a
   simple *table detector* re-inserts column breaks wherever the horizontal gap
   between words is much larger than the typical inter-word gap, so the parser
   sees ``Label  Value  Unit  Range`` columns. Line confidence = mean word conf.
3. **PaddleOCR** (``OCR_ENGINE=paddle``) and **LayoutLMv3** (``ENABLE_LAYOUTLMV3``)
   are behind flags because they pull large wheels/models. If selected but not
   installed, extraction falls back to Tesseract and says so in ``warnings``.

All heavy imports are lazy so importing this module is free.
"""

from __future__ import annotations

import logging
import os
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_TEXT_LAYER_CHARS = 40
RENDER_DPI = 300
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


@dataclass
class OcrResult:
    lines: list[str]
    line_confidences: list[float]
    method: str  # text_layer | tesseract | paddle | layoutlmv3 | plain_text | mixed
    pages: int
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def mean_confidence(self) -> float:
        return round(statistics.fmean(self.line_confidences), 3) if self.line_confidences else 0.0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["mean_confidence"] = self.mean_confidence
        return data


# ---------------------------------------------------------------- text layer


def _text_layer_pages(path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except Exception:  # noqa: BLE001 - some PDFs break layout mode
            text = page.extract_text() or ""
        pages.append(text)
    return pages


# ---------------------------------------------------------------- tesseract


def words_to_lines(words: list[dict], gap_factor: float = 2.5) -> list[tuple[str, float]]:
    """Group OCR words into lines and re-insert column breaks (table detection).

    ``words``: dicts with text, left, top, width, height, conf (0-100), block, par, line.
    """
    groups: dict[tuple, list[dict]] = {}
    for w in words:
        if not str(w.get("text", "")).strip():
            continue
        groups.setdefault((w["block"], w["par"], w["line"]), []).append(w)

    ordered = sorted(
        groups.values(), key=lambda ws: (min(w["top"] for w in ws), min(w["left"] for w in ws))
    )
    lines: list[tuple[str, float]] = []
    for ws in ordered:
        ws.sort(key=lambda w: w["left"])
        gaps = [ws[i + 1]["left"] - (ws[i]["left"] + ws[i]["width"]) for i in range(len(ws) - 1)]
        char_w = statistics.median(max(1, w["width"]) / max(1, len(str(w["text"]))) for w in ws)
        # Baseline = a typical inter-word space (lower quartile of gaps), so a
        # single wide column gap cannot inflate its own threshold.
        word_gap = sorted(gaps)[len(gaps) // 4] if gaps else 0
        threshold = max(char_w * gap_factor, word_gap * 3)
        parts = [str(ws[0]["text"])]
        for gap, w in zip(gaps, ws[1:], strict=False):
            parts.append("    " if gap > threshold else " ")
            parts.append(str(w["text"]))
        confs = [float(w["conf"]) for w in ws if float(w["conf"]) >= 0]
        conf = (statistics.fmean(confs) / 100.0) if confs else 0.0
        lines.append(("".join(parts), round(conf, 3)))
    return lines


def _tesseract_image(image) -> list[tuple[str, float]]:
    import pytesseract

    # Tesseract's OpenMP threads busy-wait; with several OCR processes per host
    # (Celery concurrency, Spark executors, multiprocessing) that degrades
    # throughput by orders of magnitude. Parallelism comes from processes instead.
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")

    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config="--psm 6")
    words = [
        {
            k: data[k][i]
            for k in (
                "text",
                "left",
                "top",
                "width",
                "height",
                "conf",
                "block_num",
                "par_num",
                "line_num",
            )
        }
        for i in range(len(data["text"]))
    ]
    for w in words:
        w["block"], w["par"], w["line"] = w.pop("block_num"), w.pop("par_num"), w.pop("line_num")
    return words_to_lines(words)


def _render_pdf(path: Path, dpi: int = RENDER_DPI):
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    try:
        for page in pdf:
            yield page.render(scale=dpi / 72).to_pil()
    finally:
        pdf.close()


def _paddle_available() -> bool:
    try:
        import paddleocr  # noqa: F401
    except ImportError:
        return False
    return True


def _paddle_image(image) -> list[tuple[str, float]]:  # pragma: no cover - optional heavy dep
    import numpy as np
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    result = ocr.ocr(np.array(image), cls=True)
    words = []
    for i, (box, (text, conf)) in enumerate(result[0] or []):
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        words.append(
            {
                "text": text,
                "left": min(xs),
                "top": min(ys),
                "width": max(xs) - min(xs),
                "height": max(ys) - min(ys),
                "conf": conf * 100,
                "block": 0,
                "par": 0,
                "line": int(min(ys) // 20),
                "_i": i,
            }
        )
    return words_to_lines(words)


def _ocr_image(image, engine: str, warnings: list[str]) -> tuple[list[tuple[str, float]], str]:
    if engine == "paddle":
        if _paddle_available():
            return _paddle_image(image), "paddle"
        warnings.append("OCR_ENGINE=paddle but paddleocr is not installed; used Tesseract")
    return _tesseract_image(image), "tesseract"


# ---------------------------------------------------------------- entry point


def extract_text(path: str | Path, engine: str | None = None) -> OcrResult:
    path = Path(path)
    engine = (engine or os.getenv("OCR_ENGINE", "tesseract")).lower()
    warnings: list[str] = []
    if os.getenv("ENABLE_LAYOUTLMV3", "false").lower() in ("1", "true", "yes"):
        warnings.append(
            "ENABLE_LAYOUTLMV3 is set but the LayoutLMv3 token classifier is not bundled; "
            "falling back to OCR + rule-based table parsing"
        )

    suffix = path.suffix.lower()
    if suffix == ".txt":
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return OcrResult(lines, [1.0] * len(lines), "plain_text", 1, warnings)

    if suffix in IMAGE_SUFFIXES:
        from PIL import Image

        with Image.open(path) as img:
            pairs, method = _ocr_image(img.convert("RGB"), engine, warnings)
        return OcrResult([p[0] for p in pairs], [p[1] for p in pairs], method, 1, warnings)

    if suffix != ".pdf":
        raise ValueError(f"Unsupported document type: {suffix}")

    page_texts = _text_layer_pages(path)
    lines: list[str] = []
    confs: list[float] = []
    methods: set[str] = set()
    rendered = None
    for i, text in enumerate(page_texts):
        if len(text.strip()) >= MIN_TEXT_LAYER_CHARS:
            page_lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
            lines += page_lines
            confs += [0.99] * len(page_lines)
            methods.add("text_layer")
            continue
        if rendered is None:
            rendered = list(_render_pdf(path))
        pairs, method = _ocr_image(rendered[i], engine, warnings)
        lines += [p[0] for p in pairs]
        confs += [p[1] for p in pairs]
        methods.add(method)
    method = methods.pop() if len(methods) == 1 else ("mixed" if methods else "empty")
    return OcrResult(lines, confs, method, len(page_texts), warnings)
