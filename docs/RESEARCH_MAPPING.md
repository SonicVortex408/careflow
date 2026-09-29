# Research mapping

The 14-week plan grounds PolyMarker in 15 papers (2022–2026) across three
pillars. This table maps each one to the part of the system that implements the
idea, so the big-data framing can be traced to code. Titles and key
contributions are as listed in the project plan; full citations should be
verified against the sources before publication.

## Pillar 1 — Big Data Analytics in healthcare

| # | Work (as cited in the plan) | Idea used | Implemented in |
|---|---|---|---|
| 1 | TriNetX: analysing clinical laboratory data outcomes in retrospective cohort studies (Biochemia Medica, 2025) | Aggregate lab results across a cohort to find population patterns | Silver/gold lake, cohort percentiles and cluster profiles — `bda_engine/etl/lake.py`, `models/clustering.py` |
| 2 | Medicare-Enhanced Laboratory and Demographics (MELD) dataset (PMC, 2026) | Multi-source lake joining labs, demographics and PROMs | Raw → bronze → silver → gold zones over 5 lab sources + intake forms — `bda_engine/schemas/lake.py` |
| 3 | Big data analytics in healthcare: current practices, innovations (Springer, 2025) | Frame the system as population-health analytics, not a chatbot | 4-V mapping in `README.md`; Spark/DuckDB engine — `bda_engine/etl/engine.py` |
| 4 | Chronic disease monitoring: bias correction in clinical laboratory data (PubMed, 2025) | Correct classification error / self-selection before deriving ranges | Data-quality layer (plausibility, decimal misread, z/IQR, duplicates) before modelling — `common/polymarker_common/quality.py`; limitations in `evaluation/REPORT.md` §6 |
| 5 | Turning testing data into predictive insights (Clinical Lab, 2026) | Lab data as early-warning signals | Deterministic escalation rules + review-queue triage — `ai-service/app/services/guardrails.py`, `backend/src/controllers/reviewController.js` |

## Pillar 2 — Machine learning (multi-biomarker analysis, symptom correlation, OCR)

| # | Work | Idea used | Implemented in |
|---|---|---|---|
| 6 | Statistical and ML approaches for clinical blood biomarkers (Frontiers AI, 2025) | Joint multi-marker correlation analysis | Spearman marker↔symptom and marker↔marker matrices, loaded into the graph as `CORRELATES_WITH` (synthetic-derived) — `bda_engine/pipeline.py` |
| 7 | ML-based multimodal molecular biomarkers (PubMed, 2026) | Engineered features from several biomarker sources | FT3/FT4, ferritin-to-TSH, TSH×FT4, interaction terms, deficit count, missingness flags — `bda_engine/features/build.py` |
| 8 | Multi-omics and ML identify novel biomarkers (Frontiers Immunology, 2025) | Unsupervised discovery of sub-clinical patterns | K-Means / GMM / DBSCAN, density outliers as a triage signal — `bda_engine/models/clustering.py` |
| 9 | Context matters in ML-based disease prediction (Sci Rep, 2025) | Labs + symptoms/context outperform labs alone | PROM intake joined to lab vectors; risk models include demographics; SHAP shows the demographic share — `models/risk.py`, `evaluation/REPORT.md` §5 |
| 10 | Layout-aware multitask models for medical document analysis (PMC, 2024) | OCR + layout parsing with synthetic documents for privacy | Synthetic PDFs in 4 layouts, column-gap table detection, LayoutLMv3 hook behind a flag — `common/polymarker_common/ocr.py`, `parser.py` |

## Pillar 3 — AI/ML in healthcare (safety, health literacy, PROMs, knowledge graphs)

| # | Work | Idea used | Implemented in |
|---|---|---|---|
| 11 | AI-driven personalised nutrition (Wiley, 2025) | Personalised interpretation of lab + lifestyle data | Per-patient bands, percentiles, cluster and risk in the interpretation — `ai-service/app/services/inference.py` |
| 12 | AI for identifying PROMs/PREMs (JMIR, 2026) | Structured extraction of patient-reported symptoms | Free-text intake answers normalised to the PROM schema in SQL — `bda_engine/etl/lake.py::silver_proms`; symptom intake UI |
| 13 | BiomarkerKB: FAIR integrated biomarker knowledge graph (bioRxiv, 2026) | Neo4j biomarker–condition graph | `graph_service/` schema, generated seed with `source` + `evidence_level` on every edge |
| 14 | AI-driven clinical decision support systems (PMC, 2025) | Deterministic guardrails + retrieval for traceable output | GraphRAG agent with guardrails as the last node; audit trail — `ai-service/app/agent/`, `services/guardrails.py` |
| 15 | ML in surgical PROMs: critical appraisal (2026) | PROMs as model features/targets | Fatigue / brain-fog / hair-loss targets and calibrated risk — `polymarker_common/proms.py`, `models/risk.py` |

## Differentiation (from the plan)

Patient-facing, symptom-correlated, multi-marker (thyroid + micronutrient)
interpretation with deterministic clinical rules and mandatory clinician
sign-off. The regulatory alignment the plan names (clinician escalation, audit
trail, human-in-the-loop) maps to the Report review workflow in `backend/` and
the guardrail audit in `ai-service/`.
