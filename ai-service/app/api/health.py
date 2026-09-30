from __future__ import annotations

from fastapi import APIRouter

from app.core.llm import llm_status
from polymarker_common.catalog import SYNTHETIC_DATA_LABEL

router = APIRouter(tags=["health"])


@router.get("/")
def root():
    return {"message": "PolyMarker AI service is running", "label": SYNTHETIC_DATA_LABEL}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    from app.services.evidence import get_graph
    from app.services.jobs import get_jobs
    from app.services.model_registry import get_registry

    jobs = get_jobs().health()
    graph = get_graph().health()
    models = get_registry().status()
    return {
        "ready": jobs.get("ok", False),
        "jobs": jobs,
        "graph": graph,
        "models": {k: models.get(k) for k in ("available", "semver", "seed", "error")},
        "llm": llm_status(),
    }
