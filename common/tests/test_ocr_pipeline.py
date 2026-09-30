import shutil

import pytest

from polymarker_common.ocr import words_to_lines
from polymarker_common.pipeline import ingest_lines

PANEL = [
    "Apex Clinical Laboratory",
    "Age: 38   Sex: Female",
    "TSH                    6.2     uIU/mL    0.40-4.00   H",
    "Free T4                0.95    ng/dL     0.8-1.8",
    "Ferritin               9       ng/mL     15-150      L",
    "Vitamin D, 25-Hydroxy  19      ng/mL     30-100      L",
    "Magnesium              19      mg/dL     1.7-2.4",
]


def test_words_to_lines_detects_columns():
    words = [
        {
            "text": "Free",
            "left": 10,
            "top": 5,
            "width": 40,
            "height": 10,
            "conf": 96,
            "block": 1,
            "par": 1,
            "line": 1,
        },
        {
            "text": "T4",
            "left": 55,
            "top": 5,
            "width": 20,
            "height": 10,
            "conf": 90,
            "block": 1,
            "par": 1,
            "line": 1,
        },
        {
            "text": "1.2",
            "left": 300,
            "top": 5,
            "width": 30,
            "height": 10,
            "conf": 80,
            "block": 1,
            "par": 1,
            "line": 1,
        },
    ]
    [(text, conf)] = words_to_lines(words)
    assert text == "Free T4    1.2"
    assert conf == pytest.approx(0.887, abs=1e-3)


def test_ingest_lines_end_to_end():
    out = ingest_lines(PANEL, ocr_method="text_layer")
    keys = [b["key"] for b in out["biomarkers"]]
    assert keys == ["TSH", "FT4", "VITD", "FERRITIN"]  # MG excluded as implausible
    assert out["metadata"]["sex"] == "F" and out["metadata"]["age"] == 38
    ft4 = next(b for b in out["biomarkers"] if b["key"] == "FT4")
    assert ft4["unit"] == "pmol/L" and ft4["value"] == pytest.approx(12.23, abs=0.01)
    codes = {(i["code"], i["marker"]) for i in out["quality"]["issues"]}
    assert ("implausible", "MG") in codes
    assert out["quality"]["needs_clinician_attention"]


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_tesseract_reads_rendered_panel(tmp_path):
    from PIL import Image, ImageDraw, ImageFont

    from polymarker_common.pipeline import ingest_document

    font = ImageFont.truetype("DejaVuSansMono.ttf", 28)
    img = Image.new("RGB", (1500, 60 * len(PANEL) + 40), "white")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(PANEL):
        draw.text((30, 20 + 60 * i), line, fill="black", font=font)
    path = tmp_path / "scan.png"
    img.save(path)
    out = ingest_document(path)
    assert out["ocr"]["method"] == "tesseract"
    assert {"TSH", "FT4", "FERRITIN"} <= {b["key"] for b in out["biomarkers"]}
