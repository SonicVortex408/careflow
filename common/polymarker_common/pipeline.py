"""Document -> canonical JSON: the ingestion path shared by the Celery worker
(one upload) and the bda_engine batch OCR job (thousands of PDFs).

    OCR/text layer -> parse rows + metadata -> LOINC/unit normalization -> quality checks
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from polymarker_common.catalog import catalog_version
from polymarker_common.normalizer import normalize_result
from polymarker_common.parser import parse_report_text
from polymarker_common.quality import check_report

PIPELINE_VERSION = "1.0.0"


def ingest_lines(
    lines: list[str],
    line_confidences: list[float] | None = None,
    *,
    sex: str | None = None,
    population_stats: dict | None = None,
    ocr_method: str = "unknown",
) -> dict[str, Any]:
    parsed = parse_report_text(lines, line_confidences)
    sex = sex or parsed.metadata.sex
    normalized = []
    flags: dict[int, str | None] = {}
    rejected: list[dict[str, Any]] = []
    for row in parsed.rows:
        try:
            result = normalize_result(
                row.label,
                f"{row.qualifier or ''}{row.value}",
                row.unit,
                sex=sex,
                ocr_confidence=row.ocr_confidence,
                lab_reference=row.reference_text,
            )
        except ValueError as exc:
            rejected.append({"line": row.line, "reason": str(exc)})
            continue
        if result is None:
            continue
        flags[len(normalized)] = row.flag
        normalized.append(result)
    quality = check_report(normalized, sex=sex, population_stats=population_stats, flags=flags)
    return {
        "pipeline_version": PIPELINE_VERSION,
        "catalog_version": catalog_version(),
        "ocr_method": ocr_method,
        "metadata": parsed.metadata.to_dict(),
        "raw_rows": [r.to_dict() for r in parsed.rows],
        "rejected_rows": rejected,
        "biomarkers": [r.to_dict() for r in quality.accepted],
        "quality": {
            "issues": [i.to_dict() for i in quality.issues],
            "completeness": quality.completeness,
            "missing_markers": quality.missing_markers,
            "needs_clinician_attention": quality.needs_clinician_attention,
            "checks_run": quality.checks_run,
        },
        "line_count": parsed.line_count,
    }


def ingest_document(
    path: str | Path,
    *,
    sex: str | None = None,
    population_stats: dict | None = None,
    engine: str | None = None,
) -> dict[str, Any]:
    from polymarker_common.ocr import extract_text

    ocr = extract_text(path, engine=engine)
    result = ingest_lines(
        ocr.lines,
        ocr.line_confidences,
        sex=sex,
        population_stats=population_stats,
        ocr_method=ocr.method,
    )
    result["ocr"] = {
        "method": ocr.method,
        "pages": ocr.pages,
        "mean_confidence": ocr.mean_confidence,
        "warnings": ocr.warnings,
    }
    return result
