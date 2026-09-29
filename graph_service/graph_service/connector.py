"""Knowledge-graph connector.

``get_connector()`` returns a Neo4j-backed connector when NEO4J_URI is set and
reachable, otherwise an in-memory graph built from the same seed data. Both
produce identical ``EvidenceChain`` records: Neo4j does the traversal, and a
shared Python post-processor applies co-condition requirements, de-duplication
and ranking, so the fallback cannot drift from the database behaviour.

An evidence chain reads:

    (Biomarker finding) -[INDICATES|AMPLIFIES]-> (Condition) -[PRESENTS_WITH]-> (Symptom)

and every hop carries ``source`` + ``evidence_level`` + ``verified``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from polymarker_common.catalog import load_catalog

from graph_service import seed_data as seed

logger = logging.getLogger(__name__)

EVIDENCE_RANK = {level: i for i, level in enumerate(seed.EVIDENCE_LEVELS)}


def is_verified(evidence_level: str) -> bool:
    return evidence_level in seed.VERIFIED_LEVELS


@dataclass
class EvidenceEdge:
    type: str
    source: str
    source_title: str
    evidence_level: str
    verified: bool
    note: str = ""


@dataclass
class SymptomLink:
    id: str
    name: str
    edge: EvidenceEdge
    reported: bool = False


@dataclass
class EvidenceChain:
    marker: str
    value: float
    finding: str
    relation: str
    condition_id: str
    condition: str
    edge: EvidenceEdge
    symptoms: list[SymptomLink] = field(default_factory=list)

    @property
    def verified(self) -> bool:
        return self.edge.verified

    @property
    def matches_reported_symptoms(self) -> list[str]:
        return [s.id for s in self.symptoms if s.reported]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["verified"] = self.verified
        data["matches_reported_symptoms"] = self.matches_reported_symptoms
        return data


class GraphConnector(Protocol):
    backend: str

    def evidence_chains(
        self, findings: dict[str, float], reported_symptoms: list[str] | None = None
    ) -> list[EvidenceChain]: ...

    def health(self) -> dict[str, Any]: ...

    def close(self) -> None: ...


# --------------------------------------------------------------------------
# Shared post-processing
# --------------------------------------------------------------------------


def _requirement_met(requires: dict | None, findings: dict[str, float]) -> bool:
    if not requires:
        return True
    key = requires.get("biomarker")
    if key not in findings:
        # Missing co-marker: keep the chain; the summary states what is missing.
        return True
    value = findings[key]
    marker = load_catalog()[key]
    if requires.get("within_reference") and not marker.reference.contains(value):
        return False
    if "above" in requires and requires["above"] is not None and not value > requires["above"]:
        return False
    return True


def _edge(edge_type: str, props: dict) -> EvidenceEdge:
    source = props.get("source", "curated_hypothesis")
    level = props.get("evidence_level", "unverified")
    return EvidenceEdge(
        type=edge_type,
        source=source,
        source_title=seed.SOURCES.get(source, {}).get("title", source),
        evidence_level=level,
        verified=is_verified(level),
        note=props.get("note", "") or "",
    )


def build_chains(
    rows: list[dict[str, Any]], findings: dict[str, float], reported: list[str]
) -> list[EvidenceChain]:
    """rows: flat traversal results (one per threshold->condition->symptom path)."""
    chains: dict[tuple[str, str, str], EvidenceChain] = {}
    reported_set = set(reported)
    for row in rows:
        requires = row.get("requires") or None
        if not _requirement_met(requires, findings):
            continue
        key = (row["marker"], row["relation"], row["condition_id"])
        edge = _edge(row["relation"], row["edge"])
        chain = chains.get(key)
        if (
            chain is None
            or EVIDENCE_RANK[edge.evidence_level] < EVIDENCE_RANK[chain.edge.evidence_level]
        ):
            previous_symptoms = chain.symptoms if chain else []
            chain = EvidenceChain(
                marker=row["marker"],
                value=row["value"],
                finding=row["finding"],
                relation=row["relation"],
                condition_id=row["condition_id"],
                condition=row["condition"],
                edge=edge,
                symptoms=previous_symptoms,
            )
            chains[key] = chain
        symptom_id = row.get("symptom_id")
        if symptom_id and all(s.id != symptom_id for s in chain.symptoms):
            chain.symptoms.append(
                SymptomLink(
                    id=symptom_id,
                    name=row["symptom"],
                    edge=_edge("PRESENTS_WITH", row.get("symptom_edge") or {}),
                    reported=symptom_id in reported_set,
                )
            )

    def rank(c: EvidenceChain):
        return (
            -len(c.matches_reported_symptoms),
            0 if c.relation == "INDICATES" else 1,
            EVIDENCE_RANK[c.edge.evidence_level],
            c.marker,
            c.condition_id,
        )

    return sorted(chains.values(), key=rank)


# --------------------------------------------------------------------------
# In-memory backend
# --------------------------------------------------------------------------


class InMemoryGraph:
    backend = "in_memory"

    def __init__(self) -> None:
        self.thresholds = {t["id"]: t for t in seed.THRESHOLDS}
        self.threshold_edges = list(seed.THRESHOLD_EDGES)
        self.presents_with = list(seed.PRESENTS_WITH)
        self.functional_bands: dict[str, dict] = {}
        self.correlations: list[dict] = list(seed.BIOMARKER_CORRELATIONS)

    def _rows(self, findings: dict[str, float]) -> list[dict]:
        rows = []
        for edge in self.threshold_edges:
            t = self.thresholds[edge["from"]]
            if t["biomarker"] not in findings:
                continue
            value = findings[t["biomarker"]]
            fires = value < t["value"] if t["op"] == "<" else value > t["value"]
            if not fires:
                continue
            base = {
                "marker": t["biomarker"],
                "value": value,
                "finding": t["label"],
                "relation": edge["type"],
                "condition_id": edge["to"],
                "condition": seed.CONDITIONS[edge["to"]],
                "edge": edge,
                "requires": edge.get("requires"),
            }
            symptoms = [p for p in self.presents_with if p["from"] == edge["to"]]
            if not symptoms:
                rows.append(base)
            for p in symptoms:
                rows.append(
                    {
                        **base,
                        "symptom_id": p["to"],
                        "symptom": seed.SYMPTOMS[p["to"]],
                        "symptom_edge": p,
                    }
                )
        return rows

    def evidence_chains(self, findings, reported_symptoms=None):
        return build_chains(self._rows(findings), findings, reported_symptoms or [])

    def upsert_functional_bands(self, bands: dict[str, dict]) -> None:
        self.functional_bands.update(bands)

    def upsert_correlations(self, correlations: list[dict]) -> None:
        self.correlations.extend(correlations)

    def health(self):
        return {"backend": self.backend, "ok": True}

    def close(self):
        return None


# --------------------------------------------------------------------------
# Neo4j backend
# --------------------------------------------------------------------------

EVIDENCE_QUERY = """
UNWIND $findings AS f
MATCH (b:Biomarker {key: f.key})-[:HAS_RANGE]->(t:FunctionalRange {kind: 'threshold'})
WHERE (t.op = '<' AND f.value < t.value) OR (t.op = '>' AND f.value > t.value)
MATCH (t)-[r1]->(c:Condition)
WHERE type(r1) IN ['INDICATES', 'AMPLIFIES']
OPTIONAL MATCH (c)-[r2:PRESENTS_WITH]->(s:Symptom)
RETURN f.key AS marker, f.value AS value, t.label AS finding, type(r1) AS relation,
       c.id AS condition_id, c.name AS condition, properties(r1) AS edge,
       s.id AS symptom_id, s.name AS symptom, properties(r2) AS symptom_edge
"""


def _requires_from_props(props: dict) -> dict | None:
    if not props.get("requires_biomarker"):
        return None
    return {
        "biomarker": props["requires_biomarker"],
        "within_reference": bool(props.get("requires_within_reference")),
        "above": props.get("requires_above"),
    }


class Neo4jConnector:
    backend = "neo4j"

    def __init__(
        self, uri: str, user: str, password: str, database: str | None = None, driver=None
    ):
        if driver is None:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(uri, auth=(user, password))
        self._driver = driver
        self._database = database

    def _run(self, query: str, **params) -> list[dict]:
        records, _, _ = self._driver.execute_query(query, params, database_=self._database)
        return [dict(r) for r in records]

    def evidence_chains(self, findings, reported_symptoms=None):
        payload = [{"key": k, "value": float(v)} for k, v in findings.items()]
        rows = self._run(EVIDENCE_QUERY, findings=payload)
        for row in rows:
            row["edge"] = dict(row.get("edge") or {})
            row["requires"] = _requires_from_props(row["edge"])
            if row.get("symptom_edge") is not None:
                row["symptom_edge"] = dict(row["symptom_edge"])
        return build_chains(rows, findings, reported_symptoms or [])

    def upsert_functional_bands(self, bands: dict[str, dict]) -> None:
        from graph_service.cypher import functional_band_statements

        for statement, params in functional_band_statements(bands):
            self._run(statement, **params)

    def upsert_correlations(self, correlations: list[dict]) -> None:
        from graph_service.cypher import correlation_statements

        for statement, params in correlation_statements(correlations):
            self._run(statement, **params)

    def health(self):
        try:
            self._driver.verify_connectivity()
            count = self._run("MATCH (n) RETURN count(n) AS n")[0]["n"]
            return {"backend": self.backend, "ok": True, "nodes": count}
        except Exception as exc:  # noqa: BLE001 - surfaced to the health endpoint
            return {"backend": self.backend, "ok": False, "error": type(exc).__name__}

    def close(self):
        self._driver.close()


def get_connector(
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    *,
    require_neo4j: bool = False,
) -> GraphConnector:
    uri = uri if uri is not None else os.getenv("NEO4J_URI", "")
    user = user or os.getenv("NEO4J_USER", "neo4j")
    password = password or os.getenv("NEO4J_PASSWORD", "")
    if uri:
        try:
            connector = Neo4jConnector(uri, user, password)
            connector._driver.verify_connectivity()
            return connector
        except Exception as exc:  # noqa: BLE001
            if require_neo4j:
                raise
            logger.warning(
                "Neo4j unavailable (%s); using in-memory knowledge graph", type(exc).__name__
            )
    return InMemoryGraph()
