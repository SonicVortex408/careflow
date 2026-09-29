# careFlow

A three-service app (`frontend/` React+Vite, `backend/` Express+Mongo,
`ai-service/` FastAPI+LangGraph) originally built as a hospital
queue-management demo, now being extended into **PolyMarker
Analytics** -- a biomarker lab-report intake, OCR, and normalization
pipeline (thyroid + micronutrient panels) -- plus `bda_engine/`, a
synthetic data generator and ETL for the analytics lake behind it.

## Where to start

| I want to... | Go to |
|---|---|
| Understand what's actually built vs. designed vs. missing | [`docs/WEEKS_1-3_STATUS_AND_PLAN.md`](docs/WEEKS_1-3_STATUS_AND_PLAN.md) |
| See the target architecture and design decisions | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Understand the original (pre-extension) codebase | [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) |
| See what's e-commerce-domain leftover vs. medical-domain | [`docs/DOMAIN_MISMATCH.md`](docs/DOMAIN_MISMATCH.md) |
| Run the chat agent / document upload / OCR pipeline | [`ai-service/README.md`](ai-service/README.md) |
| Generate synthetic patients, PROMs, and lab-report PDFs | [`bda_engine/README.md`](bda_engine/README.md) |
| Run the API gateway | `backend/` — `npm install && npm test && npm run dev` (needs `MONGO_URI`) |
| Run the frontend | `frontend/` — `npm install && npm run dev` |

## Run everything together

```bash
cp ai-service/.env.example ai-service/.env   # fill in GROQ_API_KEY at least
cp backend/.env.example backend/.env
docker compose up --build
```

See `docker-compose.yml` for what that starts (`mongo`, `redis`,
`ai-service`, a Celery `worker`, `backend`, `frontend`) and each
service's own README for running it standalone instead.

## Test suites

| Service | Command | What it needs |
|---|---|---|
| `ai-service/` | `uv run pytest` | Nothing external — 197 pass, 2 skip honestly (no Tesseract binary, no Redis) if run outside Docker |
| `bda_engine/` | `uv run pytest` | Nothing external — 96 pass |
| `backend/` | `npm test` | Nothing external (this covers only the pure logic touched by the Weeks 1-3 work; the pre-existing controllers have no test coverage) |
| `frontend/` | *(none configured)* | — |

## Verification environment note

This codebase (the Weeks 1-3 data-lake/OCR/normalization work — see
the status doc above) was built and tested in an environment with:
Python 3.10 (the machine's pinned 3.11 install was broken), no `uv`
binary (dependencies were installed with plain `pip` into a venv
instead), no Tesseract binary, no Redis, no Docker, no JVM. Every test
that needs one of those is either verified working around the gap
(e.g. Celery's eager-execution mode for testing without a broker) or
marked `skipif` with the actual connection/lookup failure as the
reason, never silently assumed. See
`docs/WEEKS_1-3_STATUS_AND_PLAN.md` for exactly what that means for
each piece, and each service's README for what to install to close
the remaining gaps (Tesseract for scanned-document OCR, Redis + a
worker for the async job queue, a JVM for the optional PySpark ETL
path).
