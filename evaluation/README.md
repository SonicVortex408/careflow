# evaluation/

Week 13 benchmarks. Results → `results/*.json`, plots → `figures/`, write-up → [`REPORT.md`](REPORT.md).

| Script | Environment | Measures |
|---|---|---|
| `run_bda_eval.py` | `cd bda_engine && uv run python ../evaluation/run_bda_eval.py` | ETL reconciliation, OCR CER/WER + field accuracy (500 PDFs), clustering (silhouette, DBI, ARI vs hidden phenotypes), risk AUROC/calibration/SHAP, functional bands vs hidden generator thresholds |
| `run_ai_eval.py` | `cd ai-service && uv run python ../evaluation/run_ai_eval.py` | guardrail red-team recall / false positives, summary readability + grounding over 500 reports, assistant behaviour cases, KB retrieval |

`cases/` holds the red-team sentences, assistant behaviour cases (schema kept
from the original `visible-cases.json`) and retrieval queries. The bda
evaluation is the only code that reads `bda_engine/data/holdout/`.
