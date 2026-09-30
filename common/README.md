# polymarker-common

Dependency-free domain code shared by `ai-service/`, `bda_engine/` and
`graph_service/` so the operational (per-upload) and analytical (batch) paths
normalise lab data identically.

| Module | Purpose |
|---|---|
| `catalog.py` + `data/biomarkers.json` | The 9 target markers: LOINC code, aliases, canonical SI unit, conversion factors, reference / plausible intervals, escalation thresholds; PROM definitions |
| `normalizer.py` | Label → LOINC mapping (exact / prefix / fuzzy, with confidence) and unit conversion to SI (inferred units are flagged) |
| `parser.py` | OCR text lines → canonical rows (label, value, unit, range, flag) + report metadata (age, sex, lab, date). Never extracts names/IDs |
| `quality.py` | Plausibility, decimal-misread, z-score and IQR outliers, duplicates, low confidence, completeness; every check is recorded for the audit trail |
| `proms.py` | Fatigue (1–10), brain fog (never…always), hair loss (none…severe) validation, encoding and binary model targets |

```bash
uv sync && uv run pytest && uv run ruff check .
```
