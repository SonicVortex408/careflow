"""
Manual smoke test for the per-patient ingestion pipeline.

Not a test -- it downloads/loads the sentence-transformers embedding
model and writes a real FAISS index to disk. Requires a file at
patient_documents/<patient_id>/test-report.txt (create one yourself;
it is gitignored on purpose -- see .gitignore).

Run from the ai-service/ directory:
    uv run python scripts/manual_patient_ingest.py [patient_id] [document_id]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.retrieval.patient_ingest import ingest_patient_document

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PATIENT_ID = "6a9d17d6b74cef0c8858926a"
DEFAULT_DOCUMENT_ID = "6a9d1beda340dcbab8e1bf0f"


def main():
    patient_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATIENT_ID
    document_id = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DOCUMENT_ID

    file_path = (
        PROJECT_ROOT
        / "patient_documents"
        / patient_id
        / "test-report.txt"
    )

    if not file_path.exists():
        print(f"Missing fixture file: {file_path}")
        print("Create it first (a plain .txt lab report works fine).")
        sys.exit(1)

    result = ingest_patient_document(
        patient_id=patient_id,
        document_id=document_id,
        file_path=file_path
    )

    print(result)


if __name__ == "__main__":
    main()
