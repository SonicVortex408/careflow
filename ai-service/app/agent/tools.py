"""Agent tools. Outputs are untrusted evidence, formatted for the model."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from app.retrieval import kb
from app.services.evidence import get_graph
from polymarker_common.catalog import SYNTHETIC_DATA_LABEL, load_catalog
from polymarker_common.normalizer import match_name


@tool
def search_knowledge_base(query: str) -> str:
    """Search the reviewed medical knowledge base (vector fallback). Returns passages with evidence levels."""
    return kb.format_results(kb.search(query, k=3))


@tool
def get_biomarker_evidence(marker: str, value: float) -> str:
    """Knowledge-graph evidence chains for one biomarker value in canonical SI units."""
    match = match_name(marker)
    if match is None:
        return "Unknown biomarker."
    chains = get_graph().evidence_chains({match.key: float(value)})
    if not chains:
        return f"No evidence chains fire for {match.key} = {value}."
    return json.dumps(
        [
            {
                "finding": c.finding,
                "relation": c.relation,
                "pattern": c.condition,
                "symptoms": [s.name for s in c.symptoms],
                "evidence_level": c.edge.evidence_level,
                "verified": c.verified,
                "source": c.edge.source_title,
            }
            for c in chains
        ]
    )


@tool
def explain_biomarker(marker: str) -> str:
    """Reference information for a biomarker (LOINC, unit, reference range, synthetic functional band)."""
    match = match_name(marker)
    if match is None:
        return "Unknown biomarker."
    m = load_catalog()[match.key]
    info = {
        "marker": m.display,
        "loinc": m.loinc,
        "unit": m.canonical_unit,
        "reference_range": [m.reference.low, m.reference.high],
        "reference_source": m.reference_source,
    }
    try:
        from app.services.model_registry import get_registry

        band = get_registry().json("functional_bands")["bands"][match.key]["functional"]
        if band:
            info["functional_band"] = {
                "low": band["low"],
                "high": band["high"],
                "note": SYNTHETIC_DATA_LABEL,
            }
    except Exception:  # noqa: BLE001 - artifacts optional
        pass
    return json.dumps(info)


TOOLS = [search_knowledge_base, get_biomarker_evidence, explain_biomarker]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
