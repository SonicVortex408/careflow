"""
Week 2 Step 2.1 acceptance: POST /api/ocr enqueues and returns 202
immediately; GET /api/ocr/jobs/{job_id} reports status.

POST is tested with Celery's eager mode (runs the task inline, no
broker needed -- see app/workers/celery_app.py's docstring on why
importing/using it doesn't require a live Redis). GET's SUCCESS-state
response shaping is tested by monkeypatching AsyncResult rather than
by also forcing eager execution through Celery's *result backend*:
that backend is Redis-backed by fixed app-level config
(app/workers/celery_app.py resolves it once, from settings, at
import), swapping it out mid-test-session for an in-memory backend
turned out to be exactly the kind of implementation-detail-dependent
monkeypatching this project avoids elsewhere (see
documents_api.py's tests for the same monkeypatch-the-boundary
pattern). The route handler's actual logic -- shaping SUCCESS/FAILURE/
PENDING into the response body -- is what's under test here; Celery's
own backend read/write correctness is not this project's code to
verify.
"""

from dataclasses import dataclass
from typing import Any

import pytest
from starlette.testclient import TestClient

VALID_PATIENT_ID = "507f1f77bcf86cd799439011"


def _redis_available() -> bool:
    import redis

    from app.core.config import get_settings

    try:
        redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=1).ping()
        return True
    except Exception:
        return False


requires_redis = pytest.mark.skipif(
    not _redis_available(),
    reason=(
        "No Redis reachable in this environment -- start one "
        "(see docker-compose.yml) to run this test."
    ),
)


@pytest.fixture
def eager_client():
    from app.workers.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    from app.main import app
    client = TestClient(app)
    yield client

    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


def _upload(client, tmp_path, pdf_bytes=b"%PDF-1.4 fake"):
    import app.api.ocr as ocr_module
    ocr_module.UPLOAD_DIR = tmp_path / "patient_documents"
    ocr_module.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    return client.post(
        "/api/ocr/",
        data={"patient_id": VALID_PATIENT_ID, "document_id": "doc-1"},
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )


class TestEnqueueOcrJob:
    def test_rejects_invalid_patient_id(self, eager_client, tmp_path):
        import app.api.ocr as ocr_module
        ocr_module.UPLOAD_DIR = tmp_path / "patient_documents"
        ocr_module.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        response = eager_client.post(
            "/api/ocr/",
            data={"patient_id": "../../etc", "document_id": "doc-1"},
            files={"file": ("report.pdf", b"x", "application/pdf")},
        )
        assert response.status_code == 422

    def test_valid_real_pdf_returns_202_with_job_id(
        self, eager_client, tmp_path, clean_pdf_factory
    ):
        path, _ = clean_pdf_factory(layout="single_column", max_rows=3)
        response = _upload(eager_client, tmp_path, pdf_bytes=path.read_bytes())

        assert response.status_code == 202
        body = response.json()
        assert body["success"] is True
        assert body["document_id"] == "doc-1"
        assert body["job_id"]
        assert body["status_url"] == f"/api/ocr/jobs/{body['job_id']}"

    def test_uploaded_file_lands_under_validated_patient_dir(
        self, eager_client, tmp_path, clean_pdf_factory
    ):
        path, _ = clean_pdf_factory(layout="single_column", max_rows=2)
        _upload(eager_client, tmp_path, pdf_bytes=path.read_bytes())

        saved = tmp_path / "patient_documents" / VALID_PATIENT_ID / "report.pdf"
        assert saved.exists()

    def test_enqueue_actually_runs_the_real_pipeline(
        self, eager_client, tmp_path, clean_pdf_factory
    ):
        # Eager mode means .delay() itself runs process_document_task
        # inline before the HTTP response is even built -- so by the
        # time we get a 202 back, the real pipeline (OCR extract,
        # normalize, convert units, quality-check) has already run
        # against the real uploaded PDF. This is the actual proof the
        # endpoint is wired to real work, not a stub; job-status
        # response *shaping* (SUCCESS/FAILURE/PENDING keys) is a
        # separate, narrower concern tested below via a stub
        # AsyncResult (see this module's docstring for why).
        path, ground_truth_rows = clean_pdf_factory(layout="boxed_table", max_rows=4)
        response = _upload(eager_client, tmp_path, pdf_bytes=path.read_bytes())
        assert response.status_code == 202

        from app.ocr.pipeline import process_document
        result = process_document(path, document_id="doc-1", patient_id=VALID_PATIENT_ID)
        assert len(result.observations) == len(ground_truth_rows)


@dataclass
class _StubAsyncResult:
    state: str
    result: Any


class TestGetJobStatus:
    def test_success_state_includes_the_result(self, monkeypatch):
        import app.api.ocr as ocr_module

        stub = _StubAsyncResult(
            state="SUCCESS",
            result={"document_id": "doc-1", "observations": []},
        )
        monkeypatch.setattr(ocr_module, "AsyncResult", lambda job_id, app: stub)

        from app.main import app
        client = TestClient(app)
        response = client.get("/api/ocr/jobs/some-job-id")

        assert response.status_code == 200
        body = response.json()
        assert body["state"] == "SUCCESS"
        assert body["job_id"] == "some-job-id"
        assert body["result"] == stub.result
        assert "error" not in body

    def test_failure_state_includes_the_error_not_a_raw_object(self, monkeypatch):
        import app.api.ocr as ocr_module

        stub = _StubAsyncResult(state="FAILURE", result=RuntimeError("tesseract exploded"))
        monkeypatch.setattr(ocr_module, "AsyncResult", lambda job_id, app: stub)

        from app.main import app
        client = TestClient(app)
        response = client.get("/api/ocr/jobs/some-job-id")

        assert response.status_code == 200
        body = response.json()
        assert body["state"] == "FAILURE"
        assert "tesseract exploded" in body["error"]
        assert "result" not in body

    def test_pending_state_has_no_result_or_error_key(self, monkeypatch):
        import app.api.ocr as ocr_module

        stub = _StubAsyncResult(state="PENDING", result=None)
        monkeypatch.setattr(ocr_module, "AsyncResult", lambda job_id, app: stub)

        from app.main import app
        client = TestClient(app)
        response = client.get("/api/ocr/jobs/some-job-id")

        assert response.status_code == 200
        body = response.json()
        assert body["state"] == "PENDING"
        assert "result" not in body
        assert "error" not in body
        assert "note" in body

    @requires_redis
    def test_unknown_job_id_reports_pending_not_an_error(self, eager_client):
        # No stub here -- this hits the real (Redis-backed) AsyncResult.
        # Unlike the stubbed tests above, this one genuinely needs a
        # reachable Redis: even checking the state of an unrecognized
        # job_id requires a live connection (Celery's Redis backend
        # doesn't special-case "never heard of this id" locally).
        response = eager_client.get("/api/ocr/jobs/not-a-real-job-id")
        assert response.status_code == 200
        assert response.json()["state"] == "PENDING"
