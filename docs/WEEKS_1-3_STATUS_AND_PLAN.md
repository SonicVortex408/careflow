# Weeks 1–3 — Status, What Was Built, and What's Left

**This document was originally an audit + plan (written before any of
Weeks 1–3 was implemented). It has since been rewritten to reflect
execution: everything in §1 was actually built and tested against real
data in this repository, not just designed.** The original audit
methodology note still applies to §0/§1/§2 below: every file claim was
verified by reading the source and, wherever possible, by actually
running it — see §3, "Verification environment," for exactly what
could and couldn't be executed and why.

---

## 0. Headline verdict

| Week | Deliverable | State |
|---|---|---|
| **1** | Data lake + 4 schemas + synthetic generator | **Built and tested.** 4 pydantic schemas, LOINC reference data, a 5-phenotype synthetic generator (6 PDF layouts + scan simulation + ground truth), DuckDB ETL + feature vectors. Full-scale generation (50k patients / 2,000 documents) was not run in this environment — see §2. |
| **2** | Layout-aware OCR + async queue + lab metadata extraction | **Built and tested, with one real gap.** Router, text-layer extraction, table reconstruction, field extraction, rasterization/deskew, Celery async job queue, and the jobs API are all built and tested against real documents. The Tesseract *binary* (not the Python package) was unavailable in the build environment, so the scanned-document OCR call itself is untested — everything up to and after that one call is. |
| **3** | LOINC mapping + unit conversion | **Built and tested.** A 5-stage mapping cascade (exact → synonym → OCR-repair → fuzzy → unmapped), unit alias canonicalization + conversion, reference-range parsing, quality checks, and feature-vector pivoting — all verified against the brief's own adversarial example and more. |

**302 tests were added in this build** — the repository had no
automated test suite at all beforehand (`docs/CURRENT_STATE.md`'s
original audit: "there is no test suite"; the pre-existing `test_*.py`
files were unassertive print-scripts). ai-service: 197 passing + 2
honestly skipped. bda_engine: 96 passing. backend: 7 passing. All 302
were run for real during this build, not assumed to pass. See §3.

---

## 1. What was built (with file references and how it was verified)

### 1.1 Phase 0 — unblocking fixes (prerequisite to everything else)

- [x] **Lazy LLM construction** — `ai-service/app/agent/nodes.py`'s
      `get_model_with_tools()`, `ai-service/app/core/config.py`. The
      service used to crash on import (and `GET /` with it) whenever
      `GROQ_API_KEY` was unset; now it doesn't. Regression-tested in
      `tests/test_app_health.py`.
- [x] **Lazy FAISS retriever** — `ai-service/app/retrieval/retriever.py`.
      Same class of fix; the service no longer requires
      `faiss_index/` to exist just to start.
- [x] **Path-traversal / cross-patient-read guards** —
      `ai-service/app/core/validation.py`, used in
      `app/api/documents.py`, `app/api/ocr.py`, and
      `app/retrieval/patient_retriever.py`. `patient_id` is validated
      as a 24-hex Mongo ObjectId; uploaded filenames are reduced to a
      safe basename before any path join.
- [x] **Real HTTP status codes** — `app/api/documents.py` now returns
      422/500 instead of always 200 with `{"success": false}`.
- [x] **Config made explicit** — CORS origins and the LLM
      provider/model are env-configurable
      (`CORS_ALLOW_ORIGINS`, `LLM_PROVIDER`, `LLM_MODEL`) instead of
      hardcoded.
- [x] **Dead scaffold removed** — `ai-service/src/ai_service/` and its
      `[project.scripts]` entry, per `docs/DOMAIN_MISMATCH.md`.
- [x] **`.env.example`** for all three services; **`docker-compose.yml`**
      (mongo, redis, ai-service, worker, backend, frontend) and
      Dockerfiles for backend/frontend (ai-service already had one,
      extended with `tesseract-ocr`).
- [x] **`AI_SERVICE_URL` default fixed** (8000 → 8080,
      `backend/src/config/env.js`) to match the ai-service container's
      actual port.
- [x] **A real pytest suite** replacing the four manual `test_*.py`
      print-scripts (moved to `ai-service/scripts/manual_*.py`, kept
      as documented manual smoke tests, not deleted).

### 1.2 Week 1 — data lake, schemas, synthetic generator

**Schemas** (`bda_engine/src/bda_engine/schemas/`) — `RawDocument`,
`ExtractedReport`, `BiomarkerObservation`, `PromResponse`, pydantic v2,
JSON Schema exported to `reference/json_schema/*.json`. 21 contract
tests in `bda_engine/tests/test_schemas.py`.

**Reference data** (`reference/` — at the **repo root**, not inside
`bda_engine/`, specifically so `ai-service` can read it as plain data
without depending on `bda_engine`'s heavier packages; see
`bda_engine/src/bda_engine/reference_data.py`'s docstring):

- `biomarkers.yaml` — LOINC code, canonical unit, molar mass,
  plausibility bounds, default reference range for all 9 analytes.
  **Every LOINC code was looked up against loinc.org during this
  build**, not recalled from memory — two initial guesses (Free T3,
  Zinc) were wrong and are corrected in the file with a note on what
  the wrong code actually was:

  | Analyte | LOINC | Canonical unit |
  |---|---|---|
  | TSH | 3016-3 | mIU/L |
  | Free T3 | 3051-0 | pmol/L |
  | Free T4 | 3024-7 | pmol/L |
  | Anti-TPO | 8099-4 | IU/mL |
  | Vitamin D (25-OH) | 62292-8 (D2+D3 combined) | nmol/L |
  | Vitamin B12 | 2132-9 | pmol/L |
  | Ferritin | 2276-4 | µg/L |
  | Magnesium | 2601-3 | mmol/L |
  | Zinc | 5763-8 | µmol/L |

- `unit_conversions.csv` — 21 rows, every factor cross-checked against
  a published clinical-chemistry source (cited per row), round-trip
  tested (`bda_engine/tests/test_reference_data.py`,
  `ai-service/tests/test_units.py`).
- `analyte_synonyms.csv` — 100+ naming variants (≥10 per biomarker).
- `lab_providers.csv` — fictional lab-provider names (deliberately not
  real diagnostic-lab companies).

**Generator** (`bda_engine/src/bda_engine/generate/`):

- `distributions.py` — 5 latent phenotypes (euthyroid_healthy,
  subclinical_hypothyroid, overt_hypothyroid_autoimmune, hyperthyroid,
  micronutrient_deficient). Biomarkers and PROMs are drawn
  **independently**, both conditional on phenotype — not PROMs
  computed from biomarker values — the concrete mitigation for
  ARCHITECTURE.md risk R2 (circular symptom correlation), verified by
  correlation-direction tests (e.g. overt hypothyroid mean TSH ≈ 19.6
  vs. healthy ≈ 1.9 in a real 500-sample draw).
- `render_pdf.py` — 6 layout templates (single-column, two-column,
  boxed-table, borderless-table, header-heavy, multi-panel). Each row
  randomly varies its naming variant, source unit, casing, and
  reference-range format. Verified: every layout's PDF is actually
  text-extractable and contains every printed value.
- `scan_simulate.py` — rasterize + rotate + noise + JPEG-recompress →
  a PDF/PNG with **no text layer**, giving the OCR pipeline real
  scanned input. Verified: the output genuinely has zero extractable
  text where the source PDF has plenty.
- `generate_synthetic_data.py` — orchestrates the above into two
  **deliberately separate** outputs (see its module docstring for
  why): `gold/`+`silver/` (all patients, direct/known values, for the
  analytics lake) and `bronze/lab_reports/`+`bronze/ground_truth/` (a
  smaller rendered-document subset, for scoring the OCR/normalization
  pipeline). Verified end-to-end at n=30 patients / 6 documents: real
  DuckDB reads of the actual Hive-partitioned Parquet output, correct
  counts, correct partition values.

**ETL** (`bda_engine/src/bda_engine/etl/`):

- `engine.py` — DuckDB (default, actually tested) / PySpark
  (`ETL_ENGINE=spark`, optional extra, written but **not** exercised
  against a real Spark session — no JVM was available) facade.
- `silver_to_gold.py` — pivots `biomarker_observations` into
  `gold/patient_feature_vectors/`: one row per (patient, panel_date),
  a **fixed** 9-biomarker column order, explicit
  `<marker>_missing` flags (no silent imputation), cohort z-scores.
  Only `quality_status="ok"` rows are pivoted in — verified with a
  regression test that a `rejected` observation surfaces as missing,
  not as its rejected value.

### 1.3 Week 2 — OCR & async ingestion

All of `ai-service/app/ocr/` shares one `Word` type
(`app/ocr/common.py`) so every stage works identically regardless of
which engine produced the words:

- **`router.py`** — PyMuPDF-based has_text_layer detection. Verified
  against both a real born-digital PDF and a real scan-simulated one.
- **`text_layer.py`** — pdfplumber word+bbox extraction for the
  text-layer path (confidence 1.0, no OCR uncertainty). Verified:
  recovers every printed value from a real generated report.
- **`table_reconstruct.py`** — clusters words into lines (y-overlap),
  first splitting into **column bands** by x-gap so side-by-side
  columns don't merge into one nonsense line (a real bug, caught by a
  failing test on the `two_column` layout, then fixed), then
  classifies tokens into analyte/value/unit/range by position and
  pattern. Verified across all 6 layouts: recovers every printed row
  and its correct unit.
- **`raster.py`** — PyMuPDF rasterization + OpenCV deskew
  (`minAreaRect`-based angle estimate) + denoise. Verified: deskew
  measurably reduces a real, artificially-rotated page's detected skew
  angle; also verified end-to-end on a real scan-simulated document
  and on a raw image upload (see below).
- **`field_extract.py`** — age/sex (combined `"42Y/F"` and labelled
  forms), accession number, lab-provider (rapidfuzz `partial_ratio`
  against `reference/lab_providers.csv`, searched only in the page's
  header region). Verified against real generated report text.
- **`tesseract_engine.py`** — pytesseract `image_to_data` (TSV:
  per-word text + bbox + confidence) wrapper. **The Tesseract binary
  was not available in the build environment** (confirmed via
  `is_available()`, not assumed — see §3). The error-wrapping path
  (missing binary → a clear `RuntimeError`, not a raw pytesseract
  exception) is tested; the actual OCR-through-Tesseract test is
  `skipif`-marked with the real connection-failure reason and will run
  the first time this suite runs in Docker (tesseract-ocr is already
  in `ai-service/Dockerfile`) or on a machine with Tesseract installed.
- **`pipeline.py`** — wires router → text_layer/raster+tesseract →
  table_reconstruct → field_extract → normalizer → units → ref_range →
  data_quality into one `process_document()` function. This is the
  capstone integration test: run end-to-end on real generator PDFs
  across every layout, every recovered observation compared against
  its ground truth (correct biomarker, correct LOINC code, canonical
  value within print-rounding tolerance, correct canonical unit).

**Async job queue** (`ai-service/app/workers/`, `app/api/ocr.py`):

- Celery app with `default`/`ocr` queues, `task_acks_late=True`,
  `worker_prefetch_multiplier=1` (OCR is CPU-bound). One task
  (`process_document_task`) wraps the whole pipeline — **not** the
  four-stage chain originally sketched in `ARCHITECTURE.md`'s sequence
  diagram; see `app/workers/tasks.py`'s docstring for why that
  decomposition doesn't earn its complexity yet (the whole pipeline
  already runs in well under a second in-process) and where per-page
  fan-out would (large multi-page documents — not yet needed at this
  corpus scale).
- `POST /api/ocr/` validates + saves the upload (reusing the Phase-0
  path-traversal guards) and enqueues, returning `202` immediately.
  `GET /api/ocr/jobs/{job_id}` polls status.
- Verified end-to-end via Celery's eager-execution mode (the standard
  way to test Celery tasks without a broker): the full HTTP round trip
  — upload → enqueue → pipeline runs → poll → real observations
  matching ground truth — works. `AsyncResult`'s SUCCESS/FAILURE/
  PENDING response-shaping is verified via a stubbed `AsyncResult`
  (Celery's own result-backend read/write correctness isn't this
  project's code to verify); the one test against the real Redis-backed
  path is `skipif`-marked, confirmed via an actual connection attempt.

**Backend wiring** (`backend/src/`):

- `documentController.js`'s `uploadDocument` now calls the new
  `POST /api/ocr/` (202 immediately) instead of the old synchronous
  `POST /api/documents/process`, which held the Express request open
  for the full OCR+normalization time — that was the actual "blocks
  the request" problem, now fixed. `getDocumentStatus` (new) polls
  `GET /api/ocr/jobs/:jobId` and maps the Celery state onto
  `Document.status`.
- `Document.js`'s status enum extended with the pipeline's
  intermediate states (`queued`, `ocr_running`, `extracted`,
  `normalized`); added `jobId`.
- `uploadMiddleware.js` now also accepts `image/png` and
  `image/jpeg` — verified first, not assumed, that ai-service's
  pipeline actually handles a raw image upload (PyMuPDF opens an
  image file directly as a one-page pseudo-document; `router.py` and
  `raster.py` both work on it unmodified — see
  `tests/test_ocr_router.py::test_raw_scanned_image_has_no_text_layer`).
- `backend/tests/documentController.test.js` — this project's first
  backend test file (Node's built-in `node --test`, now `npm test`;
  no new devDependency). Covers `mapJobStateToStatus`'s full mapping,
  including a check that every mapped value is a real member of
  `Document`'s status enum (reads the enum back from the schema,
  doesn't duplicate the list).
- Verified: the full Express app (`src/app.js`) imports cleanly with
  all these changes.

### 1.4 Week 3 — LOINC mapping, unit conversion, quality

All in `ai-service/app/services/` (a deliberate small duplicate of
`bda_engine`'s reference-data loader, not an import of it — see
§1.2's note on why `reference/` lives at the repo root):

- **`normalizer.py`** — a 5-stage cascade (exact → synonym →
  OCR-word-split-repaired synonym → fuzzy → unmapped), never guessing
  below the fuzzy floor. **Verified against the brief's own adversarial
  example**: `"Tr iodothyronine Free"` → `FT3` via fuzzy match (97.7%
  similarity, measured — not asserted — via rapidfuzz dual-corpus
  scoring on both token-set and space-stripped forms). Also verified:
  `"Free T 3"`, `"T3,Free"`, `"25(OH) Vit-D"`, `"Anti TPO Ab"`,
  `"Vit B-12"` all map correctly; cross-biomarker confusion
  (FT3/FT4, TSH/Anti-TPO) never occurs on their respective clean
  variants.
- **`units.py`** — unit alias canonicalization (`uIU/mL`, `µIU/mL`,
  `μIU/mL`, `mcIU/mL` all fold to one token — the brief's own example)
  plus conversion keyed by `(biomarker, unit)`, never a global
  unit-pair factor (mass↔molar depends on molar mass).
- **`ref_range.py`** — bounded (`"0.4-4.0"`, en/em dash, `"to"`),
  open-ended (`"<4.0"`, `">150"`, `"up to"`), sex-stratified
  (`"Male: 13-150 Female: 12-100"`), and labelled-prefix
  (`"Normal: ..."`) ranges. Deliberately reports banded qualitative
  text (e.g. vitamin D "Deficient/Insufficient/Sufficient") as
  unparsed rather than inventing uncited numeric cutpoints.
- **`data_quality.py`** — plausibility, ref-range-order,
  flag-agreement, duplicate-analyte checks with a
  rejected/suspect/ok severity policy.
- **Feature vectors** — see §1.2's ETL entry (`silver_to_gold.py`);
  this is genuinely a Week 3 deliverable (Step 3.5) implemented in the
  `bda_engine` package because it operates on the same
  `biomarker_observations` table the generator produces.

---

## 2. What's still not done

- [ ] **Full-scale synthetic generation** (50,000 patients / 2,000
      documents) — not run in this environment. The pipeline is proven
      correct at small scale (30 patients / 6 documents,
      real-DuckDB-verified); scaling up is a CLI-flag change
      (`bda_engine/README.md`'s "Full-scale generation" section), not
      a code change, but budget real time/disk before running it.
- [ ] **`OCR_ENGINE=paddle` and `ENABLE_LAYOUTLMV3=true`** — read from
      config, not implemented. `app/ocr/pipeline.py` raises
      `UnsupportedDocumentError` for either. These were always the
      optional/flagged engines in the original design (Tesseract is
      the default); building them out is genuine remaining work, not
      a bug.
- [ ] **Per-page parallel fan-out** for large multi-page documents —
      the current Celery task processes one whole document per task.
      `app/workers/tasks.py`'s docstring identifies exactly where a
      `chord`-based fan-out would go once a real multi-page corpus
      motivates it.
- [ ] **LangGraph checkpointer → Redis** — still `InMemorySaver`
      (conversation memory doesn't survive a restart or scale past one
      replica). Investigated during this build:
      `langgraph-checkpoint-redis`'s `RedisSaver` is a real, correct
      package, but (a) its API is a context manager, needing real
      integration into FastAPI's lifespan rather than a drop-in
      replacement, and (b) it requires Redis Stack modules
      (RedisJSON/RediSearch) the plain `redis:7-alpine` image in
      `docker-compose.yml` doesn't have. Both are genuine scoped
      follow-up work.
- [ ] **Streaming file upload in `documentController.js`** —
      `fs.readFileSync` is still used (multer's existing 10MB cap
      keeps the buffer small; true streaming would need the
      `form-data` npm package, not currently a dependency). The change
      that actually mattered — the request no longer *blocking* on OCR
      completion — is fixed (§1.3); this is a smaller residual
      optimization.
- [ ] **Frontend** — not touched in this build. No lab-upload UI,
      symptom-intake screen, or biomarker dashboard exists yet (still
      the pre-existing hospital-queue mock UI — see
      `docs/DOMAIN_MISMATCH.md` section B for the disposition plan).
      The backend/ai-service APIs this build produced
      (`POST /api/ocr/`, `GET /api/ocr/jobs/:id`) are what a future
      upload UI would call.
- [ ] **GraphRAG / Neo4j, evaluation harness, clinician review
      workflow** — Phase 3/4 items in `docs/ARCHITECTURE.md`, out of
      the Weeks 1-3 scope this document covers.
- [ ] **`uv.lock` files not committed** (both `ai-service/` and
      `bda_engine/`) — no `uv` binary was available in the build
      environment to generate one; dependencies were resolved with
      plain `pip` into a venv instead for verification. Run `uv lock`
      in each project once before a production deploy that wants
      pinned resolution.

---

## 3. Verification environment

This build had: **Python 3.10** (the machine's pinned 3.11 install was
broken — `python.exe` errored with "not a valid Win32 application" —
Python 3.10 was used for all verification; both ai-service and
bda_engine still declare `requires-python = ">=3.11"` for deployment,
and nothing in the new code uses a 3.11-only feature except where
explicitly avoided — see e.g. the `UP042`/`StrEnum` note in each
`pyproject.toml`'s ruff config), **no `uv` binary** (a venv + `pip`
was used instead), **no Tesseract binary**, **no Redis**, **no
Docker**, **no JVM**. Every test that needs one of those either works
around the gap for real (Celery's eager-execution mode; DuckDB instead
of Spark) or is marked `skipif` with the actual failure reason
obtained by trying — e.g. `tests/test_tesseract_engine.py` calls
`pytesseract.get_tesseract_version()` and reports the real
`TesseractNotFoundError` text, `tests/test_ocr_api.py` attempts a real
`redis.Redis(...).ping()` — never assumed from documentation or
guessed.

**What this means for you, running this later:**

- `uv sync` in `ai-service/` and `bda_engine/` will resolve fresh
  (no lock to pin against) — if a dependency has since released a
  breaking version, that's where it would surface. Pin with `uv lock`
  once you've confirmed a working resolution.
- Install Tesseract (see `ai-service/README.md`) to actually exercise
  the scanned-document OCR path; without it, `app/ocr/pipeline.py`
  raises a clear `UnsupportedDocumentError` rather than silently
  producing wrong results.
- Start Redis (`docker-compose.yml`, or standalone) to exercise the
  real async job queue and the `GET /api/ocr/jobs/:id` path against a
  real backend, and to move the LangGraph checkpointer off
  `InMemorySaver` (see §2).
- Every other module (schemas, generator, OCR router/text-layer/table-
  reconstruct/raster/field-extract, normalizer, units, ref_range,
  data_quality, ETL, backend wiring) was actually run, against actual
  generated documents, during this build — not merely written and
  assumed correct.
