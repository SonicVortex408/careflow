"""Online inference over bda_engine artifacts (cluster, bands, risk, SHAP).

Given one patient's normalized markers (SI) plus sex/age and optional PROMs:

* **bands**    - position vs laboratory reference and vs the discovered functional
                 band; population percentile and percentile within the fatigued cohort
* **cluster**  - nearest K-Means centroid (+ GMM posterior certainty), the cluster's
                 profile, and the patient's 2-D cohort-map coordinates
* **risk**     - calibrated probability per symptom target from XGBoost
* **drivers**  - top-3 SHAP contributions (TreeSHAP ``pred_contribs``) rolled up
                 from engineered features to biomarkers

Every payload carries the synthetic-data label.
"""

from __future__ import annotations

import bisect
import math
from typing import Any

import numpy as np

from app.services.model_registry import ArtifactError, ModelRegistry, get_registry
from polymarker_common.catalog import BIOMARKER_KEYS, SYNTHETIC_DATA_LABEL, load_catalog
from polymarker_common.features import aggregate_contributions, impute_row, transform_row

RISK_TARGETS = ("fatigue", "brain_fog", "hair_loss")
RISK_LABELS = {
    "fatigue": "Strong tiredness",
    "brain_fog": "Frequent brain fog",
    "hair_loss": "Noticeable hair loss",
}


def risk_level(p: float) -> str:
    if p < 0.15:
        return "low"
    if p < 0.35:
        return "moderate"
    return "high"


def _position(value: float, low: float | None, high: float | None) -> str:
    if low is not None and value < low:
        return "below"
    if high is not None and value > high:
        return "above"
    return "within"


def _percentile(value: float, quantiles: list[float], levels: list[int]) -> int:
    i = bisect.bisect_right(quantiles, value)
    if i == 0:
        return 0
    if i >= len(levels):
        return 100
    return int(levels[i - 1])


def band_positions(
    markers: dict[str, float], sex: str | None, bands_artifact: dict | None
) -> dict[str, Any]:
    catalog = load_catalog()
    out = {}
    levels = bands_artifact["percentile_levels"] if bands_artifact else None
    target = bands_artifact["target"] if bands_artifact else "fatigue"
    for key in BIOMARKER_KEYS:
        if key not in markers:
            continue
        value = float(markers[key])
        ref = catalog[key].reference_for(sex)
        entry: dict[str, Any] = {
            "key": key,
            "display": catalog[key].display,
            "value": round(value, 4),
            "unit": catalog[key].canonical_unit,
            "reference": {"low": ref.low, "high": ref.high},
            "reference_status": _position(value, ref.low, ref.high),
            "functional": None,
            "functional_status": None,
            "percentile": None,
            f"percentile_{target}_cohort": None,
        }
        band = (bands_artifact or {}).get("bands", {}).get(key)
        if band:
            f = band.get("functional")
            if f:
                low = None if f.get("lower_edge_is_data_limit") else f["low"]
                high = None if f.get("upper_edge_is_data_limit") else f["high"]
                entry["functional"] = {
                    "low": low,
                    "high": high,
                    "low_ci": f["low_ci"],
                    "high_ci": f["high_ci"],
                    "evidence_level": "synthetic_derived",
                    "verified": False,
                }
                entry["functional_status"] = _position(value, low, high)
            entry["percentile"] = _percentile(value, band["percentiles"], levels)
            cohort = band.get(f"percentiles_{target}_cohort")
            if cohort:
                entry[f"percentile_{target}_cohort"] = _percentile(value, cohort, levels)
        out[key] = entry
    return out


def _gmm_posterior(z: np.ndarray, gmm: dict) -> np.ndarray:
    logs = []
    for w, mu, cov in zip(gmm["weights"], gmm["means"], gmm["covariances"], strict=True):
        cov = np.asarray(cov)
        diff = z - np.asarray(mu)
        chol = np.linalg.cholesky(cov)
        sol = np.linalg.solve(chol, diff)
        logdet = 2 * np.sum(np.log(np.diag(chol)))
        logs.append(math.log(w) - 0.5 * (sol @ sol + logdet + len(z) * math.log(2 * math.pi)))
    logs = np.asarray(logs)
    logs -= logs.max()
    p = np.exp(logs)
    return p / p.sum()


def assign_cluster(
    values: dict[str, float], model: dict, projection: dict | None
) -> dict[str, Any]:
    raw = np.array(
        [
            math.log(max(values[k], model["eps"])) if k in model["log_markers"] else values[k]
            for k in model["features"]
        ]
    )
    z = (raw - np.asarray(model["scaler"]["mean"])) / np.asarray(model["scaler"]["std"])
    centroids = np.asarray(model["kmeans"]["centroids"])
    d = np.linalg.norm(centroids - z, axis=1)
    c = int(np.argmin(d))
    profile = model["profiles"][c]
    post = _gmm_posterior(z, model["gmm"])
    result = {
        "id": c,
        "name": profile["name"],
        "share_of_cohort": profile["share"],
        "distance": round(float(d[c]), 4),
        "gmm_certainty": round(float(post.max()), 4),
        "cohort_rates": {
            "fatigue": profile["fatigue_rate"],
            "brain_fog": profile["brain_fog_rate"],
            "hair_loss": profile["hair_loss_rate"],
        },
        "median_markers": profile["median_markers"],
    }
    if projection:
        xy = np.asarray(projection["components"]) @ z
        result["position"] = {"x": round(float(xy[0]), 3), "y": round(float(xy[1]), 3)}
    return result


def risk_scores(features: dict[str, float], registry: ModelRegistry) -> dict[str, Any]:
    import xgboost as xgb

    meta = registry.json("risk_meta")
    columns = meta["feature_columns"]
    row = np.array([[features[c] for c in columns]], dtype=float)
    dm = xgb.DMatrix(row, feature_names=columns)
    out = {}
    for t in RISK_TARGETS:
        booster = registry.booster(f"risk_{t}")
        margin = float(booster.predict(dm, output_margin=True)[0])
        raw_p = 1 / (1 + math.exp(-margin))
        cal = meta["calibration"][t]
        p = float(np.interp(raw_p, cal["x"], cal["y"])) if cal["x"] else raw_p
        contribs = booster.predict(dm, pred_contribs=True)[0]
        by_marker = aggregate_contributions(list(contribs[:-1]), columns)
        top = sorted(
            ((k, v) for k, v in by_marker.items() if k in BIOMARKER_KEYS),
            key=lambda kv: -abs(kv[1]),
        )[:3]
        catalog = load_catalog()
        out[t] = {
            "label": RISK_LABELS[t],
            "definition": meta["targets"][t],
            "probability": round(p, 4),
            "level": risk_level(p),
            "cohort_prevalence": round(meta["metrics"][t]["prevalence"], 4),
            "model_auroc": round(meta["metrics"][t]["auroc"], 4),
            "drivers": [
                {
                    "marker": k,
                    "display": catalog[k].display,
                    "contribution": round(v, 4),
                    "direction": "raises" if v > 0 else "lowers",
                }
                for k, v in top
                if abs(v) > 1e-6
            ],
        }
    return out


def run_inference(
    markers: dict[str, float],
    *,
    sex: str | None = None,
    age: float | None = None,
    proms: dict | None = None,
    registry: ModelRegistry | None = None,
) -> dict[str, Any]:
    registry = registry or get_registry()
    markers = {k: float(v) for k, v in markers.items() if k in BIOMARKER_KEYS and v is not None}
    sex = (sex or "").upper()[:1] or None
    result: dict[str, Any] = {
        "label": SYNTHETIC_DATA_LABEL,
        "models_available": registry.available,
        "inputs": {"markers_present": sorted(markers), "sex": sex, "age": age, "proms": proms},
    }
    try:
        bands = registry.json("functional_bands") if registry.available else None
    except ArtifactError:
        bands = None
    result["bands"] = band_positions(markers, sex, bands)
    if not registry.available or len(markers) < 3:
        result["cluster"] = None
        result["risk"] = None
        result["model_version"] = None
        if registry.available:
            result["note"] = "At least 3 of the 9 markers are needed for cohort analytics."
        return result

    spec = registry.json("feature_spec")
    features = transform_row(markers, sex, age, spec)
    values, _ = impute_row(markers, (sex or "F"), float(age if age is not None else 45), spec)
    result["cluster"] = assign_cluster(
        values, registry.json("cluster_model"), registry.json("cohort_projection")
    )
    result["risk"] = risk_scores(features, registry)
    result["model_version"] = {k: registry.manifest[k] for k in ("semver", "seed", "created_at")}
    result["imputed_markers"] = sorted(set(BIOMARKER_KEYS) - set(markers))
    return result
