"""Symptom correlation & risk stratification (Week 8).

One XGBoost classifier per symptom target (fatigue >= 7, brain fog often/always,
hair loss moderate/severe) on the joint multi-biomarker feature vector.

* Patient-level split: 70% train / 15% calibration / 15% test (stratified).
* Early stopping on the calibration split; isotonic calibration fitted on it and
  exported as interpolation knots, so the online path needs only numpy.
* Explanations: exact TreeSHAP contributions from ``pred_contribs=True``
  (identical to ``shap.TreeExplainer`` on the margin; asserted in tests).
  Feature-level contributions are aggregated to the nine markers for display.
* Baseline: L2 logistic regression on the same features.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from polymarker_common.features import aggregate_contributions

TARGETS = ("fatigue", "brain_fog", "hair_loss")
XGB_PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "reg_lambda": 1.0,
    "tree_method": "hist",
}


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        m = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if m.any():
            ece += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(ece)


def calibration_curve(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    out = []
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        m = (p >= lo) & (p <= hi)
        if m.any():
            out.append(
                {
                    "mean_predicted": float(p[m].mean()),
                    "observed": float(y[m].mean()),
                    "n": int(m.sum()),
                }
            )
    return out


def train_risk_models(X: pd.DataFrame, Y: pd.DataFrame, seed: int) -> dict:
    idx = np.arange(len(X))
    results: dict[str, dict] = {}
    for target in TARGETS:
        y = Y[target].to_numpy()
        tr, rest = train_test_split(idx, test_size=0.30, stratify=y, random_state=seed)
        ca, te = train_test_split(rest, test_size=0.50, stratify=y[rest], random_state=seed)
        dtr = xgb.DMatrix(X.iloc[tr], label=y[tr])
        dca = xgb.DMatrix(X.iloc[ca], label=y[ca])
        dte = xgb.DMatrix(X.iloc[te], label=y[te])
        booster = xgb.train(
            XGB_PARAMS | {"seed": seed},
            dtr,
            num_boost_round=1500,
            evals=[(dca, "calibration")],
            early_stopping_rounds=50,
            verbose_eval=False,
        )
        it = (0, booster.best_iteration + 1)
        p_ca = booster.predict(dca, iteration_range=it)
        p_te = booster.predict(dte, iteration_range=it)
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(p_ca, y[ca])
        p_te_cal = iso.predict(p_te)

        lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)).fit(
            X.iloc[tr], y[tr]
        )
        p_lr = lr.predict_proba(X.iloc[te])[:, 1]

        contribs = booster.predict(dte, pred_contribs=True, iteration_range=it)
        feat_imp = np.abs(contribs[:, :-1]).mean(axis=0)
        marker_imp = aggregate_contributions(feat_imp, list(X.columns))

        # Trim the booster to the early-stopped rounds for export.
        final = booster[: booster.best_iteration + 1]
        results[target] = {
            "booster": final,
            "calibration": {
                "x": [float(v) for v in iso.X_thresholds_],
                "y": [float(v) for v in iso.y_thresholds_],
            },
            "metrics": {
                "n_train": int(len(tr)),
                "n_calibration": int(len(ca)),
                "n_test": int(len(te)),
                "prevalence": float(y.mean()),
                "best_iteration": int(booster.best_iteration),
                "auroc": float(roc_auc_score(y[te], p_te)),
                "auprc": float(average_precision_score(y[te], p_te)),
                "brier_raw": float(brier_score_loss(y[te], p_te)),
                "brier_calibrated": float(brier_score_loss(y[te], p_te_cal)),
                "ece_raw": expected_calibration_error(y[te], p_te),
                "ece_calibrated": expected_calibration_error(y[te], p_te_cal),
                "baseline_logistic_auroc": float(roc_auc_score(y[te], p_lr)),
                "calibration_curve": calibration_curve(y[te], p_te_cal),
            },
            "global_importance": {
                "features": {
                    c: float(v)
                    for c, v in sorted(zip(X.columns, feat_imp, strict=True), key=lambda kv: -kv[1])
                },
                "markers": dict(sorted(marker_imp.items(), key=lambda kv: -kv[1])),
            },
            "test_index": te,
        }
    return results
