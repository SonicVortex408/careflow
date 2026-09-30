"""Knowledge-graph evidence for flagged markers (GraphRAG retrieval step)."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import get_settings
from graph_service.connector import GraphConnector, get_connector

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_graph() -> GraphConnector:
    s = get_settings()
    return get_connector(uri=s.neo4j_uri, user=s.neo4j_user, password=s.neo4j_password)


def reported_symptoms(proms: dict | None) -> list[str]:
    if not proms:
        return []
    out = []
    if int(proms.get("fatigue_severity") or 0) >= 7:
        out.append("fatigue")
    if proms.get("brain_fog_frequency") in ("often", "always"):
        out.append("brain_fog")
    if proms.get("hair_loss") in ("moderate", "severe"):
        out.append("hair_loss")
    return out


def evidence_for(markers: dict[str, float], proms: dict | None = None, limit: int = 8) -> dict:
    graph = get_graph()
    chains = graph.evidence_chains(markers, reported_symptoms(proms))
    return {
        "backend": graph.backend,
        "reported_symptoms": reported_symptoms(proms),
        "chains": [c.to_dict() for c in chains[:limit]],
        "total_chains": len(chains),
    }
