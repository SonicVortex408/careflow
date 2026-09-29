"""
Render one synthetic patient's biomarker panel as a lab-report PDF,
using one of several visually distinct layout templates.

This is the "heterogeneity" half of the Week 1 brief: each rendered
report varies its layout template, per-analyte naming variant, source
unit, whether/how a reference range is printed, and page count -- so
the Week 2 OCR pipeline has real variety to prove itself against, not
one format it can hardcode around.

Every value actually printed on the page, and the TRUE canonical
value/unit/biomarker it was derived from, are returned as a
`RenderedReport` -- the caller (generate_synthetic_data.py) writes
that out as the ground-truth JSON the OCR/normalization pipeline is
scored against.
"""

import random
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from bda_engine.reference_data import load_biomarkers, load_synonyms, load_unit_conversions
from bda_engine.schemas.common import BiomarkerKey

LAYOUTS = (
    "single_column",
    "two_column",
    "boxed_table",
    "borderless_table",
    "header_heavy",
    "multi_panel",
)

# A handful of textual templates for a printed bounded range, so the
# same numbers don't always appear in the same punctuation.
_RANGE_TEMPLATES = [
    "{lo} - {hi}",
    "{lo}-{hi}",
    "{lo} to {hi}",
    "Normal: {lo}-{hi}",
]

_PANEL_GROUPS = {
    "Thyroid Panel": [BiomarkerKey.TSH, BiomarkerKey.FT3, BiomarkerKey.FT4, BiomarkerKey.ANTI_TPO],
    "Micronutrient Panel": [
        BiomarkerKey.VIT_D_25OH, BiomarkerKey.VIT_B12, BiomarkerKey.FERRITIN,
        BiomarkerKey.MAGNESIUM, BiomarkerKey.ZINC,
    ],
}


@dataclass(frozen=True)
class PrintedRow:
    row_index: int
    biomarker_key: str            # ground truth
    loinc_code: str                # ground truth
    analyte_name_raw: str          # what's printed
    value_raw: str                 # what's printed, formatted
    value_printed_numeric: float   # the value in the PRINTED unit
    unit_raw: str                  # what's printed
    reference_range_raw: str | None
    value_canonical: float         # ground truth, canonical unit
    unit_canonical: str            # ground truth


@dataclass(frozen=True)
class RenderedReport:
    document_id: str
    patient_id: str
    layout: str
    pdf_path: Path
    page_count: int
    lab_provider_name: str
    patient_age_years: float
    patient_sex: str
    rows: list[PrintedRow] = field(default_factory=list)


def _convert_canonical_to_unit(
    biomarker_key: str, value_canonical: float, target_unit: str
) -> float | None:
    """Inverse of ai-service's units.convert(): given a value already in
    the biomarker's canonical unit, express it in `target_unit`. Returns
    None if target_unit isn't in reference/unit_conversions.csv for this
    biomarker (should not happen for units this module itself picked,
    but callers should not assume)."""

    for row in load_unit_conversions():
        if row.biomarker_key == biomarker_key and row.from_unit == target_unit:
            # value_canonical = value_in_target_unit * factor
            return value_canonical / row.factor
    return None


def _pick_unit_and_value(biomarker_key: str, value_canonical: float, rng: random.Random):
    """Pick a random source unit for this biomarker (from
    reference/unit_conversions.csv) and convert the canonical value
    into it for printing."""

    candidates = [r for r in load_unit_conversions() if r.biomarker_key == biomarker_key]
    row = rng.choice(candidates)
    printed_value = _convert_canonical_to_unit(biomarker_key, value_canonical, row.from_unit)
    return row.from_unit, printed_value


def _format_value(value: float) -> str:
    if value >= 100:
        return f"{value:.0f}"
    if value >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def _maybe_range_text(biomarker_key: str, unit: str, rng: random.Random) -> str | None:
    if rng.random() < 0.15:  # some reports print no range at all
        return None

    biomarkers = load_biomarkers()
    biomarker = biomarkers[biomarker_key]

    lo = _convert_canonical_to_unit(biomarker_key, biomarker.default_ref_low, unit)
    hi = _convert_canonical_to_unit(biomarker_key, biomarker.default_ref_high, unit)
    if lo is None or hi is None:
        return None

    template = rng.choice(_RANGE_TEMPLATES)
    return template.format(lo=_format_value(lo), hi=_format_value(hi))


def build_printed_rows(
    biomarker_values: dict[str, float],
    rng: random.Random,
    max_rows: int | None = None,
) -> list[PrintedRow]:
    """biomarker_values: {biomarker_key: value_in_canonical_unit}, the
    ground truth for one patient's panel (a subset of the 9, per
    Week 1's heterogeneity requirement)."""

    synonyms_by_key: dict[str, list[str]] = {}
    for row in load_synonyms():
        synonyms_by_key.setdefault(row.biomarker_key, []).append(row.variant)

    biomarkers = load_biomarkers()
    keys = list(biomarker_values.keys())
    if max_rows is not None:
        keys = rng.sample(keys, k=min(max_rows, len(keys)))

    rows = []
    for i, key in enumerate(keys):
        value_canonical = biomarker_values[key]
        unit, printed_value = _pick_unit_and_value(key, value_canonical, rng)
        # Occasionally print the raw variant in upper/title case, like a
        # real report header would.
        variant = rng.choice(synonyms_by_key[key])
        casing = rng.choice(["as_is", "title", "upper"])
        if casing == "title":
            variant = variant.title()
        elif casing == "upper":
            variant = variant.upper()

        rows.append(
            PrintedRow(
                row_index=i,
                biomarker_key=key,
                loinc_code=biomarkers[key].loinc_code,
                analyte_name_raw=variant,
                value_raw=_format_value(printed_value),
                value_printed_numeric=printed_value,
                unit_raw=unit,
                reference_range_raw=_maybe_range_text(key, unit, rng),
                value_canonical=value_canonical,
                unit_canonical=biomarkers[key].canonical_unit,
            )
        )
    return rows


def _draw_header(c: canvas.Canvas, x, y, lab_name, patient_age, patient_sex, accession):
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, lab_name)
    c.setFont("Helvetica", 9)
    c.drawString(x, y - 16, f"Patient: {patient_age:.0f}Y / {patient_sex[0].upper()}")
    c.drawString(x, y - 28, f"Accession: {accession}")
    return y - 50


def _row_line(row: PrintedRow) -> str:
    parts = [row.analyte_name_raw, row.value_raw, row.unit_raw]
    if row.reference_range_raw:
        parts.append(f"({row.reference_range_raw})")
    return "   ".join(parts)


def _render_single_column(c: canvas.Canvas, rows, header_bottom, x=0.75 * inch):
    y = header_bottom
    c.setFont("Helvetica", 10)
    for row in rows:
        c.drawString(x, y, _row_line(row))
        y -= 16
    return 1


def _render_two_column(c: canvas.Canvas, rows, header_bottom, x=0.75 * inch):
    mid = len(rows) // 2 + len(rows) % 2
    left, right = rows[:mid], rows[mid:]
    c.setFont("Helvetica", 9)
    y = header_bottom
    for row in left:
        c.drawString(x, y, _row_line(row))
        y -= 16
    y = header_bottom
    for row in right:
        c.drawString(x + 3.6 * inch, y, _row_line(row))
        y -= 16
    return 1


def _render_table(c: canvas.Canvas, rows, header_bottom, x, grid: bool):
    data = [["Analyte", "Result", "Unit", "Reference Range"]]
    for row in rows:
        data.append([
            row.analyte_name_raw, row.value_raw, row.unit_raw,
            row.reference_range_raw or "",
        ])

    table = Table(data, colWidths=[2.2 * inch, 0.9 * inch, 0.9 * inch, 1.6 * inch])
    style = [
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]
    if grid:
        style.append(("GRID", (0, 0), (-1, -1), 0.5, colors.grey))
    else:
        style.append(("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.black))
    table.setStyle(TableStyle(style))

    w, h = table.wrapOn(c, 5.5 * inch, header_bottom)
    table.drawOn(c, x, header_bottom - h)
    return 1


def _render_multi_panel(c: canvas.Canvas, rows, header_bottom, x, patient_id):
    by_panel: dict[str, list[PrintedRow]] = {name: [] for name in _PANEL_GROUPS}
    leftover = []
    for row in rows:
        placed = False
        for panel_name, keys in _PANEL_GROUPS.items():
            if row.biomarker_key in {k.value for k in keys}:
                by_panel[panel_name].append(row)
                placed = True
                break
        if not placed:
            leftover.append(row)

    y = header_bottom
    pages = 1
    for panel_name, panel_rows in by_panel.items():
        if not panel_rows:
            continue
        if y < 2 * inch:
            c.showPage()
            pages += 1
            y = 9.5 * inch
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y, panel_name)
        y -= 18
        c.setFont("Helvetica", 9)
        for row in panel_rows:
            c.drawString(x, y, _row_line(row))
            y -= 15
        y -= 10

    if leftover:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y, "Other")
        y -= 18
        c.setFont("Helvetica", 9)
        for row in leftover:
            c.drawString(x, y, _row_line(row))
            y -= 15

    return pages


def render_report_pdf(
    out_path: Path,
    document_id: str,
    patient_id: str,
    lab_provider_name: str,
    patient_age_years: float,
    patient_sex: str,
    rows: list[PrintedRow],
    layout: str,
    accession_no: str,
) -> int:
    """Writes the PDF to out_path. Returns the page count."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out_path), pagesize=letter)
    x = 0.75 * inch
    header_bottom = _draw_header(
        c, x, 10 * inch, lab_provider_name, patient_age_years, patient_sex, accession_no
    )

    if layout == "single_column":
        pages = _render_single_column(c, rows, header_bottom, x)
    elif layout == "two_column":
        pages = _render_two_column(c, rows, header_bottom, x)
    elif layout == "boxed_table":
        pages = _render_table(c, rows, header_bottom, x, grid=True)
    elif layout == "borderless_table":
        pages = _render_table(c, rows, header_bottom, x, grid=False)
    elif layout == "header_heavy":
        c.setFont("Helvetica", 7)
        c.drawString(x, header_bottom + 20, "-" * 90)
        pages = _render_table(c, rows, header_bottom, x, grid=True)
    elif layout == "multi_panel":
        pages = _render_multi_panel(c, rows, header_bottom, x, patient_id)
    else:
        raise ValueError(f"Unknown layout: {layout}")

    c.save()
    return pages
