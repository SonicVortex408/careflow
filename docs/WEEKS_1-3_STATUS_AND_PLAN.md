# Weeks 1–3 — Status Checklist & Build Plan

**Scope of this document:** the three-week brief covering (1) data-lake
architecture & schema definition, (2) distributed OCR & document ingestion,
(3) entity/unit normalization (LOINC/UMLS mapping).

**Method:** every file in `ai-service/`, `backend/`, `frontend/`, and `docs/`
was read. No code was executed. Keyword sweeps for `loinc`, `umls`, `duckdb`,
`pyspark`, `parquet`, `celery`, `redis`, `faker`, `synthetic`, `biomarker`,
`thyroid`, `ferritin`, `ocr`, `tesseract`, `paddle`, `layoutlm`, `pmol`,
`reference_range`, and `unit_convert` return **zero hits outside `docs/`**
(the three apparent hits are false positives: `Sparkles` from lucide-react,
`Promise`, and `_normalize_content` for LLM message text).

---

## 0. Headline verdict

| Week | Deliverable | State | Evidence |
|---|---|---|---|
| **1** | Data lake + 4 schemas + 50k synthetic generator | **Not started (design only)** | No DuckDB/Postgres/Spark/Parquet anywhere. No generator. No biomarker or PROM schema. |
| **2** | Layout-aware OCR + async queue + lab metadata extraction | **~5% — foundation only** | No OCR at all (not even "basic"); fully synchronous request path; no structured extraction. |
| **3** | LOINC mapping + unit conversion | **Not started** | Zero LOINC/UMLS/unit-conversion code or data files. |

The two prior docs ([`ARCHITECTURE.md`](./ARCHITECTURE.md),
[`DOMAIN_MISMATCH.md`](./DOMAIN_MISMATCH.md)) **do** specify much of this work
as a target design — `bda_engine/`, `graph_service/`, `services/normalizer.py`,
`api/ocr.py`, Celery workers, the Parquet lake, `ETL_ENGINE=spark|duckdb`. None
of it has been implemented. Design credit is real; treat it as the input to the
plan below, not as progress against the brief.

An important framing correction: the brief says *"upgrade basic OCR to a
layout-aware vision parsing pipeline."* **There is no basic OCR to upgrade.**
`ai-service/app/retrieval/patient_ingest.py` uses `PyPDFLoader`, which reads a
PDF's embedded text layer. A scanned PDF or a photographed report yields empty
or near-empty text and is indexed silently with no warning. Week 2 is therefore
a from-scratch build, not an upgrade.

---

## 1. DONE — checklist of what exists today

### 1.1 Document upload path (end-to-end, works)

- [x] **Frontend upload control** — inside `frontend/src/pages/AIAssistant.jsx`
      (1,211 lines; the only page wired to a real backend).
- [x] **Authenticated upload endpoint** — `POST /api/ai/documents`, JWT-guarded,
      role `user` only (`backend/src/controllers/documentController.js:12`).
- [x] **Disk storage with a size/type gate** — multer, 10 MB cap, allowlist
      `application/pdf` + `text/plain`, collision-safe random filenames
      (`backend/src/middleware/uploadMiddleware.js`).
- [x] **Document metadata record in MongoDB** — `backend/src/models/Document.js`:
      `{user, originalName, filename, mimeType, size, storagePath, status}` with
      `timestamps`. This is the closest existing thing to a "raw PDF metadata"
      schema.
- [x] **A usable job-state vocabulary already exists** — `status` enum
      `uploaded | processing | ready | failed` (`Document.js:38-46`). Week 2's
      job model can extend this rather than replace it.
- [x] **Backend → ai-service proxy** — multipart forward carrying `file`,
      `patient_id`, `document_id` (`documentController.js:35-68`).
- [x] **ai-service ingestion endpoint** — `POST /api/documents/process`
      (`ai-service/app/api/documents.py`), saves to
      `patient_documents/<patient_id>/` and calls the ingest function.
- [x] **Text extraction + chunking** — `PyPDFLoader` / `TextLoader` →
      `RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)`
      (`patient_ingest.py:27-28`).
- [x] **Per-chunk provenance metadata** — every chunk carries
      `{patient_id, document_id, source: "patient_upload", filename}`
      (`patient_ingest.py:74-79`). A metadata *convention*, not a schema
      definition, but the right instinct and reusable.
- [x] **Per-patient vector isolation** — one FAISS index per patient under
      `patient_faiss/<patient_id>/`, incrementally appended on re-upload
      (`patient_ingest.py:82-105`).
- [x] **Retrieval wired into chat** — `patient_retriever.get_patient_retriever`
      (`k=5`, returns `None` for a patient with no index) feeds the agent's
      system prompt.
- [x] **Front-matter metadata parser for the global KB** —
      `ingest.py::extract_metadata` parses a YAML-ish block into chunk metadata.
      Reusable shape for biomarker KB documents in a later phase.
- [x] **Failure bookkeeping** — `Document.status` is set to `failed` and
      persisted when the AI leg throws (`documentController.js:112`).

### 1.2 Design/architecture work already banked (docs only, no code)

- [x] Biomarker scope fixed at 9 analytes (TSH, Free T3, Free T4, Anti-TPO,
      Vitamin D 25-OH, B12, Ferritin, Magnesium, Zinc) and 3 PROMs (chronic
      fatigue, brain fog, hair loss) — `ARCHITECTURE.md §1`.
- [x] Decision: MongoDB stays the operational store; **Parquet is the analytics
      lake** — `ARCHITECTURE.md §5, decision 1`.
- [x] Decision: `bda_engine/` as a **separate uv project** so PySpark/XGBoost
      never enter the ai-service runtime image — decision 4.
- [x] Decision: **PySpark with a DuckDB fallback** selected by `ETL_ENGINE` —
      decision 5.
- [x] Decision: **Tesseract default; PaddleOCR + LayoutLMv3 behind flags**
      (`OCR_ENGINE`, `ENABLE_LAYOUTLMV3`) — decision 6.
- [x] Decision: `patient_id` must be validated as a 24-hex ObjectId before any
      path join (closes the current path-traversal surface) — decision 3.
- [x] Env-var inventory for the new services — `ARCHITECTURE.md §6`.
- [x] Risk register including **R2 (circular symptom correlation)** and
      **R3 (OCR accuracy)** — `ARCHITECTURE.md §8`. R2 is the single most
      important scientific caveat for this project and is already written down.
- [x] Upload → OCR → normalize → review sequence diagram — `ARCHITECTURE.md §3`.

---

## 2. NOT DONE — gap checklist

### Week 1 — Data lake & schemas

- [ ] Any analytical store. No PostgreSQL, no DuckDB, no Spark session, no
      Parquet, no `pyarrow`, no `pandas`. `ai-service/pyproject.toml` has none
      of these; MongoDB is the only datastore in the repo.
- [ ] `data_lake/` directory, partitioning convention, or medallion layering.
- [ ] **Schema 1 — raw PDF metadata.** `Document.js` is a start but has no
      `sha256`, `page_count`, `has_text_layer`, `source_channel`, `lab_provider`,
      `job_id`, `ocr_engine`, or error taxonomy.
- [ ] **Schema 2 — extracted tabular JSON.** Nothing exists. Current output is
      opaque 500-char text chunks; no rows, values, units, ranges, bboxes, or
      confidences.
- [ ] **Schema 3 — normalized biomarker entity.** Does not exist in any form.
- [ ] **Schema 4 — PROMs.** No instrument definition, no item codes, no scoring,
      no storage. There is no symptom intake anywhere in the frontend.
- [ ] Schema versioning, validation (pydantic/JSON Schema), or a contract test.
- [ ] Synthetic data generator. No `faker` dependency, no script, no dataset.
- [ ] **Ground-truth labels alongside generated documents** — not in the brief
      verbatim, but Weeks 2 and 3 cannot be measured without them. See §3.1.

### Week 2 — Distributed OCR & ingestion engine

- [ ] **OCR.** No `pytesseract`, `paddleocr`, `easyocr`, `PyMuPDF`, `pdf2image`,
      or `opencv`. Scanned/photographed reports currently produce empty text
      with no error.
- [ ] **Layout awareness.** No table detection, no bounding boxes, no
      row/column reconstruction, no LayoutLMv3.
- [ ] **Image input.** Multer rejects every image mimetype
      (`uploadMiddleware.js` allowlist) and `load_document` raises
      `ValueError` on any suffix other than `.pdf`/`.txt`
      (`patient_ingest.py:48-50`).
- [ ] **Async queue.** No Celery, no Redis, no RQ, no Spark job. The whole
      chain — `readFileSync` → HTTP → PDF parse → embedding → FAISS write — runs
      **inside one synchronous Express request**
      (`documentController.js:35-68`). One slow document blocks a request; a
      large one is read fully into memory.
- [ ] **Job IDs and status polling.** No `job_id` is minted, no
      `GET /api/ocr/jobs/:id`, no `202 Accepted` path. `ARCHITECTURE.md §3`
      specifies this flow; it is not built.
- [ ] **Concurrency.** Single-process, single-document. No worker pool, no
      prefetch tuning, no per-page parallelism for multi-page reports.
- [ ] **Canonical JSON output.** The pipeline's only output is a FAISS index.
- [ ] **Lab metadata extraction** — every field in the brief is missing:
      patient age, patient sex, lab provider, biomarker name, numerical result,
      reference range, units.
- [ ] Per-field confidence scores, `needs_review` flagging, or a correction UI.
- [ ] Idempotency/dedupe. Re-uploading the same file appends duplicate chunks to
      the patient index (`patient_ingest.py:88-98`).
- [ ] Retry, dead-letter, or backpressure handling.

### Week 3 — Entity & unit normalization

- [ ] LOINC concept table, synonym/variant dictionary, or any mapping code.
- [ ] UMLS integration or licence handling.
- [ ] Analyte string normalization (case, punctuation, OCR confusions,
      broken-word repair as in `"Tr iodothyronine Free"`).
- [ ] Fuzzy matching (no `rapidfuzz`/`thefuzz` dependency) or a confidence
      threshold policy.
- [ ] Unit alias canonicalization (`µIU/mL` vs `uIU/mL` vs `mcIU/mL`).
- [ ] Unit conversion table or engine — no `ng/dL → pmol/L`, no
      `pg/mL → pmol/L`, no molar-mass registry.
- [ ] Reference-range parsing (`"0.4 - 4.0"`, `"<4.0"`, `"up to 4.0"`, en-dash
      forms, sex/age-stratified ranges).
- [ ] Uniform feature-vector emission.
- [ ] Unmapped-analyte handling; nothing can currently be marked unmapped
      because nothing maps.

### Cross-cutting blockers that will stop Weeks 1–3 landing cleanly

- [ ] **No test runner in any service.** The three `ai-service/**/test_*.py`
      files are print scripts — no `pytest` dependency, no assertions, no test
      functions. `app/test_agent.py` is an infinite `while True: input()` REPL.
- [ ] **No `.env.example`, no `docker-compose.yml`, no CI.** Redis + a worker +
      an analytical store cannot be run reproducibly without compose.
- [ ] **ai-service crashes at import without `GROQ_API_KEY`**, because
      `init_chat_model` runs at module import (`app/agent/nodes.py:27`). Any new
      OCR endpoint inherits this: the health check 500s too.
- [ ] **`retriever.py` loads `faiss_index/` at import time** — the service will
      not start until `python -m app.retrieval.ingest` has been run.
- [ ] **`AI_SERVICE_URL` default is `http://localhost:8000`** (`env.js`) but the
      ai-service Dockerfile exposes **8080**.
- [ ] **`patient_id` and `file.filename` are joined into paths unsanitised**
      (`documents.py:39,53`) — path-traversal surface, and it is on the exact
      code path Week 2 will expand.
- [ ] **`api/documents.py` returns HTTP 200 with `{"success": false}`** on
      failure (`documents.py:110`) — the backend only catches it via the body
      check. Fix the contract before adding a second async endpoint.

---

## 3. Build plan

Sequencing principle: **Week 1's generator must emit ground truth**, because it
is the only way Weeks 2 and 3 can be measured. Build the schemas first, then the
generator, then the pipeline that fills them.

Target layout (extends `ARCHITECTURE.md §4`):

```
bda_engine/                     NEW — separate uv project
  pyproject.toml
  schemas/
    raw_document.py             pydantic: Schema 1
    extracted_report.py         pydantic: Schema 2
    biomarker_observation.py    pydantic: Schema 3
    prom_response.py            pydantic: Schema 4
    json_schema/*.json          generated, committed, contract-tested
  reference/
    biomarkers.yaml             9 analytes: key, LOINC, canonical unit, molar mass
    analyte_synonyms.csv        biomarker_key, variant, source
    unit_conversions.csv        biomarker_key, from_unit, to_unit, factor, source
    lab_providers.csv           provider name variants → normalized id
  generate/
    generate_synthetic_data.py  CLI: --patients 50000 --seed --out
    distributions.py            marker distributions + PROM coupling
    render_pdf.py               6+ report layouts → PDF
    scan_simulate.py            rasterize + skew/noise/JPEG for the OCR track
  etl/
    engine.py                   ETL_ENGINE=duckdb|spark facade
    bronze_to_silver.py
    silver_to_gold.py
  tests/

data_lake/                      gitignored; regenerable from seed
  bronze/lab_reports/           source PDFs/images, content-addressed by sha256
  bronze/raw_documents/         Parquet, partitioned by ingest_date
  bronze/ground_truth/          JSON per document — generator's own labels
  silver/extracted_results/     Parquet, partitioned by ingest_date
  silver/prom_responses/        Parquet, partitioned by survey_date
  gold/biomarker_observations/  Parquet, partitioned by observed_month
  gold/patient_feature_vectors/ Parquet — one wide row per patient × panel_date

ai-service/app/
  api/ocr.py                    NEW — POST enqueue (202) + GET job status
  workers/celery_app.py         NEW
  workers/tasks.py              NEW — ocr → extract → normalize → persist
  ocr/router.py                 NEW — text-layer vs scanned decision
  ocr/text_layer.py             NEW — pdfplumber table path
  ocr/raster.py                 NEW — PyMuPDF rasterize + deskew/denoise
  ocr/tesseract_engine.py       NEW — TSV words + per-word confidence
  ocr/paddle_engine.py          NEW — behind OCR_ENGINE=paddle
  ocr/layoutlm_engine.py        NEW — behind ENABLE_LAYOUTLMV3
  ocr/table_reconstruct.py      NEW — bbox clustering → rows/columns
  ocr/field_extract.py          NEW — age/sex/provider/accession/dates
  services/normalizer.py        NEW — analyte → LOINC
  services/units.py             NEW — unit canonicalization + conversion
  services/ref_range.py         NEW — reference-range parser
  services/data_quality.py      NEW — plausibility checks
```

### 3.0 Phase 0 — unblock first (~0.5 day, do before anything else)

These are small and every later step depends on them.

1. Add `pytest` + `ruff` to `ai-service` dev deps; convert the three `test_*.py`
   print scripts into real tests or move them to `scripts/`.
2. Make the LLM lazy — wrap `init_chat_model` in an `@lru_cache` factory so the
   service imports (and `GET /` answers) without `GROQ_API_KEY`.
3. Make `retriever.py` load the FAISS index lazily, so a fresh clone starts.
4. Write `.env.example` for all three services; fix the `AI_SERVICE_URL`
   default to `8080`.
5. Validate `patient_id` as a 24-hex ObjectId and sanitise the upload filename
   before any path join (`documents.py:39,53`).
6. Make `api/documents.py` return real HTTP status codes instead of
   `200 {"success": false}`.
7. `docker-compose.yml` with `mongo`, `redis`, `ai-service`, `worker`,
   `backend`, `frontend`.

### 3.1 Week 1 — Data lake architecture & schema definition

**Decision to confirm before starting:** the brief says
"PostgreSQL/DuckDB + Spark". `ARCHITECTURE.md` decision 1/5 already chose
**Parquet + DuckDB default with a PySpark path behind `ETL_ENGINE`**, keeping
Mongo operational. Recommendation: keep that decision — it satisfies the brief
(DuckDB *and* a PySpark context), needs no schema migration, and 50k rows do not
require a cluster. Adding Postgres would be a third datastore for no gain.

**Step 1.1 — define the four schemas as pydantic models** (`bda_engine/schemas/`),
export JSON Schema, and commit both. Field lists below are the contract; treat
any addition as a schema-version bump.

*Schema 1 — `RawDocument`* (bronze; also the shape `Document.js` should grow into)
```
document_id  patient_id  sha256  original_name  stored_uri  mime_type
size_bytes  page_count  has_text_layer  source_channel(patient_upload|synthetic|bulk)
is_synthetic  ingest_status(uploaded|queued|ocr_running|extracted|normalized|failed)
job_id  ocr_engine  ocr_engine_version  ingest_date(partition)
created_at  updated_at  error_code  error_message
```

*Schema 2 — `ExtractedReport`* (silver; one per document, the canonical OCR JSON)
```
document_id  patient_id  schema_version
extraction { engine, engine_version, layout_model, duration_ms,
             pages[]{page_no, width, height, rotation, mean_word_confidence} }
patient_context { age_years, age_confidence, sex, sex_confidence }
lab { provider_name_raw, provider_id, accession_no, collected_at, reported_at }
panels[] { panel_name_raw, page_no, table_index }
rows[] { row_id, page_no, table_index, row_index,
         analyte_name_raw,
         value_raw, value_numeric, comparator(<|>|=|none), is_numeric,
         unit_raw,
         reference_range_raw, ref_low, ref_high, ref_operator,
         flag_raw(H|L|N), method_raw,
         bbox[x0,y0,x1,y1],
         confidence{analyte, value, unit, range},
         needs_review }
warnings[]
```
`rows[]` is the join key for Week 3 — one row per biomarker occurrence, still
verbatim from the page, nothing normalized yet. Keeping raw and normalized
separate is what makes a bad mapping auditable later.

*Schema 3 — `BiomarkerObservation`* (gold; the normalized entity)
```
observation_id  document_id  row_id  patient_id
biomarker_key   (TSH|FT3|FT4|ANTI_TPO|VIT_D_25OH|VIT_B12|FERRITIN|MAGNESIUM|ZINC)
loinc_code  loinc_long_name  mapping_confidence
mapping_method  (exact|synonym|fuzzy|manual|unmapped)
value_canonical  unit_canonical
value_source  unit_source  conversion_factor  conversion_source
ref_low_canonical  ref_high_canonical  ref_basis(lab_stated|fallback_default)
lab_provider_id  patient_age_years  patient_sex
collected_at  observed_month(partition)
quality { status(ok|suspect|rejected), checks[] }
provenance { ocr_confidence, needs_review, reviewed_by, reviewed_at }
is_synthetic
```

*Schema 4 — `PromResponse`* (silver)
```
response_id  patient_id  instrument("CAREFLOW_PROM_V1")  instrument_version
submitted_at  survey_date(partition)  recall_window_days
items[] { item_code(FATIGUE_SEVERITY|BRAIN_FOG_FREQUENCY|HAIR_LOSS),
          value_raw, value_numeric, scale_min, scale_max, scale_type(nrs|ordinal) }
derived { fatigue_score, brain_fog_score, hair_loss_score, composite_burden }
is_synthetic
```
Fix the three instruments now: fatigue = 1–10 NRS, brain fog = 0–4 ordinal
frequency (never/rarely/sometimes/often/always), hair loss = 0–4 ordinal
severity. `ARCHITECTURE.md §1` says "severity 1–10 / frequency" — this pins it.

**Step 1.2 — reference data files.** `biomarkers.yaml` holds, per analyte:
`biomarker_key`, `loinc_code`, `loinc_long_name`, `canonical_unit`,
`molar_mass_g_mol`, `plausible_min`, `plausible_max`, `default_ref_low/high`,
and a `source` URL per row.

Proposed canonical units (SI-leaning, one per analyte, no exceptions):

| Analyte | Canonical unit | Common source units to convert |
|---|---|---|
| TSH | mIU/L | µIU/mL, uIU/mL, mU/L (all 1:1) |
| Free T3 | pmol/L | pg/mL (×1.536) |
| Free T4 | pmol/L | ng/dL (×12.87), pg/mL (×1.287) |
| Anti-TPO | IU/mL | kIU/L (1:1), U/mL (1:1) |
| Vitamin D 25-OH | nmol/L | ng/mL (×2.496) |
| Vitamin B12 | pmol/L | pg/mL (×0.7378) |
| Ferritin | µg/L | ng/mL (1:1) |
| Magnesium | mmol/L | mg/dL (×0.4114), mEq/L (×0.5) |
| Zinc | µmol/L | µg/dL (×0.1530) |

> **Verify before trusting.** These factors are the standard mass↔molar
> conversions and are given here so the table has a concrete starting point, but
> **every factor and every LOINC code must be checked against a citable source**
> (the LOINC release for codes, a reference lab or IFCC table for factors) and
> the `source` column filled in. Do not ship a factor with an empty `source`.
> Note also that **LOINC and UMLS both require accepting a licence** — LOINC is
> free after registration; UMLS needs a UTS account. Decide early whether UMLS
> is in scope or whether LOINC alone is enough (recommendation: LOINC only for
> these 9 analytes; UMLS adds licence friction for no coverage gain here).

**Step 1.3 — synthetic generator** (`bda_engine/generate/`), CLI:
`--patients 50000 --seed 42 --pdf-count 2000 --out data_lake/`.

- Draw age/sex/region from realistic marginals via Faker + numpy.
- Draw the 9 markers from per-analyte log-normal/normal distributions with a
  **correlation structure** (TSH↔FT4 inverse; FT3↔FT4 positive; Anti-TPO
  elevated in a hypothyroid subpopulation; ferritin sex-dependent).
- Assign each patient to one of ~5 latent phenotypes, then draw PROMs
  conditional on phenotype — **not** directly from marker values. This is the
  concrete mitigation for risk **R2**: keep the generative parameters in a
  manifest, hold them out of the modelling code, and state in
  `evaluation/REPORT.md` that any recovered correlation is partly circular.
- **Heterogeneity is the point.** Vary per report: which analytes appear (1–9),
  analyte naming variant, unit choice, reference-range format and whether a
  range is printed at all, lab provider, date formats, page count (1–4),
  layout template (target ≥6: single-column, two-column, boxed-table,
  borderless-table, header-heavy, multi-panel), plus a "missing/illegible
  field" rate.
- `render_pdf.py` — **reportlab** for the templates (pure-Python wheels; no GTK
  or system libraries, which matters on the Windows dev box). WeasyPrint is
  optional and not recommended as the default for this reason.
- `scan_simulate.py` — for a configurable fraction (suggest 40%), rasterize the
  PDF and apply rotation ±2°, gaussian noise, contrast shift, and JPEG
  artifacts, then re-wrap as a PDF or emit PNG. **Without this, the OCR track
  has no scanned inputs to prove itself against.**
- **Emit ground truth** to `bronze/ground_truth/<document_id>.json` for every
  rendered document: the exact analyte name string printed, the printed value
  and unit, the printed range, the true canonical value, and the true
  `biomarker_key`/LOINC. This file is what Weeks 2 and 3 are scored against.

**Step 1.4 — ETL facade.** `etl/engine.py` exposes `read_table` / `write_table`
and dispatches on `ETL_ENGINE` (`duckdb` default, `spark` optional extra). Both
paths write Hive-partitioned Parquet via `pyarrow`, so either engine can read
the other's output. `bronze_to_silver.py` and `silver_to_gold.py` are then
engine-agnostic.

**Dependencies to add** (`bda_engine/pyproject.toml`): `faker`, `numpy`,
`pandas`, `pyarrow`, `duckdb`, `scipy`, `reportlab`, `pillow`, `pydantic>=2`,
`pyyaml`, `typer`; optional extra `spark = ["pyspark"]`.

**Acceptance criteria**
- `uv run python -m bda_engine.generate.generate_synthetic_data --patients 50000 --seed 42`
  completes and reports counts.
- ≥50,000 patients, ≥250,000 observation rows, ≥2,000 rendered documents across
  ≥6 layouts, ≥40% of them scan-simulated.
- Every Parquet partition validates against its JSON Schema (a test asserts this).
- The same `--seed` reproduces byte-identical Parquet.
- DuckDB **and** a local Spark session can both read `gold/`.
- A ground-truth JSON exists for every rendered document.

### 3.2 Week 2 — Distributed OCR & document ingestion engine

**Step 2.1 — turn upload into a job (do this before OCR).** Mint a `job_id`,
return `202 {report_id, job_id}`, enqueue, and poll. Concretely:
`POST /api/ocr` on the ai-service enqueues and returns immediately;
`GET /api/ocr/jobs/{job_id}` returns
`{state, progress, pages_done, result_uri, error}`. The backend proxies both and
stops calling `fs.readFileSync` — stream the file instead
(`documentController.js:35`). `Document.status` extends to
`uploaded|queued|ocr_running|extracted|normalized|ready|failed`, keeping the
existing four values valid.

**Step 2.2 — Celery + Redis.** `workers/celery_app.py` with
`CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`; a `default` queue for cheap work
and an `ocr` queue with `worker_prefetch_multiplier=1` and
`--concurrency=<cores>` because OCR is CPU-bound. Task chain:

```
ocr.extract_document(document_id)
  → normalize.map_report(document_id)
    → quality.check_report(document_id)
      → persist.index_and_store(document_id)
```

Per-page fan-out for multi-page reports: `chord(ocr_page.s(p) for p in pages)`
→ `assemble_report.s()`. This is where the "concurrently" requirement is
actually met. Set `acks_late=True`, `max_retries=3` with exponential backoff,
and a dead-letter queue; idempotency key = `sha256` of the file, so a
re-uploaded document short-circuits instead of duplicating chunks
(today it duplicates — `patient_ingest.py:88-98`).

> Note: `ARCHITECTURE.md` decision 11 also moves the LangGraph checkpointer off
> `InMemorySaver` once Redis exists. Redis lands here, so schedule that move in
> the same phase — conversation memory currently dies with the process.

**Step 2.3 — routing: text layer vs scanned.** `ocr/router.py` opens the PDF
with PyMuPDF, measures extractable characters per page, and sets
`has_text_layer`. Then:
- **Text-layer path** — `pdfplumber` `extract_tables()` plus word boxes.
  Fast, near-exact, and it will handle most digitally-generated lab PDFs.
  Confidence 1.0 for these fields.
- **Scanned path** — `ocr/raster.py` renders at 300 dpi, deskews (OpenCV
  `minAreaRect` on the text mask), denoises, and binarizes (Otsu/adaptive);
  then `ocr/tesseract_engine.py` runs `image_to_data(..., output_type=TSV)`
  to get per-word text **plus bbox plus confidence**, which is what makes
  per-field confidence scoring possible at all.

**Step 2.4 — table reconstruction** (`ocr/table_reconstruct.py`). Cluster word
bboxes into lines by y-overlap, then into columns by x-gap histogram; detect
ruling lines with OpenCV morphology when present and prefer them. Classify each
column by content: analyte name (alpha-dominant), result (numeric), unit
(unit-lexicon match), reference range (range-pattern match), flag (single
H/L/N). Emit `ExtractedReport.rows[]`.

**Step 2.5 — layout-aware upgrade behind a flag.** `ENABLE_LAYOUTLMV3=true`
swaps in `ocr/layoutlm_engine.py`: LayoutLMv3 token classification over
(text, bbox, image) with labels
`ANALYTE | VALUE | UNIT | REF_RANGE | FLAG | HEADER | OTHER`. Fine-tune on the
Week 1 synthetic corpus — the ground-truth JSON plus rendered bboxes give
labelled training data **for free**, which is the strongest argument for doing
Week 1 properly first. Keep the heuristic reconstructor as the fallback and
compare both on the same held-out set. `OCR_ENGINE=paddle` similarly selects
PaddleOCR (better on rotated/low-quality scans; heavier wheels).

**Step 2.6 — lab metadata extraction** (`ocr/field_extract.py`), the explicit
brief list:
- **Age** — regex family over `Age: 42`, `42 Y`, `42Y/M`, `DOB: 1983-04-02`
  (compute against `collected_at`).
- **Sex** — `Sex|Gender: M|F|Male|Female`, plus the combined `42Y/F` form.
- **Lab provider** — search the top ~25% of page 1 against
  `reference/lab_providers.csv` with fuzzy matching; fall back to the most
  frequent non-analyte header string.
- **Biomarker name / result / unit / reference range** — from `rows[]` above.
- **Accession, collected_at, reported_at** — labelled-date regexes with
  `dateutil` parsing and a multi-format tolerance.

Every field carries a confidence; anything below threshold sets `needs_review`.

**Dependencies to add** (`ai-service`): `celery[redis]`, `redis`, `pymupdf`,
`pdfplumber`, `pytesseract`, `opencv-python-headless`, `pillow`,
`python-dateutil`, `rapidfuzz`; optional extras `paddle = ["paddleocr",
"paddlepaddle"]`, `layoutlm = ["transformers", "torch"]` (torch is already
present transitively via sentence-transformers — pin CPU-only).
**System dependency:** the Tesseract binary. Install it in the Docker image
(`apt-get install -y tesseract-ocr`); on Windows it needs a separate installer
and `TESSERACT_CMD` pointing at the exe. Document both.

**Acceptance criteria**
- Upload returns `202` in <300 ms; no HTTP request holds an OCR call.
- 2,000 synthetic documents process through the queue; report throughput at
  concurrency 1/2/4/8.
- Against Week 1 ground truth: analyte-name exact-match, value within 1e-6
  relative tolerance, unit exact-match, reference-range exact-match — report all
  four, split by text-layer vs scan-simulated. Set the target after the first
  baseline run rather than guessing it now.
- Every failure lands in the dead-letter queue with `error_code` set; none fail
  silently.
- Re-uploading an identical file creates no duplicate chunks.
- A scanned image upload (PNG/JPEG) succeeds end to end — requires widening the
  multer allowlist.

### 3.3 Week 3 — Entity & unit normalization (LOINC mapping)

**Step 3.1 — `services/normalizer.py`, a deterministic cascade.** Each stage
records `mapping_method` and a confidence; the first hit wins:

1. **Canonicalize the string** — lowercase; strip punctuation; collapse
   whitespace; drop matrix/qualifier stopwords (`serum`, `plasma`, `level`,
   `total`, `s.`, `test`); expand abbreviations (`ft3`→`free t3`,
   `t.p.o`→`tpo`, `25(oh)d`→`25 hydroxy vitamin d`); repair OCR confusions
   (`0`↔`O`, `1`↔`l`↔`I`, `rn`↔`m`, `5`↔`S`); and **repair broken words** by
   trying adjacent-token joins — this is exactly the
   `"Tr iodothyronine Free"` → `"triiodothyronine free"` case in the brief, and
   a token-join pass plus order-insensitive matching is what solves it.
2. **Exact match** on canonicalized form against `analyte_synonyms.csv`.
3. **Synonym/variant match** — the curated table. Seed ≥15 variants per
   analyte (e.g. FT3: `free t3`, `ft3`, `t3 free`, `free triiodothyronine`,
   `triiodothyronine free`, `ft-3`, `free tri-iodothyronine`, …). Mine more
   variants automatically from the Week 1 generator's naming-variant list, then
   hand-review.
4. **Fuzzy match** — `rapidfuzz.token_set_ratio` (order-insensitive, which the
   `"Tr iodothyronine Free"` word order needs). Accept ≥92 as `fuzzy`; 80–92
   maps but sets `needs_review`; <80 is **`unmapped`**.
5. **Never guess.** `unmapped` rows are persisted with `biomarker_key = null`
   and surfaced in a review queue. A silent wrong mapping is far worse than an
   explicit gap.

Attach `loinc_code` from `biomarkers.yaml` once `biomarker_key` is known — the
LOINC code is a property of the canonical analyte, not of the raw string, so
there is exactly one place to correct a bad code.

**Step 3.2 — `services/units.py`.**
- *Alias canonicalization* first: normalize micro-sign variants
  (`µ`, `μ`, `u`, `mc`), case (`ML`→`mL`), separators (`per`, `/`), and
  whitespace. `µIU/mL`, `uIU/mL`, `mcIU/mL`, `µiu/ml` all collapse to one token.
- *Conversion* second: look up `(biomarker_key, from_unit, to_unit)` in
  `unit_conversions.csv` → `value * factor`. Keying by analyte is essential
  because mass↔molar depends on molar mass — `ng/dL → pmol/L` is **not** one
  global factor. Store `conversion_factor` and `conversion_source` on the
  observation so any number can be traced back.
- Unknown unit ⇒ `quality.status = "suspect"`, `needs_review = true`, value
  kept raw and **excluded from feature vectors**. Never assume the canonical
  unit when the unit is missing.
- Consider `pint` for dimensional checking, but keep the CSV as the source of
  truth for the mass↔molar factors — the audit trail matters more than the
  elegance.

**Step 3.3 — `services/ref_range.py`.** Parse, in priority order:
`"0.4 - 4.0"`, `"0.4–4.0"` (en/em dash), `"0.4 to 4.0"`, `"<4.0"`, `">150"`,
`"≤4.0"`, `"up to 4.0"`, `"Normal: 0.4-4.0"`, `"Male: 13-150 Female: 12-100"`
(select by extracted sex), and banded text like
`"Deficient/Insufficient/Sufficient"` (map to numeric cut-points). Convert the
parsed bounds through the **same** unit path as the value, then fall back to
`biomarkers.yaml` defaults with `ref_basis = "fallback_default"` when the report
printed no range. A lab-stated range always beats a default.

**Step 3.4 — `services/data_quality.py`.** Per observation: plausibility bounds
from `biomarkers.yaml`; unit-mismatch detection (a TSH of `2500` is `µIU/L` or
an OCR decimal slip, not a real value); `ref_low < ref_high`; duplicate
analyte within one report; value/flag agreement (flag says `H` but value sits
inside the range). Each check appends to `quality.checks[]` and can set
`ok | suspect | rejected`.

**Step 3.5 — uniform feature vectors.** `silver_to_gold.py` pivots
`biomarker_observations` to one row per `(patient_id, panel_date)` with a fixed
9-column ordering, plus `<marker>_missing` indicator columns and
`<marker>_zscore` against the cohort. Fixed column order and explicit
missingness flags are what make the vector safe to hand to a model. Imputation
belongs in `bda_engine/features/`, downstream, never in the normalizer.

**Step 3.6 — expose it.** `POST /api/normalize` (dry-run: raw rows in,
normalized out) for testing and for a clinician correction UI, plus the
in-pipeline call from `workers/tasks.py`. A manual correction writes back to
`analyte_synonyms.csv` as `source = "manual_review"` so the mapping table
improves over time.

**Acceptance criteria**
- Mapping coverage ≥99% of generated rows (the generator's variants are known,
  so anything less is a real bug).
- **Zero wrong mappings** on the ground-truth set — measure precision, not just
  coverage; report unmapped separately from misrouted.
- A dedicated adversarial-variant test set including
  `"Tr iodothyronine Free"`, `"FT3"`, `"Free T 3"`, `"T3,Free"`,
  `"25(OH) Vit-D"`, `"Anti TPO Ab"`, `"Vit B-12"`.
- Round-trip property test: convert source→canonical→source for every row in
  `unit_conversions.csv` and assert recovery within 1e-9.
- Every factor and every LOINC code in the reference files has a non-empty
  `source`; a test asserts this.
- No observation reaches `gold/` with `mapping_method = "unmapped"` and
  `quality.status = "ok"`.

---

## 4. Next steps, in order

1. **Confirm the open decisions** in §5 — 1 and 3 change the file layout and the
   generator's runtime, so settle them before writing code.
2. **Phase 0 unblockers** (§3.0). Half a day. Nothing else is testable until
   `pytest` exists and the service imports without a Groq key.
3. **Week 1 Step 1.1 — the four pydantic schemas + JSON Schema export.** These
   are the contract every later phase codes against; land them in their own PR
   and review the field lists carefully.
4. **Week 1 Step 1.2 — reference data files**, with `source` filled in for
   every LOINC code and conversion factor. Do this before the generator, which
   reads the same files.
5. **Week 1 Step 1.3 — the generator, including ground truth and
   scan simulation.** Do not skip `scan_simulate.py`; without it Week 2's OCR
   has nothing real to prove.
6. **Week 1 Step 1.4 — ETL facade + bronze→silver→gold**, verified readable by
   both DuckDB and Spark.
7. **Week 2 Step 2.1–2.2 — jobs and Celery before any OCR code.** Getting the
   async contract right first means the OCR engines plug into a working
   pipeline instead of the reverse. Move the LangGraph checkpointer to Redis in
   the same PR.
8. **Week 2 Step 2.3–2.4 — text-layer path first, then the scanned path.** The
   text-layer path is cheap and will carry most documents; it also gives a
   correctness baseline for the OCR path to be measured against.
9. **Week 2 Step 2.6 — field extraction**, then measure against ground truth
   and set the accuracy targets from that baseline.
10. **Week 3 Steps 3.1–3.3 — normalizer, units, ranges**, each with its own
    test file. Build the adversarial-variant test set first and let it drive
    the implementation.
11. **Week 3 Steps 3.4–3.5 — quality checks and feature vectors**, closing the
    loop into `gold/patient_feature_vectors/`.
12. **Week 2 Step 2.5 — LayoutLMv3 behind the flag, last.** It is the optional
    upgrade; it needs the labelled corpus from step 5 and a working heuristic
    baseline to beat.

One branch and one PR per numbered step. Add a GitHub Actions workflow running
`ruff` + `pytest` at step 2 so every subsequent PR is gated.

---

## 5. Open decisions needing sign-off

| # | Question | Recommendation |
|---|---|---|
| 1 | Postgres, or Parquet + DuckDB with a PySpark path? | **Parquet + DuckDB default, PySpark behind `ETL_ENGINE`** — matches `ARCHITECTURE.md` decisions 1/5, satisfies the brief, avoids a third datastore. |
| 2 | Is **UMLS** in scope, or is LOINC enough? | **LOINC only.** Nine analytes need no UMLS breadth, and UMLS adds a UTS licence dependency. Revisit if the analyte list grows. |
| 3 | 50,000 **patients**, or 50,000 rendered **PDF documents**? | The brief says "50,000+ heterogeneous lab reports". Rendering 50k PDFs is feasible but slow and disk-heavy. **Recommendation: 50k+ patient/report records in Parquet, of which ~2,000 are rendered as actual PDFs/images** for the OCR track. Confirm this reading — if 50k rendered documents are genuinely required, budget the render time and parallelize `render_pdf.py`. |
| 4 | Where do PROMs get collected in the UI? | No symptom intake exists in the frontend. Week 1 only needs the schema and synthetic PROMs; the intake screen is frontend work that can land later, but schedule it explicitly rather than assuming it. |
| 5 | Tesseract on the Windows dev box | It is a system binary, not a wheel. Either install it locally and set `TESSERACT_CMD`, or run the worker only in Docker. Decide before step 8. |
