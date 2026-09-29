"""End-to-end interpretation (Week 11): the unified output JSON.

    document -> OCR -> normalize (LOINC + SI) -> quality checks
             -> cohort inference (cluster, bands, risk, SHAP)
             -> knowledge-graph evidence chains
             -> GraphRAG summary -> deterministic guardrails
             -> escalation + appointment guide + audit trail

The result is *not* shown to the patient by this service: the backend stores it
as ``pending_clinician_review`` and releases it only after clinician sign-off.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services import guardrails
from app.services.evidence import evidence_for
from app.services.inference import run_inference
from app.services.model_registry import ArtifactError, get_registry
from app.services.summary import appointment_guide, generate_summary
from polymarker_common.catalog import SYNTHETIC_DATA_LABEL
from polymarker_common.proms import Proms

logger = logging.getLogger(__name__)
SCHEMA_VERSION = "1.0.0"


def population_stats() -> dict | None:
    registry = get_registry()
    if not registry.available:
        return None
    try:
        return registry.json("population_stats")["stats"]
    except ArtifactError:
        return None


def _validated_proms(proms: dict | None) -> dict | None:
    if not proms:
        return None
    try:
        return Proms.from_dict(proms).to_dict()
    except (KeyError, ValueError, TypeError):
        logger.info("Ignoring invalid PROMs payload")
        return None


def interpret(
    extraction: dict[str, Any],
    *,
    proms: dict | None = None,
    sex: str | None = None,
    age: float | None = None,
    report_id: str | None = None,
) -> dict[str, Any]:
    """Interpret an extraction (canonical report JSON from polymarker_common.pipeline)."""
    t0 = time.perf_counter()
    meta = extraction.get("metadata") or {}
    sex = sex or meta.get("sex")
    age = age if age is not None else meta.get("age")
    proms = _validated_proms(proms)
    markers = {b["key"]: b["value"] for b in extraction.get("biomarkers", [])}
    quality = extraction.get("quality") or {}

    inference = run_inference(markers, sex=sex, age=age, proms=proms)
    evidence = evidence_for(markers, proms)
    escalation = guardrails.evaluate_escalation(markers, proms, quality.get("issues"))
    context = {
        "bands": inference["bands"],
        "cluster": inference.get("cluster"),
        "risk": inference.get("risk"),
        "evidence": evidence,
        "quality": quality,
        "reported_values": {
            b["key"]: {"raw_value": b.get("raw_value"), "raw_unit": b.get("raw_unit")}
            for b in extraction.get("biomarkers", [])
        },
    }
    summary = generate_summary(context, escalation)
    return {
        "schema_version": SCHEMA_VERSION,
        "report_id": report_id,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "label": SYNTHETIC_DATA_LABEL,
        "disclaimer": guardrails.DISCLAIMER,
        "extraction": {
            "metadata": meta,
            "biomarkers": extraction.get("biomarkers", []),
            "quality": quality,
            "ocr": extraction.get("ocr"),
            "pipeline_version": extraction.get("pipeline_version"),
            "catalog_version": extraction.get("catalog_version"),
        },
        "proms": proms,
        "analytics": {
            "models_available": inference["models_available"],
            "model_version": inference.get("model_version"),
            "bands": inference["bands"],
            "cluster": inference.get("cluster"),
            "risk": inference.get("risk"),
            "imputed_markers": inference.get("imputed_markers", []),
            "note": inference.get("note"),
            "label": SYNTHETIC_DATA_LABEL,
        },
        "evidence": evidence,
        "summary": {
            "text": summary.text,
            "source": summary.source,
            "readability_grade": summary.readability_grade,
            "attempts": summary.attempts,
        },
        "guardrails": {
            "passed": summary.passed,
            "violations": [v.__dict__ for v in summary.violations],
            "audit": summary.audit,
            "version": guardrails.GUARDRAILS_VERSION,
        },
        "escalation": summary.escalation,
        "appointment_guide": appointment_guide(context, escalation),
        "review": {"required": True, "status": "pending_clinician_review"},
        "timing_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def interpret_document(
    path: Path,
    *,
    proms: dict | None = None,
    sex: str | None = None,
    age: float | None = None,
    report_id: str | None = None,
) -> dict[str, Any]:
    from app.core.config import get_settings
    from polymarker_common.pipeline import ingest_document

    t0 = time.perf_counter()
    extraction = ingest_document(
        path, sex=sex, population_stats=population_stats(), engine=get_settings().ocr_engine
    )
    result = interpret(extraction, proms=proms, sex=sex, age=age, report_id=report_id)
    result["timing_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return result
