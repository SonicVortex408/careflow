# ai-service

FastAPI + Celery + LangGraph service for PolyMarker Analytics. Called only by the
backend (Express), which owns authentication and patient identity.

**Population analytics returned here are derived from synthetic data, for
research/demo purposes, not clinical guidance.** Interpretations are created as
`pending_clinician_review`; the backend releases them only after sign-off.

## Endpoints

| Method | Path | |
|---|---|---|
| GET | `/`, `/health`, `/ready` | liveness; readiness reports jobs / graph / models / LLM backends |
| POST | `/api/ocr` | multipart `file, report_id, patient_id[, proms, sex, age]` → `202 {job_id}` |
| GET | `/api/ocr/jobs/{job_id}` | `queued | processing | completed | failed` (+ `result`) |
| POST | `/api/interpret` | structured markers → the same unified interpretation JSON |
| POST | `/api/inference` | cluster, band positions, calibrated risk, SHAP top-3 |
| GET | `/api/inference/{cohort,bands,catalog,model}` | dashboard data |
| POST | `/api/chat/` | GraphRAG assistant (`patient_context` = latest approved results) |
| POST | `/api/documents/process` | index a general document for the assistant → `202 {job_id}` |

All `/api/*` routes require `X-Internal-Key` when `INTERNAL_API_KEY` is set.

## Pipeline (one upload)

```
file ─► polymarker_common.pipeline      OCR (text layer | Tesseract + column detection)
        ├─ parser                        rows + metadata (never names/IDs)
        ├─ normalizer                    LOINC + SI units, confidences
        └─ quality                       plausibility, decimal misread, z/IQR vs cohort stats
     ─► services/inference.py            K-Means/GMM cluster, functional bands, percentiles,
                                         XGBoost risk (isotonic-calibrated) + TreeSHAP top-3
     ─► services/evidence.py             Neo4j evidence chains (in-memory fallback)
     ─► services/summary.py              LLM draft grounded on the above  ──┐ regenerate ≤ N
     ─► services/guardrails.py           check ─────────────────────────────┘ else template
                                         finalize: redact, escalation notice, disclaimer, audit
```

## Guardrails (deterministic, always last)

Blocked diagnostic / prescriptive / dosage / cure language · Flesch-Kincaid
grade ≤ 8 · mandatory disclaimer + synthetic label · escalation rules (catalog
thresholds, PROMs, data-quality errors, chat red flags) · privacy redaction ·
prompt-injection echo removal · audit trail with draft/final hashes.

## Retrieval

* Knowledge graph first (GraphRAG); vector search over `knowledge_base/` is the
  fallback. Metadata filtering (`status: active`, non-internal audience) is
  enforced in code for both FAISS and the BM25 fallback.
* Per-patient indexes live under `PATIENT_INDEX_DIR/<ObjectId>/`; every returned
  chunk is re-checked against the requesting patient.

## Run

```bash
uv sync                               # --extra vector for FAISS/sentence-transformers
cp .env.example .env
JOB_BACKEND=local uv run uvicorn app.main:app --reload --port 8080
uv run celery -A app.worker.celery_app worker --concurrency=2   # with JOB_BACKEND=celery
uv run pytest && uv run ruff check .
AI_INTEGRATION=1 LIVE_NEO4J_URI=bolt://localhost:7687 uv run pytest tests/test_integration_live.py
```

The image is built from the repository root: `docker build -f ai-service/Dockerfile .`
