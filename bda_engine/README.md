# bda_engine — offline big-data engine

Builds the synthetic multi-source lab data lake and the population-level models
the ai-service uses online. **Everything here is derived from synthetic data, for
research/demo purposes, not clinical guidance.**

```
raw (CSV/JSONL per lab, intake JSONL, PDFs)
  └─ etl/lake.py ──► bronze ──► silver (LOINC + SI + quality flags) ──► gold (1 row / patient)
  └─ etl/ocr_batch.py ─ distributed OCR (Spark mapPartitions | process pool) ──► lake/extracted
gold ─► features/build.py ─► models/clustering.py      K-Means · GMM · DBSCAN
                          ─► models/functional_ranges.py spline-logistic threshold discovery
                          ─► models/risk.py            XGBoost + isotonic calibration + TreeSHAP
                          ─► models/export.py          versioned artifacts + manifest.json
```

## Quick start

```bash
uv sync                    # add --extra spark for PySpark (needs Java 17+)
uv run bda all             # generate -> etl -> ocr -> train   (~8 min on 4 cores)
ETL_ENGINE=spark uv run bda etl
uv run pytest              # small-scale end-to-end, incl. Spark/DuckDB parity
```

| Env var | Default | |
|---|---|---|
| `ETL_ENGINE` | `duckdb` | `spark` runs the same SQL on PySpark (`SPARK_MASTER`, default `local[*]`) |
| `SYNTHETIC_SEED` | `42` | seeds generator and models; part of every artifact name |
| `N_PATIENTS` / `N_PDFS` | `50000` / `500` | |
| `BDA_DATA_DIR` | `bda_engine/data` | raw / holdout / lake (git-ignored) |
| `MODEL_ARTIFACT_DIR` | `<repo>/models` | shared volume with ai-service in compose |
| `MODEL_SEMVER` | `1.0.0` | |

## Layout

| Path | What |
|---|---|
| `schemas/` | lake zone schemas (`lake.py`) and the canonical report JSON schema |
| `scripts/generate_synthetic_data.py` | 50k patients, ~67k reports, ~500k lab rows from 5 labs with different labels/units/formats, free-text intake forms, ~500 PDFs in 4 layouts (35% scanned) |
| `etl/engine.py` | `DuckDBEngine` / `SparkEngine` behind one interface |
| `etl/lake.py` | the ETL as portable SQL; label→LOINC map broadcast from the shared normalizer |
| `etl/ocr_batch.py` | batch OCR using the same `polymarker_common.pipeline` as the online worker |
| `features/build.py` | log transforms, FT3/FT4, ferritin-to-TSH, TSH×FT4, interaction terms, deficit count, sex×age-band median imputation + missingness flags |
| `models/` | clustering, functional bands, risk models, artifact export |
| `pipeline.py` | `bda generate|etl|ocr|train|all` |

## Held-out generator (validity threat R2)

Symptoms are generated *from* marker values. Models trained on this data partly
rediscover those rules, so "discoveries" are not findings. The generator's
parameters are written to `data/holdout/` and are never read by ETL or training;
`evaluation/` compares discovered thresholds with them and reports the
circularity as a limitation.

## Artifacts (`MODEL_ARTIFACT_DIR`)

`{model}_{semver}_s{seed}.{json|ubj}` indexed by `manifest.json` (sha256, bytes,
catalog version, synthetic label). The ai-service loads only through the
manifest. A reference artifact set (seed 42, 50k patients) is committed under
`/models` so the stack works without running the ~8 min pipeline.
