# ai-service

FastAPI service: the RAG chat agent, document/OCR ingestion, and the
LOINC/unit normalization pipeline for careFlow's biomarker features
(Weeks 1-3 of the data-lake/OCR/normalization brief — see
`../docs/WEEKS_1-3_STATUS_AND_PLAN.md` for the full design and
`../docs/CURRENT_STATE.md` for the pre-existing chat/RAG functionality
this extends).

## Quick start

```bash
cd ai-service
uv sync
cp .env.example .env   # fill in GROQ_API_KEY at least, for chat

# Build the global knowledge-base index (required once for /api/chat's
# search_docs tool; not required for /health or the OCR endpoints)
uv run python -m app.retrieval.ingest

uv run uvicorn app.main:app --reload --port 8080
uv run pytest      # 197 tests, ~30s, no external services required
```

`GET /health` answers even with no `.env` at all -- every external
dependency (the LLM client, the FAISS index, Redis, Tesseract) is
constructed lazily and fails only when an endpoint that actually needs
it is called, with a clear error. `GET /` is the older liveness stub;
prefer `/health` for container health checks.

### Async OCR pipeline (Week 2) -- also needs Redis + a worker

```bash
# in one terminal: the API (as above), plus REDIS_URL in .env
# in another terminal:
uv run celery -A app.workers.celery_app worker --loglevel=INFO -Q default,ocr
```

`POST /api/ocr/` (multipart: `file`, `patient_id`, `document_id`)
enqueues and returns `202 {job_id, status_url}` immediately.
`GET /api/ocr/jobs/{job_id}` polls the result.

### Tesseract (scanned-document OCR)

`OCR_ENGINE=tesseract` (the default) needs the **Tesseract binary**,
not just the `pytesseract` Python package -- there is no PyPI wheel
for it:

- Docker: already installed in `Dockerfile` (`apt-get install
  tesseract-ocr`).
- Windows dev machine: install from
  <https://github.com/UB-Mannheim/tesseract/wiki>, then set
  `TESSERACT_CMD` in `.env` to the installed `tesseract.exe`.
- Linux/macOS dev machine: `apt-get install tesseract-ocr` /
  `brew install tesseract`.

Check `app/ocr/tesseract_engine.is_available()` if you're unsure
whether it's found; `app/ocr/pipeline.py` raises a clear
`UnsupportedDocumentError` (not a raw traceback) when it isn't.

**This was not available in the environment this codebase was
developed in** (no system package manager access) -- every OCR module
except the actual Tesseract call is fully tested against real
documents (see `tests/test_ocr_router.py`,
`tests/test_text_layer.py`, `tests/test_table_reconstruct.py`,
`tests/test_raster.py`); the one test that needs the real binary is
`tests/test_tesseract_engine.py::TestExtractWordsFromImage`, marked
`skipif` with the actual connection-failure reason (not assumed), and
will run for real the first time this suite runs in Docker or on a
machine with Tesseract installed.

## Layout

```
app/
  main.py            FastAPI app, CORS, routers, /health
  core/
    config.py        pydantic-settings, lazy get_settings()
    validation.py    patient_id / filename path-traversal guards
  agent/             LangGraph chat agent (pre-existing, see docs/CURRENT_STATE.md)
  retrieval/         FAISS ingestion + retrieval (global KB + per-patient)
  api/
    chat.py          POST /api/chat/
    documents.py     POST /api/documents/process  (legacy sync path, still used
                      by the chat agent's per-patient RAG ingestion)
    ocr.py           POST /api/ocr/, GET /api/ocr/jobs/{id}  (Week 2 async path)
  ocr/               Week 2: router, text_layer, raster, tesseract_engine,
                      table_reconstruct, field_extract, pipeline
  services/          Week 3: normalizer, units, ref_range, data_quality,
                      reference_data (loads ../reference/, shared with bda_engine)
  workers/           Week 2: celery_app.py, tasks.py
scripts/             manual_*.py -- REPL/smoke-test scripts, not pytest tests
tests/               pytest; tests/conftest.py imports bda_engine directly
                      (a sibling project, not a runtime dependency of this
                      service -- see app/services/reference_data.py's
                      docstring) to generate real test PDFs
```

## Reference data

`reference/` (LOINC codes, unit-conversion factors, analyte synonyms,
lab-provider names) lives at the **repo root**, not inside
`ai-service/`, so it can be shared with `bda_engine/` as plain data
without this service depending on `bda_engine`'s heavier packages
(pandas, faker, reportlab, duckdb). See
`app/services/reference_data.py`'s module docstring. This means
**ai-service's Docker build context is the repo root**, not
`ai-service/` itself (see `docker-compose.yml` and the top of
`Dockerfile`).

## Known gaps (see `../docs/WEEKS_1-3_STATUS_AND_PLAN.md` for the full list)

- `OCR_ENGINE=paddle` and `ENABLE_LAYOUTLMV3=true` are read from
  config but **not implemented** -- only `tesseract` (the default) has
  an engine behind it. Selecting either currently raises
  `UnsupportedDocumentError` via `app/ocr/pipeline.py`.
- The LangGraph chat agent's checkpointer is still `InMemorySaver`
  (conversation memory does not survive a restart or scale past one
  replica). A Redis-backed checkpointer
  (`langgraph-checkpoint-redis`) was evaluated but not wired in: its
  `RedisSaver` is a context-manager API that needs real integration
  into FastAPI's lifespan, and it requires Redis Stack modules
  (RedisJSON/RediSearch) that the plain `redis:7-alpine` image in
  `docker-compose.yml` does not have -- both are real follow-up work,
  not a quick fix.
- `uv.lock` is not committed (see the note at the top of
  `Dockerfile`) -- no `uv` binary was available in the environment
  this was built in to generate one. Run `uv lock` once before a
  production deploy that wants pinned, reproducible dependency
  resolution.
