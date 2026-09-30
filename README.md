# PolyMarker Analytics

**A scalable big-data architecture for multi-biomarker clustering, symptom
correlation and functional-range discovery in unstructured health records.**

PolyMarker (formerly *careFlow* / *LabLens*) turns heterogeneous thyroid and
micronutrient lab reports into clinician-reviewed, plain-language insight:

- **OCR ingestion:** distributed (Spark) or per-upload (Celery), with layout-tolerant parsing.
- **Normalization:** LOINC coding and SI-unit conversion with confidence scores.
- **Data quality:** statistical checks with an audit trail.
- **Population analytics:** clustering, functional-band discovery and calibrated symptom-risk models with SHAP explanations.
- **Knowledge graph:** a Neo4j clinical graph whose evidence chains carry source and evidence level.
- **GraphRAG assistant:** answers wrapped in deterministic safety guardrails.
- **Clinician sign-off:** mandatory before any patient sees an interpretation.

> **Synthetic-data rule.** All population-level data in this repository is
> synthetic. Every cluster, functional range, percentile and risk score is
> *derived from synthetic data, for research/demo purposes, not clinical
> guidance* — in code, API responses and the UI. PolyMarker does not diagnose.

**Scope:** 9 biomarkers (TSH, Free T3, Free T4, Anti-TPO, Vitamin D 25-OH,
Vitamin B12, Ferritin, Magnesium, Zinc) · 3 PROMs (fatigue 1–10, brain-fog
frequency, hair loss).

## Architecture

```
frontend/  React 18 + Vite + Tailwind (Vercel)
   │  patient: upload + job status · symptom intake · gauges / radar / cohort map · assistant
   │  clinician: review queue · sign-off · escalations · cohort analytics      admin: clinicians
   ▼  VITE_API_BASE_URL
backend/   Express 5 API gateway · JWT roles patient|clinician|admin · Report workflow
   │       processing → pending_clinician_review → approved | rejected        MongoDB
   ▼  X-Internal-Key
ai-service/ FastAPI + LangGraph ─── Celery worker ── Redis (broker, results, checkpointer)
   │   /api/ocr → OCR → normalize → quality → inference → graph evidence → summary → guardrails
   ├── graph_service/  Neo4j schema + seed + connector (in-memory fallback)
   └── models/         versioned artifacts ◄── bda_engine/ (offline, PySpark | DuckDB)
common/    polymarker_common: catalog, normalizer, parser, OCR, quality, features (shared)
evaluation/ metrics scripts, figures, REPORT.md
```

Design decisions, risks and the request flow: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
Research grounding: [`docs/RESEARCH_MAPPING.md`](docs/RESEARCH_MAPPING.md).
Results: [`evaluation/REPORT.md`](evaluation/REPORT.md).

## Quick start (Docker)

```bash
cp .env.example .env          # set JWT_SECRET, AI_INTERNAL_KEY; optionally GROQ_API_KEY
docker compose up --build     # mongo, redis-stack, neo4j, ai-service, worker, backend, frontend
```

Open http://localhost:5173 and sign in with the seeded demo accounts (change the
passwords in `.env`): `patient@polymarker.local`, `clinician@polymarker.local`,
`admin@polymarker.local`. A reference model set (seed 42, 50k synthetic
patients) ships in `models/`; to regenerate the data lake and retrain:

```bash
docker compose --profile ml run --rm bda all      # ~8 min, ~8 GB RAM (ETL_ENGINE=spark|duckdb)
docker compose run --rm graph-seed                # reload bands/correlations into Neo4j
```

Minimum resources: 4 CPU / 6 GB RAM for the core stack (Neo4j heap is capped at
512 MB); the `ml` profile adds Spark and needs ~8 GB.

## Local development

| Service | Commands |
|---|---|
| common | `cd common && uv sync --extra ocr && uv run pytest` |
| graph_service | `cd graph_service && uv sync && uv run pytest` |
| bda_engine | `cd bda_engine && uv sync --extra spark && uv run bda all && uv run pytest` |
| ai-service | `cd ai-service && uv sync && JOB_BACKEND=local uv run uvicorn app.main:app --port 8080` |
| backend | `cd backend && npm ci && npm run dev` · tests: `MONGO_URI_TEST=... npm test` |
| frontend | `cd frontend && npm ci && VITE_API_BASE_URL=http://localhost:5000/api npm run dev` |

Each service has a `.env.example`. Tesseract is needed for OCR of scanned
documents (`apt install tesseract-ocr`); Java 17+ for PySpark.

**Production deployment:** frontend on Vercel, back end on Render via the
blueprint in [`render.yaml`](render.yaml), MongoDB Atlas and (optionally) Neo4j
Aura — step by step in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). Set
`VITE_API_BASE_URL` in Vercel for every environment; the frontend contains no
hardcoded backend URL (CI fails if one is reintroduced).

## Big-data framing (the four Vs)

| V | Where it shows up |
|---|---|
| **Volume** | 50,000 synthetic patients · 67k reports · 0.5 M raw result rows · 500 PDFs; partitioned Parquet lake (bronze/silver/gold); PySpark ETL with identical DuckDB path |
| **Variety** | 5 labs with different labels, units (conventional vs SI), formats (CSV, JSONL), decimal commas, detection limits; unstructured PDFs in 4 layouts, 35 % scanned; free-text PROM answers; a property graph |
| **Velocity** | Asynchronous Celery/Redis ingestion with job-status polling; ~0.4 s per document OCR; 13 ms interpretation per report; Spark `mapPartitions` batch OCR |
| **Value** | Functional bands narrower than lab ranges, cluster profiles, calibrated symptom risk with SHAP drivers, evidence chains, clinician-reviewed plain-language summaries |

## 14-week plan — status

| Phase | Weeks | Delivered | Where |
|---|---|---|---|
| 1 · Ingestion & BDA engine | 1–4 | data-lake schemas; 50k synthetic generator; OCR (text layer / Tesseract + table detection; Paddle & LayoutLMv3 behind flags); Celery queue; LOINC + unit normalizer; z-score/IQR/decimal-misread checks with audit | `bda_engine/`, `common/`, `ai-service/app/api/ocr.py` |
| 2 · Graph & ML | 5–8 | Neo4j graph with evidence levels; joint feature vectors, ratios, interactions; K-Means / GMM / DBSCAN; functional-band discovery; XGBoost + SHAP | `graph_service/`, `bda_engine/features`, `bda_engine/models` |
| 3 · GraphRAG & safety | 9–11 | GraphRAG agent with cohort insights; deterministic guardrails (no diagnosis/dosing, FK ≤ 8, disclaimer, escalation, audit); unified output JSON | `ai-service/app/agent`, `app/services` |
| 4 · UI, review, evaluation, docs | 12–14 | gauges, radar, cohort map; clinician review portal; CER/WER, silhouette/DBI, AUROC, safety & hallucination benchmarks; rebrand, docs, CI | `frontend/`, `backend/`, `evaluation/`, `docs/` |

## Tests

Every service has an automated suite, run in CI (`.github/workflows/ci.yml`)
with live Neo4j, Redis Stack and MongoDB service containers:
common 45 · graph_service 10 · bda_engine 13 · ai-service 41 (+3 live) ·
backend 11 · frontend 14.

## Safety model

1. Interpretations are stored as `pending_clinician_review`; patients see
   nothing until a clinician approves or edits it.
2. The LLM is never the last step: every patient-facing text passes the
   deterministic guardrails, and failing drafts are regenerated, then replaced
   by a template.
3. Retrieved content is data, not instructions; retrieval filters are enforced
   in code; patient indexes are isolated and ownership-checked.
4. Knowledge-graph links carry `source` and `evidence_level`; unverified links
   are shown as unverified.
