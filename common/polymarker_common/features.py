"""Single-row feature transform used online (ai-service inference).

This is the dependency-free twin of ``bda_engine.features.build`` (vectorised,
used for training). A parity test in bda_engine asserts both produce identical
vectors for real rows, so the model sees the same features online as offline.
"""

from __future__ import annotations

import math

from polymarker_common.catalog import BIOMARKER_KEYS, load_catalog

DEFICIT_MARKERS = ("VITD", "B12", "FERRITIN", "MG", "ZINC")


def age_band(age: float, bands: list[float]) -> int:
    for i in range(len(bands) - 1):
        if bands[i] <= age < bands[i + 1]:
            return i
    return len(bands) - 2


def impute_row(
    markers: dict[str, float | None], sex: str, age: float, spec: dict
) -> tuple[dict[str, float], dict[str, bool]]:
    key = f"{sex}|{age_band(age, spec['age_bands'])}"
    medians = spec["impute"].get(key, spec["global_median"])
    values, missing = {}, {}
    for k in BIOMARKER_KEYS:
        v = markers.get(k)
        is_missing = v is None or (isinstance(v, float) and math.isnan(v))
        values[k] = float(medians[k]) if is_missing else float(v)
        missing[k] = is_missing
    return values, missing


def transform_row(
    markers: dict[str, float | None], sex: str | None, age: float | None, spec: dict
) -> dict[str, float]:
    """``spec`` is the exported feature_spec artifact."""
    sex = (sex or "F").upper()[:1]
    age = float(age if age is not None else 45)
    eps = spec["eps"]
    values, missing = impute_row(markers, sex, age, spec)
    catalog = load_catalog()
    f: dict[str, float] = {}
    for k in spec["log_markers"]:
        f[f"log_{k}"] = math.log(max(values[k], eps))
    for k in spec["linear_markers"]:
        f[k] = values[k]
    f["ft3_ft4_ratio"] = values["FT3"] / max(values["FT4"], eps)
    f["log_ferritin_to_tsh"] = f["log_FERRITIN"] - f["log_TSH"]
    f["log_tsh_x_ft4"] = f["log_TSH"] + f["log_FT4"]
    f["low_iron_x_high_tsh"] = float(values["FERRITIN"] < 30) * max(
        f["log_TSH"] - math.log(2.5), 0.0
    )
    f["log_tpo_x_log_tsh"] = f["log_TPOAB"] * f["log_TSH"]
    f["log_b12_x_log_vitd"] = f["log_B12"] * f["log_VITD"]
    f["micronutrient_deficit_count"] = float(
        sum(values[k] < catalog[k].reference.low for k in DEFICIT_MARKERS)
    )
    f["sex_female"] = float(sex == "F")
    f["age"] = age
    for k in BIOMARKER_KEYS:
        f[f"{k}_missing"] = float(missing[k])
    return {c: f[c] for c in spec["columns"]}


def feature_to_markers(columns: list[str]) -> dict[str, list[str]]:
    """Which biomarker(s) each engineered feature is derived from (for SHAP roll-up)."""
    mapping: dict[str, list[str]] = {}
    for col in columns:
        if col == "age":
            mapping[col] = ["age"]
        elif col == "sex_female":
            mapping[col] = ["sex"]
        elif col == "ft3_ft4_ratio":
            mapping[col] = ["FT3", "FT4"]
        elif col in ("log_ferritin_to_tsh", "low_iron_x_high_tsh"):
            mapping[col] = ["FERRITIN", "TSH"]
        elif col == "log_tsh_x_ft4":
            mapping[col] = ["TSH", "FT4"]
        elif col == "log_tpo_x_log_tsh":
            mapping[col] = ["TPOAB", "TSH"]
        elif col == "log_b12_x_log_vitd":
            mapping[col] = ["B12", "VITD"]
        elif col == "micronutrient_deficit_count":
            mapping[col] = list(DEFICIT_MARKERS)
        else:
            key = col.removeprefix("log_").removesuffix("_missing")
            mapping[col] = [key] if key in BIOMARKER_KEYS else []
    return mapping


def aggregate_contributions(contribs: list[float], columns: list[str]) -> dict[str, float]:
    """Split each feature's SHAP value equally over its source markers."""
    mapping = feature_to_markers(columns)
    out = {k: 0.0 for k in (*BIOMARKER_KEYS, "age", "sex")}
    for value, col in zip(contribs, columns, strict=True):
        sources = mapping[col]
        if not sources:
            continue
        for s in sources:
            out[s] += float(value) / len(sources)
    return out
