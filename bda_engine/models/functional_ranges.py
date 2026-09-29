"""Functional health band discovery (Week 7).

For every marker we ask: *over which values is the symptom (fatigue by default)
least likely, and where does it start to rise?*

Method A - regression threshold discovery (primary)
    Logistic regression of the symptom on a natural-spline basis of the marker
    (log scale where skewed) adjusted for age and sex. The marginal risk curve is
    evaluated on a grid over the 1st-99th percentile. The functional band is the
    contiguous region around the risk minimum where predicted risk stays within
    ``TOLERANCE`` (relative) of that minimum. Band edges are the points where
    symptom risk "statistically spikes". A bootstrap gives a CI for each edge.

Method B - cluster-based band (secondary)
    The P10-P90 range of the marker inside the K-Means cluster with the lowest
    symptom prevalence.

If the risk curve is flat (max/min < ``MIN_EFFECT``) no functional band is
reported for that marker. All output is labelled synthetic-derived.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler

from bda_engine.features.build import EPS, LOG_MARKERS
from polymarker_common.catalog import BIOMARKER_KEYS, SYNTHETIC_DATA_LABEL, load_catalog

TOLERANCE = 0.25
MIN_EFFECT = 1.3
GRID = 120
BOOTSTRAP = 20
BOOT_SAMPLE = 15_000
PERCENTILES = list(range(1, 100))


def _to_x(values: np.ndarray, key: str) -> np.ndarray:
    return np.log(np.maximum(values, EPS)) if key in LOG_MARKERS else values


def _from_x(x: np.ndarray, key: str) -> np.ndarray:
    return np.exp(x) if key in LOG_MARKERS else x


def _risk_curve(
    x: np.ndarray, age: np.ndarray, female: np.ndarray, y: np.ndarray, grid: np.ndarray
) -> np.ndarray:
    spline = SplineTransformer(n_knots=6, degree=3, extrapolation="linear")
    basis = spline.fit_transform(x.reshape(-1, 1))
    design = np.column_stack([basis, (age - 45) / 15, female])
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
    model.fit(design, y)
    gb = spline.transform(grid.reshape(-1, 1))
    # marginal risk at the cohort's mean age / sex mix
    g_design = np.column_stack(
        [gb, np.full(len(grid), (age.mean() - 45) / 15), np.full(len(grid), female.mean())]
    )
    return model.predict_proba(g_design)[:, 1]


def _band_from_curve(grid: np.ndarray, risk: np.ndarray) -> tuple[float, float, int]:
    i_min = int(np.argmin(risk))
    limit = risk[i_min] * (1 + TOLERANCE)
    lo = i_min
    while lo > 0 and risk[lo - 1] <= limit:
        lo -= 1
    hi = i_min
    while hi < len(grid) - 1 and risk[hi + 1] <= limit:
        hi += 1
    return float(grid[lo]), float(grid[hi]), i_min


def discover_bands(
    values: pd.DataFrame,
    demo: pd.DataFrame,
    y: pd.Series,
    cluster_labels: np.ndarray,
    cluster_profiles: list[dict],
    seed: int,
    target: str = "fatigue",
) -> dict:
    rng = np.random.default_rng(seed)
    catalog = load_catalog()
    age = demo["age"].to_numpy(dtype=float)
    female = (demo["sex"] == "F").to_numpy(dtype=float)
    yv = y.to_numpy()
    eligible = [p for p in cluster_profiles if p["share"] >= 0.05]
    best_cluster = min(eligible, key=lambda p: p[f"{target}_rate"])["cluster"]

    out: dict[str, dict] = {}
    for key in BIOMARKER_KEYS:
        v = values[key].to_numpy(dtype=float)
        x = _to_x(v, key)
        lo_q, hi_q = np.quantile(x, [0.01, 0.99])
        grid = np.linspace(lo_q, hi_q, GRID)
        risk = _risk_curve(x, age, female, yv, grid)
        effect = float(risk.max() / max(risk.min(), 1e-6))
        band_lo, band_hi, i_min = _band_from_curve(grid, risk)

        boots_lo, boots_hi = [], []
        for _ in range(BOOTSTRAP):
            b = rng.choice(len(x), size=min(len(x), BOOT_SAMPLE), replace=True)
            r = _risk_curve(x[b], age[b], female[b], yv[b], grid)
            bl, bh, _ = _band_from_curve(grid, r)
            boots_lo.append(bl)
            boots_hi.append(bh)

        ref = catalog[key].reference
        cluster_vals = v[cluster_labels == best_cluster]
        functional = None
        if effect >= MIN_EFFECT:
            functional = {
                "low": round(float(_from_x(np.array([band_lo]), key)[0]), 4),
                "high": round(float(_from_x(np.array([band_hi]), key)[0]), 4),
                "low_ci": [
                    round(float(_from_x(np.array([q]), key)[0]), 4)
                    for q in np.quantile(boots_lo, [0.05, 0.95])
                ],
                "high_ci": [
                    round(float(_from_x(np.array([q]), key)[0]), 4)
                    for q in np.quantile(boots_hi, [0.05, 0.95])
                ],
                "lower_edge_is_data_limit": bool(band_lo <= grid[0]),
                "upper_edge_is_data_limit": bool(band_hi >= grid[-1]),
                "method": "spline_logistic_min_risk",
                "tolerance": TOLERANCE,
                "target": target,
            }
        step = max(1, GRID // 40)
        out[key] = {
            "unit": catalog[key].canonical_unit,
            "reference": {"low": ref.low, "high": ref.high},
            "functional": functional,
            "effect_ratio": round(effect, 3),
            "min_risk_at": round(float(_from_x(np.array([grid[i_min]]), key)[0]), 4),
            "cluster_band": {
                "cluster": int(best_cluster),
                "low": round(float(np.quantile(cluster_vals, 0.10)), 4),
                "high": round(float(np.quantile(cluster_vals, 0.90)), 4),
            },
            "risk_curve": [
                {
                    "value": round(float(_from_x(np.array([g]), key)[0]), 4),
                    "risk": round(float(r), 4),
                }
                for g, r in zip(grid[::step], risk[::step], strict=True)
            ],
            "percentiles": [
                round(float(q), 4) for q in np.quantile(v, np.array(PERCENTILES) / 100)
            ],
            f"percentiles_{target}_cohort": [
                round(float(q), 4) for q in np.quantile(v[yv == 1], np.array(PERCENTILES) / 100)
            ],
        }
    return {
        "label": SYNTHETIC_DATA_LABEL,
        "target": target,
        "tolerance": TOLERANCE,
        "percentile_levels": PERCENTILES,
        "bands": out,
    }
