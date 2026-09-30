"""General medical documents for the assistant (non-lab uploads).

POST /api/documents/process  -> 202 {job_id}; poll /api/ocr/jobs/{job_id}.
Previously this indexed synchronously and returned 200 with success:false on
failure; it is now an async job with proper HTTP status codes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.security import require_internal_key, safe_child, safe_suffix, validate_object_id
from app.services.jobs import get_jobs

router = APIRouter(
    prefix="/api/documents", tags=["documents"], dependencies=[Depends(require_internal_key)]
)


@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
async def process_document(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    document_id: str = Form(...),
):
    s = get_settings()
    pid = validate_object_id(patient_id)
    did = validate_object_id(document_id, "document_id")
    suffix = safe_suffix(file.filename, (".pdf", ".txt"))
    directory = safe_child(s.patient_documents_dir, pid)
    directory.mkdir(parents=True, exist_ok=True)
    path = safe_child(directory, f"doc-{did}{suffix}")
    data = await file.read(s.max_upload_bytes + 1)
    if len(data) > s.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File too large")
    path.write_bytes(data)
    job_id = get_jobs().submit(
        "index_document", {"path": str(path), "patient_id": pid, "document_id": did}
    )
    return {"job_id": job_id, "status": "queued", "document_id": did}
