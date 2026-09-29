# graph_service — clinical knowledge graph

Neo4j model of how the nine biomarkers relate to deficiency/thyroid patterns and
to the three PROM symptoms. Used by the ai-service GraphRAG node to fetch
**evidence chains** for flagged markers:

```
(Biomarker)-[:HAS_RANGE]->(FunctionalRange {kind:'threshold'})
    -[:INDICATES | :AMPLIFIES {source, evidence_level, verified}]->(Condition)
    -[:PRESENTS_WITH {source, evidence_level, verified}]->(Symptom)
```

* `schema.cypher` — constraints and indexes (hand-written).
* `seed.cypher` — **generated** from `graph_service/seed_data.py` + the shared
  biomarker catalog: `uv run python -m graph_service.cypher`. A test fails if it is stale.
* `graph_service/connector.py` — `get_connector()` returns a Neo4j connector when
  `NEO4J_URI` is reachable, else an in-memory graph built from the same seed.
  Both go through one post-processor, so they return identical chains.
* `graph_service/loader.py` — applies schema + seed to Neo4j, and optionally the
  bda_engine functional bands / correlations (`--artifacts ../models`), which are
  stored with `evidence_level: synthetic_derived, verified: false`.

Every edge carries `source` and `evidence_level`. Edges without guideline or
authoritative-review backing are `unverified` and are reported that way to the
LLM prompt and the UI. Nothing in the graph is clinical guidance.

```bash
uv sync
uv run pytest
NEO4J_URI=bolt://localhost:7687 NEO4J_PASSWORD=... uv run python -m graph_service.loader --artifacts ../models
```
