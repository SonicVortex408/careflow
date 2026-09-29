"""Plain task functions. Celery tasks and the local executor both call these."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def process_report(payload: dict[str, Any]) -> dict[str, Any]:
    from app.retrieval.patient_index import index_patient_text
    from app.services.interpretation import interpret_document

    path = Path(payload["path"])
    result = interpret_document(
        path,
        proms=payload.get("proms"),
        sex=payload.get("sex"),
        age=payload.get("age"),
        report_id=payload.get("report_id"),
    )
    # Best effort: make the report searchable by the patient's assistant.
    try:
        lines = [
            f"{b['display']}: {b['raw_value']} {b['raw_unit']} (normalized {b['value']} {b['unit']})"
            for b in result["extraction"]["biomarkers"]
        ]
        indexed = index_patient_text(
            payload["patient_id"],
            payload.get("report_id", ""),
            "\n".join(lines),
            source="lab_report",
        )
        result["indexed_for_assistant"] = indexed
    except Exception as exc:  # noqa: BLE001
        logger.warning("Patient indexing skipped: %s", type(exc).__name__)
        result["indexed_for_assistant"] = False
    return result


def index_document(payload: dict[str, Any]) -> dict[str, Any]:
    from app.retrieval.patient_index import index_patient_file

    chunks = index_patient_file(
        payload["patient_id"], payload["document_id"], Path(payload["path"])
    )
    return {"document_id": payload["document_id"], "chunks": chunks}


TASKS = {"process_report": process_report, "index_document": index_document}
