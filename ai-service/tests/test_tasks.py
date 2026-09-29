"""
Week 2 Step 2.2 acceptance: the task's business logic, exercised via
Celery's eager mode (task_always_eager=True), which runs a task inline
in the calling process instead of going through a real broker/worker --
the standard way to test Celery task logic without Redis. This tests
the actual `process_document_task` code path (retry/error handling
included), not just the plain function underneath it.
"""

import pytest

from app.ocr.pipeline import UnsupportedDocumentError
from app.workers.celery_app import celery_app
from app.workers.tasks import _serialize_result, process_document_task


@pytest.fixture(autouse=True)
def eager_mode():
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


class TestProcessDocumentTaskEager:
    def test_processes_a_real_document_end_to_end(self, clean_pdf_factory):
        path, ground_truth_rows = clean_pdf_factory(layout="single_column", max_rows=4)

        async_result = process_document_task.delay(
            str(path), document_id="doc-1", patient_id="pat-1"
        )
        result = async_result.get()

        assert result["document_id"] == "doc-1"
        assert result["has_text_layer"] is True
        assert len(result["observations"]) == len(ground_truth_rows)

        recovered_keys = {o["biomarker_key"] for o in result["observations"]}
        expected_keys = {r.biomarker_key for r in ground_truth_rows}
        assert expected_keys <= recovered_keys

    def test_result_is_json_serializable(self, clean_pdf_factory):
        import json

        path, _ = clean_pdf_factory(layout="single_column", max_rows=3)
        result = process_document_task.delay(
            str(path), document_id="doc-2", patient_id="pat-1"
        ).get()

        # Must not raise -- proves _serialize_result actually stripped
        # every non-JSON-native type (frozen dataclasses, enums).
        json.dumps(result)

    def test_unsupported_document_error_is_not_retried_into_a_generic_failure(
        self, scanned_pdf_factory
    ):
        from app.ocr.tesseract_engine import is_available

        if is_available().available:
            pytest.skip(
                "Tesseract is installed in this environment; "
                "this tests the missing-binary path."
            )

        scanned_path, _, _ = scanned_pdf_factory()

        # With task_eager_propagates=True, eager execution raises at
        # .delay() itself, not deferred to .get() -- that's the point
        # of the eager-propagates setting (surface task errors
        # immediately in tests rather than silently returning a
        # failed AsyncResult).
        with pytest.raises(UnsupportedDocumentError):
            process_document_task.delay(
                str(scanned_path), document_id="doc-scanned", patient_id="pat-1"
            )


class TestSerializeResult:
    def test_empty_observations_serializes_cleanly(self, clean_pdf_factory):
        import json

        from app.ocr.pipeline import process_document

        path, _ = clean_pdf_factory(layout="single_column", max_rows=1)
        result = process_document(path, document_id="d", patient_id="p")
        serialized = _serialize_result(result)
        json.dumps(serialized)
        assert "observations" in serialized
        assert "warnings" in serialized
