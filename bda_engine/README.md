# bda_engine

careFlow's big-data engine: the Week 1 synthetic lab-report generator,
the four data-lake schemas, and the bronze -> silver -> gold ETL.

A separate `uv` project from `ai-service/` on purpose (see
`docs/ARCHITECTURE.md` decision 4): this package's dependencies
(pandas, faker, reportlab, duckdb, the optional PySpark extra) are
irrelevant to a request-serving API and are kept out of that runtime
image.

See `docs/WEEKS_1-3_STATUS_AND_PLAN.md` section 3.1 for the full design
and `docs/BDA_ENGINE.md` for usage instructions once generation has been
run at scale.

## Quick start

```bash
cd bda_engine
uv sync
uv run pytest                                    # 56+ tests, no external services needed
uv run python scripts/export_json_schema.py       # regenerate reference/json_schema/*.json
uv run generate-synthetic-data --patients 50000 --pdf-count 2000 --seed 42
```

## Layout

```
src/bda_engine/
  schemas/      pydantic: RawDocument, ExtractedReport, BiomarkerObservation, PromResponse
  generate/     distributions.py, render_pdf.py, scan_simulate.py, generate_synthetic_data.py
  etl/          engine.py (DuckDB/PySpark facade), bronze_to_silver.py, silver_to_gold.py
reference/      ../reference/ at the repo root -- shared with ai-service, see
                src/bda_engine/reference_data.py for why it lives there
tests/          pytest, no external services required
```
