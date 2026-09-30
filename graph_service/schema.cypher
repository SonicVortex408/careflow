// PolyMarker Analytics knowledge graph schema (Neo4j 5).
// Apply before seed.cypher:  python -m graph_service.loader
//
// Nodes
//   (:Biomarker {key, name, panel, canonical_unit})
//   (:LOINC {code, name})
//   (:FunctionalRange {id, biomarker, kind: 'reference'|'threshold'|'functional_band',
//                      low?, high?, op?, value?, unit, label, source, evidence_level, verified})
//   (:Condition {id, name})
//   (:Symptom {id, name})
//   (:Source {id, title, publisher, year})
//
// Relationships (every one carries source + evidence_level + verified)
//   (Biomarker)-[:CODED_AS]->(LOINC)
//   (Biomarker)-[:HAS_RANGE]->(FunctionalRange)
//   (FunctionalRange)-[:INDICATES|AMPLIFIES]->(Condition)
//   (Condition)-[:PRESENTS_WITH]->(Symptom)
//   (Biomarker)-[:CORRELATES_WITH {direction, rho?}]->(Biomarker|Symptom)
//   (any edge).source -> (:Source {id})

CREATE CONSTRAINT biomarker_key IF NOT EXISTS FOR (b:Biomarker) REQUIRE b.key IS UNIQUE;
CREATE CONSTRAINT loinc_code IF NOT EXISTS FOR (l:LOINC) REQUIRE l.code IS UNIQUE;
CREATE CONSTRAINT range_id IF NOT EXISTS FOR (r:FunctionalRange) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT condition_id IF NOT EXISTS FOR (c:Condition) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT symptom_id IF NOT EXISTS FOR (s:Symptom) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT source_id IF NOT EXISTS FOR (s:Source) REQUIRE s.id IS UNIQUE;
CREATE INDEX range_kind IF NOT EXISTS FOR (r:FunctionalRange) ON (r.kind, r.biomarker);
