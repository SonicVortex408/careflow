"""Multi-biomarker joint feature vectors (Week 6).

Input: gold/patient_features (one row per patient, 9 SI markers + age/sex + PROMs).
Output: a model-ready matrix with

* log transforms of the right-skewed markers (all except Mg / Zn),
* clinical ratios: FT3/FT4 (peripheral conversion), ferritin-to-TSH cross index,
  TSH x FT4 product (feedback set-point),
* interaction terms: low-iron x high-TSH, TPO x TSH, B12 x vitamin D,
* a micronutrient deficit count (markers below their reference low),
* imputation: median within sex x age band, plus ``<marker>_missing`` indicators
  so the model can learn from missingness instead of hiding it.

The same ``FeatureSpec`` is exported to the artifact manifest and re-implemented
in the ai-service inference path; ``transform_one`` is the single-row reference
used to test that parity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from polymarker_common.catalog import BIOMARKER_KEYS, load_catalog

LOG_MARKERS = ("TSH", "FT3", "FT4", "TPOAB", "VITD", "B12", "FERRITIN")
LINEAR_MARKERS = ("MG", "ZINC")
AGE_BANDS = (0, 30, 45, 60, 200)
EPS = 1e-3


def age_band(age: float) -> int:
    for i in range(len(AGE_BANDS) - 1):
        if AGE_BANDS[i] <= age < AGE_BANDS[i + 1]:
            return i
    return len(AGE_BANDS) - 2


@dataclass
class FeatureSpec:
    columns: list[str]
    impute: dict[str, dict[str, float]]  # "<sex>|<band>" -> {marker: median}
    global_median: dict[str, float]
    version: str = "1.0.0"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "columns": self.columns,
            "impute": self.impute,
            "global_median": self.global_median,
            "log_markers": list(LOG_MARKERS),
            "linear_markers": list(LINEAR_MARKERS),
            "age_bands": list(AGE_BANDS),
            "eps": EPS,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FeatureSpec:
        return cls(
            d["columns"],
            d["impute"],
            d["global_median"],
            d.get("version", "1.0.0"),
            d.get("notes", []),
        )


def fit_imputer(df: pd.DataFrame) -> tuple[dict, dict]:
    global_median = {k: float(df[k].median()) for k in BIOMARKER_KEYS}
    bands = df["age"].map(age_band)
    impute = {}
    for (sex, band), grp in df.groupby([df["sex"], bands]):
        impute[f"{sex}|{band}"] = {
            k: float(grp[k].median()) if grp[k].notna().any() else global_median[k]
            for k in BIOMARKER_KEYS
        }
    return impute, global_median


def _derived(
    values: dict[str, np.ndarray], sex_f: np.ndarray, age: np.ndarray
) -> dict[str, np.ndarray]:
    catalog = load_catalog()
    feats: dict[str, np.ndarray] = {}
    for k in LOG_MARKERS:
        feats[f"log_{k}"] = np.log(np.maximum(values[k], EPS))
    for k in LINEAR_MARKERS:
        feats[k] = values[k]
    feats["ft3_ft4_ratio"] = values["FT3"] / np.maximum(values["FT4"], EPS)
    feats["log_ferritin_to_tsh"] = feats["log_FERRITIN"] - feats["log_TSH"]
    feats["log_tsh_x_ft4"] = feats["log_TSH"] + feats["log_FT4"]
    feats["low_iron_x_high_tsh"] = (values["FERRITIN"] < 30).astype(float) * np.maximum(
        feats["log_TSH"] - math.log(2.5), 0
    )
    feats["log_tpo_x_log_tsh"] = feats["log_TPOAB"] * feats["log_TSH"]
    feats["log_b12_x_log_vitd"] = feats["log_B12"] * feats["log_VITD"]
    deficit = np.zeros_like(values["TSH"])
    for k in ("VITD", "B12", "FERRITIN", "MG", "ZINC"):
        deficit += (values[k] < catalog[k].reference.low).astype(float)
    feats["micronutrient_deficit_count"] = deficit
    feats["sex_female"] = sex_f.astype(float)
    feats["age"] = age.astype(float)
    return feats


def impute_values(
    df: pd.DataFrame, spec: FeatureSpec
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Return (imputed marker values, missing indicators) using the spec's medians."""
    bands = df["age"].map(age_band)
    keys = (df["sex"].astype(str) + "|" + bands.astype(str)).to_numpy()
    values: dict[str, np.ndarray] = {}
    missing: dict[str, np.ndarray] = {}
    for k in BIOMARKER_KEYS:
        col = df[k].to_numpy(dtype=float)
        miss = np.isnan(col)
        fill = np.array([spec.impute.get(key, spec.global_median)[k] for key in keys])
        values[k] = np.where(miss, fill, col)
        missing[f"{k}_missing"] = miss.astype(float)
    return values, missing


def build_features(
    df: pd.DataFrame, spec: FeatureSpec | None = None
) -> tuple[pd.DataFrame, FeatureSpec]:
    """Return (X, spec). Fits the imputer when ``spec`` is None."""
    df = df.reset_index(drop=True)
    fitted = spec is None
    if fitted:
        impute, global_median = fit_imputer(df)
        spec = FeatureSpec(
            columns=[],
            impute=impute,
            global_median=global_median,
            notes=["Imputation medians are derived from synthetic data."],
        )
    values, missing = impute_values(df, spec)
    feats = _derived(values, (df["sex"] == "F").to_numpy(), df["age"].to_numpy(dtype=float))
    feats.update(missing)
    X = pd.DataFrame(feats)
    if fitted:
        spec.columns = list(X.columns)
    return X[spec.columns], spec


def transform_one(
    markers: dict[str, float | None], sex: str | None, age: float | None, spec: FeatureSpec
) -> dict[str, float]:
    """Single-patient reference implementation (mirrors ai-service inference)."""
    row = {k: markers.get(k) for k in BIOMARKER_KEYS}
    df = pd.DataFrame(
        [
            {
                **{k: (np.nan if v is None else float(v)) for k, v in row.items()},
                "sex": (sex or "F").upper()[:1],
                "age": float(age if age is not None else 45),
            }
        ]
    )
    X, _ = build_features(df, spec)
    return {c: float(X.iloc[0][c]) for c in spec.columns}


def targets(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fatigue": (df["fatigue_severity"] >= 7).astype(int),
            "brain_fog": df["brain_fog_frequency"].isin(["often", "always"]).astype(int),
            "hair_loss": df["hair_loss"].isin(["moderate", "severe"]).astype(int),
        }
    )
