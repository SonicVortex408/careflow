import hashlib
import json

import numpy as np
import pandas as pd
import pytest
import xgboost as xgb

from bda_engine.features.build import FeatureSpec, build_features, transform_one
from polymarker_common.catalog import BIOMARKER_KEYS, SYNTHETIC_DATA_LABEL


def test_manifest_integrity(small_settings, trained):
    _, manifest = trained
    assert manifest["label"] == SYNTHETIC_DATA_LABEL
    expected = {
        "feature_spec",
        "cluster_model",
        "cohort_projection",
        "functional_bands",
        "population_stats",
        "correlations",
        "risk_fatigue",
        "risk_brain_fog",
        "risk_hair_loss",
        "risk_meta",
        "training_report",
    }
    assert expected <= set(manifest["artifacts"])
    for name, entry in manifest["artifacts"].items():
        path = small_settings.artifact_dir / entry["path"]
        assert path.name.startswith(f"{name}_{manifest['semver']}_s{manifest['seed']}")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


def test_feature_ratios_and_single_row_parity(small_settings, trained):
    gold = pd.read_parquet(small_settings.lake_dir / "gold" / "patient_features").head(50)
    X, spec = build_features(gold)
    spec2 = FeatureSpec.from_dict(json.loads(json.dumps(spec.to_dict())))
    row = gold.iloc[3]
    one = transform_one(
        {k: (None if pd.isna(row[k]) else row[k]) for k in BIOMARKER_KEYS},
        row["sex"],
        row["age"],
        spec2,
    )
    np.testing.assert_allclose([one[c] for c in spec.columns], X.iloc[3].to_numpy(), rtol=1e-9)
    if not pd.isna(row["FT3"]) and not pd.isna(row["FT4"]):
        assert one["ft3_ft4_ratio"] == pytest.approx(row["FT3"] / row["FT4"])


def test_risk_models_beat_chance_and_are_calibrated(trained):
    report, _ = trained
    for target, m in report["risk"].items():
        assert m["auroc"] > 0.6, target
        assert m["ece_calibrated"] < 0.08, target


def test_pred_contribs_match_shap_tree_explainer(small_settings, trained):
    import shap

    _, manifest = trained
    booster = xgb.Booster()
    booster.load_model(
        str(small_settings.artifact_dir / manifest["artifacts"]["risk_fatigue"]["path"])
    )
    gold = pd.read_parquet(small_settings.lake_dir / "gold" / "patient_features").head(40)
    spec = FeatureSpec.from_dict(
        json.loads(
            (
                small_settings.artifact_dir / manifest["artifacts"]["feature_spec"]["path"]
            ).read_text()
        )
    )
    X, _ = build_features(gold, spec)
    contribs = booster.predict(xgb.DMatrix(X), pred_contribs=True)
    sv = shap.TreeExplainer(booster).shap_values(X)
    np.testing.assert_allclose(contribs[:, :-1], sv, atol=1e-4)
    # contributions + bias reproduce the margin
    margin = booster.predict(xgb.DMatrix(X), output_margin=True)
    np.testing.assert_allclose(contribs.sum(axis=1), margin, atol=1e-4)


def test_functional_bands_cover_all_markers(small_settings, trained):
    _, manifest = trained
    bands = json.loads(
        (
            small_settings.artifact_dir / manifest["artifacts"]["functional_bands"]["path"]
        ).read_text()
    )
    assert bands["label"] == SYNTHETIC_DATA_LABEL
    assert set(bands["bands"]) == set(BIOMARKER_KEYS)
    for b in bands["bands"].values():
        assert len(b["percentiles"]) == 99
        if b["functional"]:
            assert b["functional"]["low"] < b["functional"]["high"]


def test_cluster_model_is_exportable(small_settings, trained):
    _, manifest = trained
    model = json.loads(
        (small_settings.artifact_dir / manifest["artifacts"]["cluster_model"]["path"]).read_text()
    )
    k = len(model["kmeans"]["centroids"])
    assert len(model["profiles"]) == k
    assert all(len(c) == len(BIOMARKER_KEYS) for c in model["kmeans"]["centroids"])


def test_online_single_row_transform_matches_training_features(small_settings, trained):
    """ai-service uses polymarker_common.features.transform_row; training uses build_features."""
    from polymarker_common.features import transform_row

    _, manifest = trained
    spec = json.loads(
        (small_settings.artifact_dir / manifest["artifacts"]["feature_spec"]["path"]).read_text()
    )
    gold = pd.read_parquet(small_settings.lake_dir / "gold" / "patient_features").head(200)
    X, _ = build_features(gold, FeatureSpec.from_dict(spec))
    for i in range(len(gold)):
        row = gold.iloc[i]
        markers = {k: (None if pd.isna(row[k]) else float(row[k])) for k in BIOMARKER_KEYS}
        online = transform_row(markers, row["sex"], float(row["age"]), spec)
        np.testing.assert_allclose(
            [online[c] for c in spec["columns"]], X.iloc[i].to_numpy(), rtol=1e-9, atol=1e-12
        )
