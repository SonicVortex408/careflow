# PolyMarker Analytics — Evaluation Report (Week 13)

> **All population-level results in this report are derived from synthetic data,
> for research/demo purposes, and are not clinical guidance.** Nothing here has
> been validated on real patients.

Model artifacts: `models/manifest.json` (semver 1.0.0, seed 42). Raw numbers:
[`results/bda_metrics.json`](results/bda_metrics.json) and
[`results/ai_metrics.json`](results/ai_metrics.json). Reproduce:

```bash
cd bda_engine && uv run python ../evaluation/run_bda_eval.py   # OCR, ETL, clustering, risk, bands (~4 min)
cd ai-service && uv run python ../evaluation/run_ai_eval.py     # guardrails, summaries, assistant, retrieval
```

## 1. Data and scale

| | |
|---|---|
| Synthetic patients | 50,000 (40,049 with ≥7 markers and complete PROMs used for modelling) |
| Lab reports / result rows | 67,266 reports · 500,908 raw rows from 5 labs (4 CSV, 1 JSONL) |
| PDFs | 500 in 4 layouts; 168 rendered as scanned images (blur, skew) |
| Injected noise | 4,862 label typos · 4,977 missing units · 1,430 decimal-point misreads · 2,371 duplicate rows |

## 2. ETL and data quality (Weeks 1, 3, 4)

Both engines run the same SQL and produce **identical** silver tables (asserted
row-for-row in `bda_engine/tests`).

| Engine | bronze | silver | gold | total |
|---|---|---|---|---|
| DuckDB (1 node) | 1.9 s | 5.2 s | 0.9 s | **7.9 s** |
| PySpark `local[4]` | 15.0 s | 43.0 s | 9.8 s | **67.8 s** |

At 0.5 M rows Spark is ~8× slower than DuckDB: JVM start-up and shuffle overhead
dominate at this size. Spark is kept for the horizontal-scaling path (the same
job runs on a cluster via `SPARK_MASTER`), DuckDB is the default for development
and CI (architecture decision 5).

| Injected problem | Injected | Detected / handled |
|---|---|---|
| Duplicate rows | 2,371 | 2,371 removed |
| Missing units | 4,977 | 4,997 inferred (+20 unknown-unit rows) |
| Decimal misreads (×10) | 1,430 | 1,451 flagged as decimal-misread suspects |
| Label typos | 4,862 | 4,666 mapped by fuzzy matching (**96.0 %**); 196 rows left unmapped |

Detector *counts* reconcile with injected counts; per-row precision/recall of
the decimal-misread flag was not measured (the generator does not tag which row
it corrupted), so these are consistency checks, not accuracy estimates.

## 3. OCR and table extraction (Weeks 2, 13)

Shared ingestion pipeline (`polymarker_common.pipeline`) over all 500 PDFs, 4
worker processes, 53 s wall time (0.42 s/document).

| Subset | Docs | CER | WER | Field recall | Value accuracy | Precision |
|---|---|---|---|---|---|---|
| **All** | 500 | 0.18 % | 0.79 % | 99.0 % | **97.7 %** | 98.6 % |
| Text-layer PDFs | 332 | 0.00 % | 0.00 % | 100 % | 100 % | 100 % |
| Scanned (Tesseract) | 168 | 0.55 % | 2.35 % | 97.1 % | **93.1 %** | 95.8 % |

By layout (value accuracy): colon-inline 99.7 %, pipe table 99.2 %, columns
96.2 %, boxed grid 95.6 %. Metadata: sex 99.8 %, age 100 %, lab 100 %, date
99.4 %. **Patient names never appear in extracted output (0/500).**

Of scanned values that were read wrongly, **78 %** carried a low-confidence flag
(<0.75) and are highlighted for clinician verification in the review portal; the
remaining 22 % are confidently wrong, which is why clinician sign-off (not
OCR confidence) is the control. Two parser bugs were found by the end-to-end
browser test (a flag printed between value and unit; a longer label swallowing
the value) and fixed before these numbers were measured.

Limitations: layouts are synthetic and cleaner than real faxes/phone photos;
LayoutLMv3 and PaddleOCR are wired behind flags but were not evaluated.

## 4. Clustering (Week 7)

| Model | Groups | Silhouette | Davies–Bouldin | ARI vs hidden phenotype | NMI |
|---|---|---|---|---|---|
| K-Means (selected by silhouette, k=3…9) | 9 | 0.135 | 1.56 | **0.258** | 0.303 |
| Gaussian mixture (selected by BIC) | 8 | −0.018 | 11.9 | 0.117 | 0.208 |
| DBSCAN (eps from k-distance, 8k sample) | 1 + noise | — | — | — | — |

Lab values are continuous with overlapping phenotypes, so separation is weak
(silhouette 0.14); clusters are best read as *profiles* ("Low ferritin",
"High anti-TPO", "Low free T4, high TSH" …, see `figures/cluster_profiles.png`),
not as discrete disease groups. K-Means recovers the hidden phenotypes
moderately (ARI 0.26); GMM with full covariances is worse on every metric.

DBSCAN finds one dense core and **3.7 % density outliers**. The outliers are
clinically distinct: 56 % report strong tiredness (vs 17 % in the core), and 67 %
of them are overt thyroid phenotypes (1 % of the core). Density-based outlier
detection is therefore useful as a triage signal even where partitioning is not.

## 5. Symptom risk models + SHAP (Week 8)

XGBoost per symptom, isotonic calibration on a held-out split, evaluated on a
separate 15 % test split (n = 6,008 patients).

| Target | Prevalence | AUROC | AUPRC | Brier | ECE | Logistic baseline AUROC |
|---|---|---|---|---|---|---|
| Strong tiredness (≥7/10) | 18.5 % | **0.81** | 0.59 | 0.112 | 0.012 | 0.78 |
| Frequent brain fog | 24.1 % | 0.69 | 0.48 | 0.161 | 0.012 | 0.67 |
| Noticeable hair loss | 22.1 % | 0.74 | 0.52 | 0.142 | 0.016 | 0.72 |

Figures: `roc_curves.png`, `calibration.png`, `shap_fatigue_beeswarm.png`.
Top SHAP drivers match the generator's design: tiredness → ferritin, TSH, B12;
brain fog → B12, TSH, ferritin; hair loss → ferritin, sex, TSH, zinc. The
gradient-boosted models beat the linear baseline by 0.02–0.03 AUROC, consistent
with the non-linear hinge effects and the ferritin × TSH interaction. Online
explanations use XGBoost `pred_contribs`, asserted equal to `shap.TreeExplainer`.

## 6. Functional-range discovery (Week 7) and the circularity threat (R2)

The discovered band edge (where adjusted tiredness risk rises 25 % above its
minimum) is compared with the **hidden generator threshold**
(`bda_engine/data/holdout/generator_params.json`, never read by training):

| Marker | Edge | Generator | Discovered | 90 % CI | Lab reference edge |
|---|---|---|---|---|---|
| TSH | upper | 2.5 | 2.39 | 1.90–2.50 | 4.0 |
| Free T4 | lower | 12.0 | 13.5 | 12.7–13.8 | 10.0 |
| Ferritin | lower | 45 | 55.4 | 51.4–287 | 15 |
| Vitamin D | lower | 60 | 44.2 | 42.7–56.7 | 50 |
| Vitamin B12 | lower | 260 | 226 | 208–246 | 148 |
| Magnesium | lower | 0.78 | 0.72 | 0.70–0.94 | 0.70 |

* Median relative error **12.6 %**; 5 of 6 discovered edges are narrower than
  the lab reference range, as the design intends (`figures/functional_bands_vs_truth.png`).
* The bootstrap CI contains the true threshold for only **1 of 6** markers. The
  error is systematic, not noise: the "within 25 % of minimum risk" rule places
  the edge where the smooth risk curve has *already* risen, which falls on the
  far side of a hinge whose slope is shallow (vitamin D, B12) and on the near
  side where it is steep (ferritin, free T4). The CI measures sampling
  variability only and must not be read as coverage of the true threshold.

**Validity threat R2 — circularity.** Symptoms were *generated from* marker
values with hinge functions. Recovering thresholds close to those hinges shows
the pipeline can find structure that is present; it is **not** evidence that
such thresholds exist in real patients. The functional bands, percentiles and
risk scores are demonstrations of method on synthetic data and are labelled as
such in code, API responses and the UI. A real-world claim would require
de-identified clinical data, pre-registered thresholds, and external validation.

## 7. Guardrails, summaries and GraphRAG safety (Weeks 9–10)

**Red-team set** (`cases/guardrail_cases.json`): 30 unsafe sentences
(diagnostic, prescriptive, dosage, cure, prompt injection) and 25 safe
look-alikes (lab values with units, conditional safety advice).

| Metric | Result |
|---|---|
| Unsafe recall (all categories) | **100 %** (30/30) |
| False-positive rate on safe sentences | **0 %** (0/25) — after fixing two found in the first run ("If you have chest pain…", "You have the right…") |

**Summaries over the 500 ground-truth reports** (structured input, random PROMs,
LLM disabled → deterministic template path):

| Metric | Result |
|---|---|
| Flesch–Kincaid grade | mean 4.95 · p95 5.68 · max 6.15 · **100 % ≤ 8** |
| Guardrails passed / disclaimer present / synthetic label present | 100 % / 100 % / 100 % |
| Hallucination proxy: summaries with any number not present in the inputs | **0 / 500** |
| Marker escalation recall (catalog thresholds on true values) | **100 %** |
| Latency (interpretation, excl. OCR) | 12.6 ms/report |

**Assistant cases** (`cases/assistant_cases.json`, schema kept from the original
`visible-cases.json`): **10/10 pass** — retrieval sources, no internal/draft
documents, no dosing or diagnosis, prompt-injection question, red flags (chest
pain, self-harm → emergency), critical magnesium from patient context → urgent.

**Knowledge-base retrieval** (13 queries): top-1 **100 %**, blocked-document
leaks **0** (metadata filter enforced in code; the Step 0 audit found the
internal notes returned as the *top* hit).

**Live integration** (not a metric, a check): Celery over Redis, the Redis
LangGraph checkpointer (memory survives a new agent instance) and Neo4j evidence
chains identical to the in-memory fallback — `ai-service/tests/test_integration_live.py`,
`graph_service/tests/test_graph.py::test_live_neo4j_matches_in_memory`. A
Playwright run covered patient upload → clinician sign-off → patient dashboard →
assistant against the live stack with no browser console errors.

### What is not measured

* **LLM-generated summaries.** No provider key was available in the evaluation
  environment, so every summary above came from the template. With an LLM the
  same guardrails run and unsafe drafts are regenerated then replaced by the
  template (unit-tested with scripted unsafe drafts), but readability,
  hallucination and faithfulness of real LLM drafts still need measuring with a
  key: `LLM_PROVIDER=groq GROQ_API_KEY=... uv run python ../evaluation/run_ai_eval.py`.
* The hallucination proxy only checks numbers; it cannot catch a fabricated
  qualitative claim. Template output is grounded by construction.
* Guardrail sets are small and written by the developers; an independent
  clinical red team is needed before any real-world use.

## 8. Summary against the 14-week plan

| Plan item | Evidence |
|---|---|
| 50k+ synthetic lake, schemas, Spark/DuckDB ETL | §1–2 |
| Distributed OCR + layout parsing, canonical JSON | §3 |
| LOINC + unit normalization | §2 (typo recovery 96 %), §3 (value accuracy 97.7 %) |
| Z-score / IQR / decimal-misread checks + audit | §2 |
| Neo4j knowledge graph with evidence levels | §7 live parity |
| Joint feature vectors, ratios, interactions | §5 SHAP drivers |
| DBSCAN / K-Means / GMM + functional bands | §4, §6 |
| XGBoost + SHAP risk | §5 |
| GraphRAG + deterministic guardrails | §7 |
| CER/WER, silhouette/DBI, AUROC, safety & hallucination | §3–§7 |
