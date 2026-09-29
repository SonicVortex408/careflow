"""
POST /api/documents/process: input validation and the HTTP status-code
contract fix (previously always 200, even on failure -- see
WEEKS_1-3_STATUS_AND_PLAN.md Phase 0, item 6).

The real ingestion function (embeddings + FAISS) is monkeypatched out;
these tests are about the HTTP layer, not the retrieval pipeline.
"""

from starlette.testclient import TestClient

VALID_PATIENT_ID = "507f1f77bcf86cd799439011"


def _client(monkeypatch, tmp_path, ingest_result=None, ingest_error=None):
    import app.api.documents as documents_module

    documents_module.UPLOAD_DIR = tmp_path / "patient_documents"
    documents_module.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def fake_ingest(patient_id, document_id, file_path):
        if ingest_error is not None:
            raise ingest_error
        return ingest_result or {
            "patient_id": patient_id,
            "document_id": document_id,
            "filename": file_path.name,
            "chunks": 3,
            "index_path": str(file_path.parent),
        }

    monkeypatch.setattr(documents_module, "ingest_patient_document", fake_ingest)

    from app.main import app
    return TestClient(app)


def test_rejects_invalid_patient_id_with_422(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/api/documents/process",
        data={"patient_id": "../../etc", "document_id": "doc-1"},
        files={"file": ("report.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 422


def test_accepts_valid_request_and_returns_200(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/api/documents/process",
        data={"patient_id": VALID_PATIENT_ID, "document_id": "doc-1"},
        files={"file": ("report.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["patient_id"] == VALID_PATIENT_ID

    # The file must actually land under the validated patient_id
    # directory, sanitised.
    saved = tmp_path / "patient_documents" / VALID_PATIENT_ID / "report.txt"
    assert saved.exists()


def test_path_traversal_filename_is_sanitised_before_saving(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/api/documents/process",
        data={"patient_id": VALID_PATIENT_ID, "document_id": "doc-1"},
        files={"file": ("../../../evil.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 200

    # Must never escape the patient's own upload directory.
    escaped = tmp_path / "evil.txt"
    assert not escaped.exists()

    saved = tmp_path / "patient_documents" / VALID_PATIENT_ID / "evil.txt"
    assert saved.exists()


def test_ingestion_failure_returns_500_not_200(monkeypatch, tmp_path):
    client = _client(
        monkeypatch, tmp_path,
        ingest_error=RuntimeError("embedding model unavailable"),
    )

    response = client.post(
        "/api/documents/process",
        data={"patient_id": VALID_PATIENT_ID, "document_id": "doc-1"},
        files={"file": ("report.txt", b"hello", "text/plain")},
    )

    # Previously this endpoint returned 200 with {"success": false} on
    # any exception, so `!response.ok` checks on the caller side never
    # fired. A processing failure must be a non-2xx response.
    assert response.status_code == 500


def test_unsupported_file_type_returns_422(monkeypatch, tmp_path):
    client = _client(
        monkeypatch, tmp_path,
        ingest_error=ValueError("Unsupported document type: .exe"),
    )

    response = client.post(
        "/api/documents/process",
        data={"patient_id": VALID_PATIENT_ID, "document_id": "doc-1"},
        files={"file": ("malware.exe", b"hello", "application/octet-stream")},
    )

    assert response.status_code == 422
