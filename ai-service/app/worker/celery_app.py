"""Celery application (broker + result backend: Redis).

celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
"""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

_s = get_settings()

celery_app = Celery("polymarker", broker=_s.broker_url, backend=_s.result_backend)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=_s.job_result_ttl_seconds,
    task_time_limit=600,
    task_soft_time_limit=540,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="polymarker.process_report", bind=True, max_retries=2)
def process_report_task(self, payload: dict) -> dict:
    from app.worker.tasks_impl import process_report

    return process_report(payload)


@celery_app.task(name="polymarker.index_document")
def index_document_task(payload: dict) -> dict:
    from app.worker.tasks_impl import index_document

    return index_document(payload)
