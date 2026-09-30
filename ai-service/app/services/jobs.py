"""Job submission + status (Velocity: async ingestion with polling).

JOB_BACKEND=celery  Celery over Redis (production / compose). A small Redis
                    record per job lets us tell "unknown id" from "queued".
JOB_BACKEND=local   in-process thread pool + dict (local dev without Redis, tests).
"""

from __future__ import annotations

import json
import logging
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import get_settings

logger = logging.getLogger(__name__)

STATES = ("queued", "processing", "completed", "failed")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class JobBackend(Protocol):
    name: str

    def submit(self, kind: str, payload: dict[str, Any]) -> str: ...

    def get(self, job_id: str) -> dict[str, Any] | None: ...

    def health(self) -> dict[str, Any]: ...


class LocalJobs:
    name = "local"

    def __init__(self, workers: int = 2):
        from app.worker.tasks_impl import TASKS

        self._tasks = TASKS
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="job")
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _run(self, job_id: str, kind: str, payload: dict) -> None:
        with self._lock:
            self._jobs[job_id].update(status="processing", started_at=_now())
        try:
            result = self._tasks[kind](payload)
            update = {"status": "completed", "result": result}
        except Exception as exc:  # noqa: BLE001
            logger.error("job %s failed: %s", job_id, traceback.format_exc(limit=3))
            update = {"status": "failed", "error": type(exc).__name__}
        with self._lock:
            self._jobs[job_id].update(update, finished_at=_now())

    def submit(self, kind, payload):
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "kind": kind,
                "status": "queued",
                "created_at": _now(),
            }
        self._pool.submit(self._run, job_id, kind, payload)
        return job_id

    def get(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def health(self):
        return {"backend": self.name, "ok": True}


class CeleryJobs:
    name = "celery"
    _TASK_NAMES = {
        "process_report": "polymarker.process_report",
        "index_document": "polymarker.index_document",
    }
    _STATE_MAP = {
        "PENDING": "queued",
        "RECEIVED": "queued",
        "STARTED": "processing",
        "RETRY": "processing",
        "SUCCESS": "completed",
        "FAILURE": "failed",
        "REVOKED": "failed",
    }

    def __init__(self):
        import redis

        from app.worker.celery_app import celery_app

        s = get_settings()
        self._app = celery_app
        self._redis = redis.Redis.from_url(s.redis_url)
        self._ttl = s.job_result_ttl_seconds

    def _key(self, job_id: str) -> str:
        return f"polymarker:job:{job_id}"

    def submit(self, kind, payload):
        job_id = str(uuid.uuid4())
        record = {"job_id": job_id, "kind": kind, "created_at": _now()}
        self._redis.set(self._key(job_id), json.dumps(record), ex=self._ttl)
        payload = stash_file(self._redis, job_id, payload)
        self._app.send_task(self._TASK_NAMES[kind], args=[payload], task_id=job_id)
        return job_id

    def get(self, job_id):
        raw = self._redis.get(self._key(job_id))
        if raw is None:
            return None
        record = json.loads(raw)
        res = self._app.AsyncResult(job_id)
        status = self._STATE_MAP.get(res.state, "processing")
        record["status"] = status
        if status == "completed":
            record["result"] = res.result
        elif status == "failed":
            record["error"] = (
                type(res.result).__name__
                if isinstance(res.result, Exception)
                else str(res.result)[:200]
            )
        return record

    def health(self):
        try:
            self._redis.ping()
            return {"backend": self.name, "ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"backend": self.name, "ok": False, "error": type(exc).__name__}


FILE_HANDOFF_TTL_SECONDS = 3600


def _file_key(job_id: str) -> str:
    return f"polymarker:file:{job_id}"


def stash_file(redis_client, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Copy the uploaded file into Redis so a worker on another machine can read it.

    The API and the Celery worker only share a filesystem in docker-compose; on
    hosts where each service has its own disk (e.g. Render) the worker restores
    the file from Redis. Uploads are capped at 10 MB and expire after an hour.
    """
    path = payload.get("path")
    if not path:
        return payload
    with open(path, "rb") as fh:
        redis_client.set(_file_key(job_id), fh.read(), ex=FILE_HANDOFF_TTL_SECONDS)
    return {**payload, "file_key": _file_key(job_id)}


def ensure_local_file(payload: dict[str, Any]) -> None:
    """Worker side of ``stash_file``: restore the upload if this disk lacks it."""
    from pathlib import Path

    path = Path(payload["path"])
    key = payload.get("file_key")
    if path.exists() or not key:
        return
    import redis

    data = redis.Redis.from_url(get_settings().redis_url).get(key)
    if data is None:
        raise FileNotFoundError("Uploaded file expired before processing")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@lru_cache(maxsize=1)
def get_jobs() -> JobBackend:
    backend = get_settings().job_backend.lower()
    if backend == "local":
        return LocalJobs()
    return CeleryJobs()
