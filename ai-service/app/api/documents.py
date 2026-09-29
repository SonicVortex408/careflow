import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.validation import (
    InvalidFilename,
    InvalidPatientId,
    safe_filename,
    validate_patient_id,
)
from app.retrieval.patient_ingest import ingest_patient_document

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"]
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

UPLOAD_DIR = PROJECT_ROOT / "patient_documents"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


@router.post("/process")
async def process_document(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    document_id: str = Form(...)
):
    # =========================
    # 0. VALIDATE INPUT
    # =========================
    # patient_id and the uploaded filename both end up in a filesystem
    # path (patient_documents/<patient_id>/<filename>). Validate both
    # before any path is built -- see app/core/validation.py.
    try:
        patient_id = validate_patient_id(patient_id)
        clean_filename = safe_filename(file.filename)
    except (InvalidPatientId, InvalidFilename) as error:
        raise HTTPException(status_code=422, detail=str(error))

    try:

        # =========================
        # 1. PATIENT DIRECTORY
        # =========================

        patient_dir = (
            UPLOAD_DIR / patient_id
        )

        patient_dir.mkdir(
            parents=True,
            exist_ok=True
        )


        # =========================
        # 2. SAVE DOCUMENT
        # =========================

        file_path = (
            patient_dir / clean_filename
        )

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )


        # =========================
        # 3. INGEST DOCUMENT
        # =========================

        ingestion_result = (
            ingest_patient_document(
                patient_id=patient_id,
                document_id=document_id,
                file_path=file_path
            )
        )


        # =========================
        # 4. RETURN RESULT
        # =========================

        return {
            "success": True,
            "message": "Document uploaded and indexed successfully",

            "patient_id": patient_id,

            "document_id": document_id,

            "filename": clean_filename,

            "path": str(file_path),

            "chunks": ingestion_result["chunks"],

            "index_path": ingestion_result["index_path"]
        }

    except ValueError as error:
        # Unsupported file type, empty document, etc. -- a client error,
        # not a server error.
        raise HTTPException(status_code=422, detail=str(error))

    except Exception as error:
        # Previously this returned HTTP 200 with {"success": false},
        # which meant the backend's `aiResponse.ok` check never fired
        # and every caller had to remember to also check the body. A
        # processing failure is a server-side failure; return 500 so
        # HTTP-level error handling (retries, alerting, `!response.ok`
        # checks) works the way callers expect.
        print(
            "Document processing error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=f"Unable to process document: {error}",
        )
