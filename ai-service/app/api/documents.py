from fastapi import APIRouter, UploadFile, File, Form
from pathlib import Path
import shutil

from app.retrieval.patient_ingest import (
    ingest_patient_document
)


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
            patient_dir / file.filename
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

            "filename": file.filename,

            "path": str(file_path),

            "chunks": ingestion_result["chunks"],

            "index_path": ingestion_result["index_path"]
        }


    except Exception as error:

        print(
            "Document processing error:",
            error
        )

        return {
            "success": False,
            "message": "Unable to process document",
            "error": str(error)
        }
