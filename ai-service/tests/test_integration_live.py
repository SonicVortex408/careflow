"""Live integration: Celery worker over Redis, Redis checkpointer, Neo4j.

Opt-in: AI_INTEGRATION=1 REDIS_URL=redis://... NEO4J_URI=bolt://... NEO4J_PASSWORD=...
and a running worker: celery -A app.worker.celery_app worker
"""

import os
import time

import pytest

from .conftest import PATIENT, REPORT, SAMPLE_REPORT

pytestmark = pytest.mark.skipif(
    os.getenv("AI_INTEGRATION") != "1", reason="live integration disabled"
)


@pytest.fixture
def live_client(monkeypatch):
    from fastapi.testclient import TestClient

    from app.core import config
    from app.main import create_app

    monkeypatch.setenv("JOB_BACKEND", "celery")
    monkeypatch.setenv("CHECKPOINTER", "redis")
    monkeypatch.setenv("NEO4J_URI", os.environ["LIVE_NEO4J_URI"])
    config.get_settings.cache_clear()
    return TestClient(create_app())


def test_celery_job_roundtrip(live_client):
    r = live_client.post(
        "/api/ocr",
        data={"patient_id": PATIENT, "report_id": REPORT},
        files={"file": ("report.txt", SAMPLE_REPORT.encode(), "text/plain")},
    )
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    deadline = time.time() + 120
    seen = set()
    while time.time() < deadline:
        job = live_client.get(f"/api/ocr/jobs/{job_id}").json()
        seen.add(job["status"])
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.5)
    assert job["status"] == "completed", job
    assert job["result"]["evidence"]["backend"] == "neo4j"
    assert job["result"]["review"]["status"] == "pending_clinician_review"


def test_ready_reports_live_backends(live_client):
    ready = live_client.get("/ready").json()
    assert ready["jobs"] == {"backend": "celery", "ok": True}
    assert ready["graph"]["backend"] == "neo4j" and ready["graph"]["ok"]


def test_redis_checkpointer_persists_across_agent_instances(monkeypatch):
    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.redis import RedisSaver

    from app.agent.graph import build_graph, get_checkpointer
    from app.core import config

    monkeypatch.setenv("CHECKPOINTER", "redis")
    config.get_settings.cache_clear()
    assert isinstance(get_checkpointer(), RedisSaver)

    cfg = {"configurable": {"thread_id": f"{PATIENT}:live-{time.time()}"}}
    build_graph(get_checkpointer()).invoke(
        {"messages": [HumanMessage(content="What is TSH?")], "patient_id": PATIENT}, config=cfg
    )
    # A brand-new graph + saver (e.g. another replica) sees the same conversation.
    state = build_graph(get_checkpointer()).get_state(cfg)
    assert any(m.type == "human" and "TSH" in m.content for m in state.values["messages"])
