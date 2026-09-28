from pathlib import Path

from app.retrieval.patient_ingest import (
    ingest_patient_document
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

file_path = (
    PROJECT_ROOT
    / "patient_documents"
    / "6a9d17d6b74cef0c8858926a"
    / "test-report.txt"
)


result = ingest_patient_document(
    patient_id="6a9d17d6b74cef0c8858926a",
    document_id="6a9d1beda340dcbab8e1bf0f",
    file_path=file_path
)


print(result)