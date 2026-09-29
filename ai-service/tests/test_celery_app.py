"""
Week 2 Step 2.2 acceptance: constructing the Celery app must not
require a live Redis connection -- see app/workers/celery_app.py's
module docstring for why this matters (app/main.py's import chain
reaches it, and the API process must start without Redis up yet).
"""

from app.workers.celery_app import celery_app


def test_celery_app_imports_without_a_live_broker():
    # If this module imported without raising, the assertion below is
    # the real check: the app is configured, not just "didn't crash".
    assert celery_app.main == "ai_service"


def test_ocr_queue_routing_configured():
    routes = celery_app.conf.task_routes
    assert routes["app.workers.tasks.process_document_task"]["queue"] == "ocr"


def test_prefetch_and_ack_late_configured_for_cpu_bound_work():
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_acks_late is True


def test_process_document_task_is_registered():
    # Importing app.workers.tasks (via `include=` in celery_app.py)
    # must actually register the task under celery_app.
    import app.workers.tasks  # noqa: F401

    assert "app.workers.tasks.process_document_task" in celery_app.tasks
