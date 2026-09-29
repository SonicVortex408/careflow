"""
Week 2, Step 2.2: the Celery application.

Constructing `Celery(...)` does not connect to the broker -- that
happens lazily, the first time a task is actually sent or a worker
starts consuming. Importing this module is therefore safe with no
Redis running (verified: see tests/test_celery_app.py), which matters
because app/main.py imports app/api/ocr.py which imports this module,
and the API process must still start cleanly without Redis up yet
(same "start clean, fail loud only when actually used" principle as
app/core/config.py's lazy settings).

Two queues, per ARCHITECTURE.md's design:
  default  cheap/quick tasks (none yet defined, reserved)
  ocr      app.workers.tasks.process_document_task -- CPU-bound, so the
           worker should be started with --concurrency=<cores> and
           worker_prefetch_multiplier=1 (set below) so one slow
           document doesn't starve others queued behind it.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_service",
    broker=settings.celery_broker_url_resolved,
    backend=settings.celery_result_backend_resolved,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_routes={
        "app.workers.tasks.process_document_task": {"queue": "ocr"},
    },
    task_acks_late=True,          # a worker crash mid-task re-queues it, doesn't drop it
    worker_prefetch_multiplier=1,  # OCR is CPU-bound; don't let one worker hoard the queue
    task_track_started=True,       # so job status can report "running", not just pending/done
    result_expires=60 * 60 * 24,   # 24h -- long enough to poll, not an indefinite Redis grow
)
