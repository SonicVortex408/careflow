"""Report ingestion: enqueue OCR + interpretation, poll job status.

POST /api/ocr                 multipart: file, report_id, patient_id[, proms, sex, age] -> 202 {job_id}
GET  /api/ocr/jobs/{job_id}   {job_id, status: queued|processing|completed|failed, result?, error?}
POST /api/interpret           structured markers (manual entry / re-interpretation) -> interpretation
"""

from __future__ import annotations

import json
import re
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.security import require_internal_key, safe_child, safe_suffix, validate_object_id
from app.services.jobs import get_jobs

router = APIRouter(prefix="/api", tags=["ingestion"], dependencies=[Depends(require_internal_key)])

ALLOWED_SUFFIXES = (".pdf", ".txt", ".png", ".jpg", ".jpeg")
_JOB_ID = re.compile(r"^[0-9a-f-]{36}$")


def _parse_proms(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="proms must be JSON") from exc
    return data if isinstance(data, dict) else None


@router.post("/ocr", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_report(
    file: UploadFile = File(...),
    report_id: str = Form(...),
    patient_id: str = Form(...),
    proms: str | None = Form(None),
    sex: str | None = Form(None),
    age: float | None = Form(None),
):
    s = get_settings()
    pid = validate_object_id(patient_id)
    rid = validate_object_id(report_id, "report_id")
    suffix = safe_suffix(file.filename, ALLOWED_SUFFIXES)
    directory = safe_child(s.patient_documents_dir, pid)
    directory.mkdir(parents=True, exist_ok=True)
    path = safe_child(directory, f"{rid}{suffix}")
    written = 0
    with open(path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > s.max_upload_bytes:
                out.close()
                path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large")
            out.write(chunk)
    job_id = get_jobs().submit(
        "process_report",
        {
            "path": str(path),
            "report_id": rid,
            "patient_id": pid,
            "proms": _parse_proms(proms),
            "sex": (sex or None),
            "age": age,
        },
    )
    return {"job_id": job_id, "status": "queued", "report_id": rid}


@router.get("/ocr/jobs/{job_id}")
def job_status(job_id: str):
    if not _JOB_ID.match(job_id):
        raise HTTPException(status_code=422, detail="Invalid job id")
    job = get_jobs().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


class MarkerInput(BaseModel):
    label: str = Field(..., description="lab label, e.g. 'Free T4' or a catalog key")
    value: str | float
    unit: str | None = None


class InterpretRequest(BaseModel):
    patient_id: str
    report_id: str | None = None
    biomarkers: list[MarkerInput]
    proms: dict | None = None
    sex: str | None = None
    age: float | None = None


@router.post("/interpret")
def interpret_structured(req: InterpretRequest):
    from app.services.interpretation import interpret, population_stats
    from polymarker_common.normalizer import normalize_result
    from polymarker_common.quality import check_report

    validate_object_id(req.patient_id)
    results, rejected = [], []
    for m in req.biomarkers:
        try:
            r = normalize_result(m.label, m.value, m.unit, sex=req.sex)
        except ValueError as exc:
            rejected.append({"label": m.label, "reason": str(exc)})
            continue
        if r is None:
            rejected.append({"label": m.label, "reason": "not a target biomarker"})
        else:
            results.append(r)
    quality = check_report(results, sex=req.sex, population_stats=population_stats())
    extraction = {
        "metadata": {"sex": req.sex, "age": req.age, "lab_provider": None, "collected_at": None},
        "biomarkers": [r.to_dict() for r in quality.accepted],
        "quality": quality.to_dict() | {"rejected": rejected},
        "ocr": {"method": "structured_input"},
    }
    return interpret(extraction, proms=req.proms, sex=req.sex, age=req.age, report_id=req.report_id)


def _cleanup(path) -> None:  # pragma: no cover - utility for admin scripts
    shutil.rmtree(path, ignore_errors=True)
