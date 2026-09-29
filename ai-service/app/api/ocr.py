"""
Week 2, Step 2.1: the async ingestion job API.

POST /api/ocr enqueues and returns 202 immediately (no HTTP request
ever blocks on OCR -- the gap documented in
docs/WEEKS_1-3_STATUS_AND_PLAN.md as "the whole chain runs inside one
synchronous Express request" is closed on the ai-service side here;
backend/src/controllers/documentController.js switching to call this
instead of POST /api/documents/process is the matching backend-side
follow-up, not yet wired in this change).

GET /api/ocr/jobs/{job_id} polls Celery's own result backend (Redis)
directly via AsyncResult -- no separate job-status table to keep in
sync.
"""

import shutil
from pathlib import Path

from celery.result import AsyncResult
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.validation import (
    InvalidFilename,
    InvalidPatientId,
    safe_filename,
    validate_patient_id,
)
from app.workers.celery_app import celery_app
from app.workers.tasks import process_document_task

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_ROOT / "patient_documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/", status_code=202)
async def enqueue_ocr_job(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    document_id: str = Form(...),
):
    try:
        patient_id = validate_patient_id(patient_id)
        clean_filename = safe_filename(file.filename)
    except (InvalidPatientId, InvalidFilename) as error:
        raise HTTPException(status_code=422, detail=str(error))

    patient_dir = UPLOAD_DIR / patient_id
    patient_dir.mkdir(parents=True, exist_ok=True)
    file_path = patient_dir / clean_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    job = process_document_task.delay(str(file_path), document_id, patient_id)

    return {
        "success": True,
        "document_id": document_id,
        "job_id": job.id,
        "status_url": f"/api/ocr/jobs/{job.id}",
    }


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    # job_id is a Celery task UUID, not a 24-hex ObjectId -- no
    # path-traversal surface here the way patient_id/filename have
    # elsewhere, since AsyncResult only reads from the configured
    # result backend (Redis) by key, never touches the filesystem.
    result = AsyncResult(job_id, app=celery_app)

    body = {
        "job_id": job_id,
        "state": result.state,  # PENDING | STARTED | SUCCESS | FAILURE | RETRY
    }

    if result.state == "SUCCESS":
        body["result"] = result.result
    elif result.state == "FAILURE":
        body["error"] = str(result.result)
    elif result.state == "PENDING":
        # Celery cannot distinguish "unknown job_id" from "queued, not
        # yet started" -- both report PENDING. Callers should treat a
        # PENDING job_id they didn't themselves just create as
        # suspect after a reasonable timeout, not as a guarantee it
        # will eventually run.
        body["note"] = "PENDING means either queued or an unrecognized job_id."

    return body
