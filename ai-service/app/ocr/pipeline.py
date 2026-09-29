"""
Week 2 + Week 3 integration: the full document -> observations pipeline.

This is the plain-function core that app/workers/tasks.py wraps as a
Celery task chain (see that module for why it's split this way: the
business logic here is directly unit-testable without a broker, and
the Celery layer is a thin, mostly-untestable-without-Redis shim
around it).

    router.inspect_document
      -> text_layer.extract_words              (has_text_layer=True)
         | raster.prepare_for_ocr + tesseract_engine.extract_words_from_image
                                                 (has_text_layer=False)
      -> table_reconstruct.reconstruct_rows
      -> field_extract.{extract_age,extract_sex,extract_accession,extract_lab_provider}
      -> normalizer.map_analyte_name  (per row)
      -> units.convert                (per row, using the extracted/parsed value)
      -> ref_range.parse_reference_range (per row, using the extracted sex)
      -> data_quality.run_quality_checks (per row, with sibling context)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from app.ocr.common import PageWords
from app.ocr.field_extract import (
    extract_accession,
    extract_age,
    extract_lab_provider,
    extract_sex,
)
from app.ocr.router import inspect_document
from app.ocr.table_reconstruct import RowCandidate, default_known_units, reconstruct_rows
from app.ocr.text_layer import extract_words
from app.services.common_types import Comparator
from app.services.data_quality import run_quality_checks
from app.services.normalizer import map_analyte_name
from app.services.ref_range import parse_reference_range
from app.services.units import convert

_VALUE_PARSE_RE = re.compile(r"^([<>≤≥]?)\s*(\d+\.?\d*)$")


class UnsupportedDocumentError(Exception):
    """Raised when a document needs an OCR engine this build can't run
    (e.g. OCR_ENGINE=tesseract but the binary isn't installed) --
    distinct from a genuine extraction failure, so callers can
    distinguish "install Tesseract" from "this document is corrupt"."""


@dataclass(frozen=True)
class ObservationResult:
    row_id: str
    document_id: str
    patient_id: str
    biomarker_key: str | None
    loinc_code: str | None
    mapping_method: str
    mapping_confidence: float
    value_canonical: float | None
    unit_canonical: str | None
    value_source: float | None
    unit_source: str
    conversion_factor: float | None
    conversion_source: str | None
    ref_low_canonical: float | None
    ref_high_canonical: float | None
    quality_status: str
    quality_checks: list
    needs_review: bool
    analyte_name_raw: str
    value_raw: str
    reference_range_raw: str | None
    ocr_confidence: float


@dataclass(frozen=True)
class DocumentResult:
    document_id: str
    patient_id: str
    has_text_layer: bool
    patient_age: str | None
    patient_sex: str | None
    accession: str | None
    lab_provider: str | None
    observations: list[ObservationResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _parse_value(value_raw: str) -> tuple[float | None, Comparator]:
    match = _VALUE_PARSE_RE.match(value_raw.strip())
    if not match:
        return None, Comparator.NONE
    comparator_str, number_str = match.groups()
    comparator_map = {
        "<": Comparator.LT, "≤": Comparator.LT,
        ">": Comparator.GT, "≥": Comparator.GT,
    }
    return float(number_str), comparator_map.get(comparator_str, Comparator.NONE)


def _get_pages(pdf_path: Path, has_text_layer: bool) -> list[PageWords]:
    if has_text_layer:
        return list(extract_words(pdf_path))

    from app.core.config import get_settings
    settings = get_settings()

    if settings.ocr_engine != "tesseract":
        raise UnsupportedDocumentError(
            f"OCR_ENGINE={settings.ocr_engine!r} is not implemented in this build "
            "(only 'tesseract' is). See docs/WEEKS_1-3_STATUS_AND_PLAN.md Week 2 gaps."
        )

    from app.ocr.raster import prepare_for_ocr
    from app.ocr.tesseract_engine import extract_words_from_image, is_available

    availability = is_available()
    if not availability.available:
        raise UnsupportedDocumentError(
            f"Tesseract binary not available: {availability.error}. "
            "See app/ocr/tesseract_engine.py's docstring to install it."
        )

    raster_pages = prepare_for_ocr(pdf_path)
    return [
        extract_words_from_image(p.image, p.page_no, p.dpi)
        for p in raster_pages
    ]


def _observation_for_row(
    row: RowCandidate, document_id: str, patient_id: str, patient_sex: str | None,
    sibling_keys: list[str],
) -> ObservationResult:
    mapping = map_analyte_name(row.analyte_name_raw)

    value_numeric, _comparator = _parse_value(row.value_raw)

    conversion = None
    if mapping.biomarker_key is not None and value_numeric is not None and row.unit_raw:
        conversion = convert(mapping.biomarker_key, value_numeric, row.unit_raw)

    ref_low = ref_high = None
    if row.reference_range_raw:
        ref_result = parse_reference_range(row.reference_range_raw, patient_sex=patient_sex)
        if ref_result.parsed and mapping.biomarker_key and row.unit_raw:
            if ref_result.ref_low is not None:
                lo_conv = convert(mapping.biomarker_key, ref_result.ref_low, row.unit_raw)
                ref_low = lo_conv.value_canonical if lo_conv.unit_recognized else None
            if ref_result.ref_high is not None:
                hi_conv = convert(mapping.biomarker_key, ref_result.ref_high, row.unit_raw)
                ref_high = hi_conv.value_canonical if hi_conv.unit_recognized else None

    value_canonical = conversion.value_canonical if conversion else None
    unit_canonical = conversion.unit_canonical if conversion else None

    quality = run_quality_checks(
        biomarker_key=mapping.biomarker_key,
        value_canonical=value_canonical,
        ref_low=ref_low,
        ref_high=ref_high,
        flag_raw=None,
        sibling_biomarker_keys=sibling_keys,
    )

    return ObservationResult(
        row_id=f"{document_id}:row{row.row_index}",
        document_id=document_id,
        patient_id=patient_id,
        biomarker_key=mapping.biomarker_key,
        loinc_code=mapping.loinc_code,
        mapping_method=mapping.mapping_method,
        mapping_confidence=mapping.mapping_confidence,
        value_canonical=value_canonical,
        unit_canonical=unit_canonical,
        value_source=value_numeric,
        unit_source=row.unit_raw or "",
        conversion_factor=conversion.conversion_factor if conversion else None,
        conversion_source=conversion.conversion_source if conversion else None,
        ref_low_canonical=ref_low,
        ref_high_canonical=ref_high,
        quality_status=quality.status,
        quality_checks=list(quality.checks),
        needs_review=mapping.needs_review or quality.status != "ok",
        analyte_name_raw=row.analyte_name_raw,
        value_raw=row.value_raw,
        reference_range_raw=row.reference_range_raw,
        ocr_confidence=row.confidence,
    )


def process_document(
    pdf_path: Path, document_id: str, patient_id: str, known_providers: list[str] | None = None,
) -> DocumentResult:
    """The full pipeline, called with a document already on disk (the
    Celery task in app/workers/tasks.py handles fetching/queueing;
    this function is deliberately I/O-minimal and synchronous so it's
    trivial to unit test)."""

    from app.services.reference_data import load_lab_providers

    layer_info = inspect_document(pdf_path)
    pages = _get_pages(pdf_path, layer_info.has_text_layer)

    full_text = "\n".join(w.text for page in pages for w in page.words)
    # pdfplumber/tesseract emit words without the spacing a human reader
    # sees; join with spaces too, for field_extract's regexes which
    # expect e.g. "45Y / F" or "45Y/F" -- both survive either join, but
    # a space-joined version also matches "Age: 45" style single-token
    # sequences correctly.
    full_text_spaced = " ".join(w.text for page in pages for w in page.words)

    age = extract_age(full_text_spaced)
    sex = extract_sex(full_text_spaced)
    accession = extract_accession(full_text_spaced)

    providers = known_providers or sorted({r.canonical_name for r in load_lab_providers()})
    provider = extract_lab_provider(full_text, providers)

    unit_set = default_known_units()
    rows = reconstruct_rows(pages, unit_set)

    observations = []
    for i, row in enumerate(rows):
        sibling_keys = [
            map_analyte_name(other.analyte_name_raw).biomarker_key
            for j, other in enumerate(rows) if j != i
        ]
        observations.append(
            _observation_for_row(row, document_id, patient_id, sex.value, sibling_keys)
        )

    warnings = []
    if not rows:
        warnings.append("No data rows were recovered from this document.")

    return DocumentResult(
        document_id=document_id,
        patient_id=patient_id,
        has_text_layer=layer_info.has_text_layer,
        patient_age=age.value,
        patient_sex=sex.value,
        accession=accession.value,
        lab_provider=provider.value,
        observations=observations,
        warnings=warnings,
    )
