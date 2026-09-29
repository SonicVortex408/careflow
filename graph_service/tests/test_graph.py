import os

import pytest

from graph_service import seed_data as seed
from graph_service.connector import InMemoryGraph, Neo4jConnector, get_connector
from graph_service.cypher import SEED_PATH, generate_seed, split_statements


def test_seed_cypher_is_up_to_date():
    assert SEED_PATH.read_text(encoding="utf-8") == generate_seed(), (
        "seed.cypher is stale: run `uv run python -m graph_service.cypher`"
    )


def test_every_edge_has_known_source_and_evidence_level():
    edges = seed.THRESHOLD_EDGES + seed.PRESENTS_WITH + seed.BIOMARKER_CORRELATIONS
    for edge in edges:
        assert edge["source"] in seed.SOURCES, edge
        assert edge["evidence_level"] in seed.EVIDENCE_LEVELS, edge
    # Every relationship statement in the generated seed sets evidence_level.
    rel_statements = [
        s for s in split_statements(generate_seed()) if "]->(" in s and "HAS_RANGE" not in s
    ]
    assert rel_statements and all("evidence_level" in s for s in rel_statements)


def test_unverified_edges_are_marked_unverified():
    text = generate_seed()
    for line in text.splitlines():
        if 'evidence_level: "unverified"' in line:
            assert "verified: false" in line


def test_low_ferritin_and_raised_tsh_chains():
    graph = InMemoryGraph()
    findings = {"FERRITIN": 12.0, "TSH": 5.8, "FT4": 14.0}
    chains = graph.evidence_chains(findings, reported_symptoms=["fatigue"])
    pairs = {(c.marker, c.relation, c.condition_id) for c in chains}
    assert ("FERRITIN", "INDICATES", "iron_deficiency") in pairs
    assert ("FERRITIN", "AMPLIFIES", "subclinical_hypothyroidism") in pairs
    assert ("TSH", "INDICATES", "subclinical_hypothyroidism") in pairs
    iron = next(c for c in chains if c.condition_id == "iron_deficiency")
    # ferritin <15 (guideline) wins over <30 (expert consensus) for the same condition
    assert iron.edge.evidence_level == "guideline" and iron.verified
    assert "fatigue" in iron.matches_reported_symptoms
    amplifies = next(c for c in chains if c.relation == "AMPLIFIES" and c.marker == "FERRITIN")
    assert amplifies.edge.evidence_level == "unverified" and not amplifies.verified
    # chains matching reported symptoms rank first
    assert chains[0].matches_reported_symptoms


def test_co_condition_requirement_blocks_subclinical_when_ft4_low():
    graph = InMemoryGraph()
    chains = graph.evidence_chains({"TSH": 12.0, "FT4": 6.0})
    ids = {c.condition_id for c in chains}
    assert "hypothyroidism" in ids
    assert "subclinical_hypothyroidism" not in ids


def test_normal_panel_has_no_chains():
    graph = InMemoryGraph()
    findings = {
        "TSH": 1.8,
        "FT4": 15,
        "FT3": 4.5,
        "TPOAB": 10,
        "VITD": 80,
        "B12": 400,
        "FERRITIN": 90,
        "MG": 0.85,
        "ZINC": 13,
    }
    assert graph.evidence_chains(findings) == []


class _FakeRecord(dict):
    pass


class _FakeDriver:
    """Replays in-memory traversal rows the way Neo4j would return them."""

    def __init__(self):
        self.queries = []

    def execute_query(self, query, params, database_=None):
        self.queries.append((query, params))
        graph = InMemoryGraph()
        findings = {f["key"]: f["value"] for f in params["findings"]}
        rows = []
        for row in graph._rows(findings):
            edge = dict(row["edge"])
            req = edge.pop("requires", None)
            if req:
                edge["requires_biomarker"] = req["biomarker"]
                edge["requires_within_reference"] = req.get("within_reference", False)
                edge["requires_above"] = req.get("above")
            rows.append(
                _FakeRecord(
                    {
                        "marker": row["marker"],
                        "value": row["value"],
                        "finding": row["finding"],
                        "relation": row["relation"],
                        "condition_id": row["condition_id"],
                        "condition": row["condition"],
                        "edge": edge,
                        "symptom_id": row.get("symptom_id"),
                        "symptom": row.get("symptom"),
                        "symptom_edge": row.get("symptom_edge"),
                    }
                )
            )
        return rows, None, None

    def close(self):
        pass


def test_neo4j_and_in_memory_backends_agree():
    findings = {"FERRITIN": 12.0, "TSH": 12.0, "FT4": 6.0, "VITD": 25, "TPOAB": 120}
    neo = Neo4jConnector("bolt://fake", "neo4j", "x", driver=_FakeDriver())
    a = [c.to_dict() for c in neo.evidence_chains(findings, ["fatigue"])]
    b = [c.to_dict() for c in InMemoryGraph().evidence_chains(findings, ["fatigue"])]
    assert a == b


def test_get_connector_falls_back_without_neo4j():
    connector = get_connector(uri="bolt://127.0.0.1:1", user="neo4j", password="x")
    assert connector.backend == "in_memory"


@pytest.mark.skipif(not os.getenv("NEO4J_URI"), reason="needs a live Neo4j (NEO4J_URI)")
def test_live_neo4j_matches_in_memory():
    from graph_service.loader import load

    load()
    live = get_connector(require_neo4j=True)
    findings = {"FERRITIN": 12.0, "TSH": 5.8, "FT4": 14.0}
    assert [c.to_dict() for c in live.evidence_chains(findings)] == [
        c.to_dict() for c in InMemoryGraph().evidence_chains(findings)
    ]


def test_split_statements_keeps_semicolons_inside_literals():
    text = 'MERGE (a {note: "x; y"});\n// comment\nMERGE (b);\n'
    assert split_statements(text) == ['MERGE (a {note: "x; y"})', "MERGE (b)"]
