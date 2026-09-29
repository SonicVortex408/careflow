# bda_engine

careFlow's big-data engine: the Week 1 synthetic lab-report generator,
the four data-lake schemas, and the bronze -> silver -> gold ETL /
feature-vector pipeline (Week 3, Step 3.5).

A separate `uv` project from `ai-service/` on purpose (see
`../docs/ARCHITECTURE.md` decision 4): this package's dependencies
(pandas, faker, reportlab, duckdb, the optional PySpark extra) are
irrelevant to a request-serving API and are kept out of that runtime
image. `ai-service/app/services/` re-implements the small pieces it
needs (reading `../reference/`, converting units) independently rather
than importing this package -- see
`ai-service/app/services/reference_data.py`'s docstring.

See `../docs/WEEKS_1-3_STATUS_AND_PLAN.md` section 3.1 for the full
design this implements.

## Quick start

```bash
cd bda_engine
uv sync
uv run pytest                                 # 96 tests, ~7s, no external services needed

# Small-scale sanity run (seconds, a few MB):
uv run generate-synthetic-data --patients 50 --pdf-count 8 --seed 42 --out /tmp/data_lake

# Full-scale run (NOT run in the environment this was built in -- budget
# real time and disk; see "Full-scale generation" below):
uv run generate-synthetic-data --patients 50000 --pdf-count 2000 --seed 42

uv run python scripts/export_json_schema.py   # regenerate reference/json_schema/*.json
```

## Layout

```
src/bda_engine/
  schemas/           pydantic: RawDocument, ExtractedReport, BiomarkerObservation, PromResponse
  reference_data.py  loaders for ../reference/ (biomarkers.yaml, *.csv)
  generate/
    distributions.py         5 latent phenotypes -> biomarker + PROM sampling
    render_pdf.py             6 layout templates (reportlab)
    scan_simulate.py          rasterize + degrade -> no-text-layer PDFs/PNGs
    generate_synthetic_data.py  orchestrates the above -> data_lake/
  etl/
    engine.py          DuckDB (default) / PySpark (ETL_ENGINE=spark, optional
                        extra) read/write facade
    silver_to_gold.py  pivots biomarker_observations -> patient_feature_vectors
reference/            ../reference/ at the repo root -- shared with ai-service,
                       see src/bda_engine/reference_data.py for why it lives there
tests/                 pytest, no external services required
```

## Output layout (`data_lake/`, gitignored -- regenerate from `--seed`)

```
data_lake/
  gold/
    patients.parquet                  every --patients patient, direct/known values
    biomarker_observations/           Hive-partitioned by biomarker_key
  silver/
    prom_responses.parquet
  bronze/
    lab_reports/<document_id>.pdf     the --pdf-count rendered subset (some
                                       scan-simulated -- see scan_simulate.py)
    ground_truth/<document_id>.json   what's actually printed on each document,
                                       plus the true canonical mapping --
                                       this is what ai-service's OCR/
                                       normalization pipeline is scored against
    raw_documents/                    Hive-partitioned by ingest_date
```

**These two outputs are deliberately kept separate** (see
`generate_synthetic_data.py`'s module docstring): `gold/` has every
patient's biomarkers directly, computed with no OCR involved
(`mapping_method="exact"`); `bronze/ground_truth/` is a much smaller
set of actual rendered documents used only to measure the OCR/
normalization pipeline's accuracy. Running that pipeline on the
`bronze/` documents and writing its output back into `gold/` would
double-count those patients against their already-known values, so
that wiring intentionally doesn't exist here.

## Full-scale generation

`--patients 50000 --pdf-count 2000` was **not run** in the environment
this was built in -- the test suite (`uv run pytest`) proves the
pipeline correct at small scale (30 patients / 6 documents in
`tests/test_generate_synthetic_data.py`), and scaling up is then just
changing the CLI flags, not a code change. Before running it at full
scale, budget:

- **Time**: rendering ~2,000 PDFs (reportlab) plus scan-simulating
  ~40% of them (PyMuPDF rasterize + OpenCV/PIL degradation at 200-300
  dpi) is the slow part; the 50,000 direct-value patient rows are fast
  (pure numpy/pandas). Time a `--pdf-count 100` run first and
  extrapolate.
- **Disk**: each rendered PDF is a few KB; each scan-simulated PDF
  (rasterized to an image and JPEG-recompressed) is much larger,
  typically 200KB-1MB depending on dpi. 2,000 documents at ~40% scanned
  could be low hundreds of MB, not GBs, but verify locally.
- **`--seed`**: fixed, so the same seed reproduces byte-identical
  output -- pick and record a seed to run once, not repeatedly.

## Known gaps (see `../docs/WEEKS_1-3_STATUS_AND_PLAN.md` for the full list)

- `etl/engine.py`'s `SparkEngine` was written but never exercised
  against a real Spark session -- no JVM was available in this build
  environment. `DuckDBEngine` (the default) is what the test suite
  actually runs.
- The phenotype means/distributions in `generate/distributions.py` are
  illustrative and plausible, not fit to any real clinical dataset --
  every value this project produces is labelled "derived from
  synthetic data" per `../docs/ARCHITECTURE.md`'s synthetic-data rule.
  See that module's docstring for the R2 validity-threat note (PROMs
  are drawn independently of biomarkers, both conditional on the same
  phenotype -- correlated for the right structural reason, not because
  one was computed from the other, but still the generator's own rule).
