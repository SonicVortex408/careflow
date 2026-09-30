"""bda_engine command line.

uv run bda generate          # synthetic raw zone (50k patients, ~500 PDFs)
uv run bda etl               # raw -> bronze -> silver -> gold (ETL_ENGINE=spark|duckdb)
uv run bda ocr               # distributed OCR of raw/pdf into lake/extracted
uv run bda train             # features, clustering, functional bands, risk models, artifacts
uv run bda all               # everything above
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from dataclasses import replace

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from bda_engine.config import Settings, get_settings
from bda_engine.features.build import build_features, impute_values, targets
from bda_engine.models.clustering import fit_clusters
from bda_engine.models.export import ArtifactWriter
from bda_engine.models.functional_ranges import discover_bands
from bda_engine.models.risk import TARGETS, train_risk_models
from polymarker_common.catalog import BIOMARKER_KEYS, SYNTHETIC_DATA_LABEL
from polymarker_common.proms import BRAIN_FOG_LEVELS, HAIR_LOSS_LEVELS
from polymarker_common.proms import TARGETS as TARGET_DEFS

logger = logging.getLogger("bda_engine")
MIN_MARKERS = 7


def load_training_frame(s: Settings) -> pd.DataFrame:
    gold = pd.read_parquet(s.lake_dir / "gold" / "patient_features")
    observed = gold[list(BIOMARKER_KEYS)].notna().sum(axis=1)
    keep = (
        (observed >= MIN_MARKERS)
        & gold["fatigue_severity"].notna()
        & gold["brain_fog_frequency"].notna()
        & gold["hair_loss"].notna()
    )
    df = gold[keep].sort_values("patient_id").reset_index(drop=True)
    logger.info(
        "training frame: %d of %d patients (>= %d markers and complete PROMs)",
        len(df),
        len(gold),
        MIN_MARKERS,
    )
    return df


def _correlations(df: pd.DataFrame) -> dict:
    scores = pd.DataFrame(
        {
            "fatigue": df["fatigue_severity"].astype(float),
            "brain_fog": df["brain_fog_frequency"].map(BRAIN_FOG_LEVELS.index).astype(float),
            "hair_loss": df["hair_loss"].map(HAIR_LOSS_LEVELS.index).astype(float),
        }
    )
    edges, matrix = [], {}
    for k in BIOMARKER_KEYS:
        mask = df[k].notna()
        matrix[k] = {}
        for sym in scores.columns:
            rho = float(spearmanr(df.loc[mask, k], scores.loc[mask, sym]).statistic)
            matrix[k][sym] = round(rho, 4)
            if abs(rho) >= 0.1:
                edges.append(
                    {
                        "from": k,
                        "to": sym,
                        "rho": round(rho, 4),
                        "direction": "positive" if rho > 0 else "inverse",
                    }
                )
    marker_matrix = df[list(BIOMARKER_KEYS)].corr(method="spearman").round(4)
    return {
        "method": "spearman",
        "marker_symptom": matrix,
        "edges": edges,
        "marker_marker": marker_matrix.to_dict(),
    }


def train(s: Settings) -> dict:
    t0 = time.perf_counter()
    df = load_training_frame(s)
    X, spec = build_features(df)
    Y = targets(df)
    values_arr, _ = impute_values(df, spec)
    values = pd.DataFrame(values_arr)
    symptoms = Y.assign(fatigue_severity=df["fatigue_severity"].astype(float))

    clusters = fit_clusters(values, symptoms, s.seed)
    bands = discover_bands(
        values,
        df[["age", "sex"]],
        Y["fatigue"],
        clusters["labels"],
        clusters["model"]["profiles"],
        s.seed,
    )
    risk = train_risk_models(X, Y, s.seed)
    correlations = _correlations(df)
    pop_stats = json.loads(
        (s.lake_dir / "audit" / "population_stats.json").read_text(encoding="utf-8")
    )

    w = ArtifactWriter(s.artifact_dir, s.model_semver, s.seed)
    w.write_json("feature_spec", spec.to_dict())
    w.write_json("cluster_model", clusters["model"])
    w.write_json("cohort_projection", clusters["projection"])
    w.write_json("functional_bands", bands)
    w.write_json("population_stats", {"stats": pop_stats})
    w.write_json("correlations", correlations)
    for t in TARGETS:
        w.write_booster(f"risk_{t}", risk[t]["booster"])
    w.write_json(
        "risk_meta",
        {
            "targets": {t: TARGET_DEFS[t] for t in TARGETS},
            "feature_columns": list(X.columns),
            "calibration": {t: risk[t]["calibration"] for t in TARGETS},
            "metrics": {t: risk[t]["metrics"] for t in TARGETS},
            "global_importance": {t: risk[t]["global_importance"] for t in TARGETS},
        },
    )
    training_report = {
        "patients": len(df),
        "clustering": clusters["metrics"],
        "risk": {
            t: {k: v for k, v in risk[t]["metrics"].items() if k != "calibration_curve"}
            for t in TARGETS
        },
        "functional_bands": {
            k: (v["functional"] | {"effect_ratio": v["effect_ratio"]}) if v["functional"] else None
            for k, v in bands["bands"].items()
        },
        "seconds": round(time.perf_counter() - t0, 1),
    }
    w.write_json("training_report", training_report)
    fingerprint = hashlib.sha256(
        pd.util.hash_pandas_object(
            df[["patient_id", *BIOMARKER_KEYS]], index=False
        ).values.tobytes()
    ).hexdigest()[:16]
    w.write_manifest(
        {
            "data": {
                "fingerprint": fingerprint,
                "patients": len(df),
                "synthetic": True,
                "note": SYNTHETIC_DATA_LABEL,
            },
            "summary": {
                "kmeans_k": clusters["metrics"]["kmeans"]["k"],
                "kmeans_silhouette": round(clusters["metrics"]["kmeans"]["silhouette"], 4),
                "auroc": {t: round(risk[t]["metrics"]["auroc"], 4) for t in TARGETS},
            },
        }
    )

    # Evaluation-only side outputs (not artifacts): cluster assignments + test indices.
    eval_dir = s.data_dir / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "patient_id": df["patient_id"],
            "kmeans": clusters["labels"],
            "gmm": clusters["gmm_labels"],
        }
    ).to_parquet(eval_dir / "cluster_assignments.parquet", index=False)
    np.savez(eval_dir / "risk_test_index.npz", **{t: risk[t]["test_index"] for t in TARGETS})
    dbs = clusters["dbscan_sample"]
    pd.DataFrame(
        {"patient_id": df["patient_id"].iloc[dbs["index"]].to_numpy(), "dbscan": dbs["labels"]}
    ).to_parquet(eval_dir / "dbscan_sample.parquet", index=False)
    return training_report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="PolyMarker bda_engine")
    parser.add_argument("command", choices=["generate", "etl", "ocr", "train", "all"])
    parser.add_argument("--engine", choices=["spark", "duckdb"], default=None)
    parser.add_argument("--patients", type=int, default=None)
    parser.add_argument("--pdfs", type=int, default=None)
    args = parser.parse_args()
    s = get_settings()
    if args.engine:
        s = replace(s, etl_engine=args.engine)
    if args.patients:
        s = replace(s, n_patients=args.patients)
    if args.pdfs is not None:
        s = replace(s, n_pdfs=args.pdfs)

    out = {}
    if args.command in ("generate", "all"):
        from bda_engine.scripts.generate_synthetic_data import generate

        out["generate"] = generate(s.n_patients, s.n_pdfs, s.seed, s.data_dir)
    if args.command in ("etl", "all"):
        from bda_engine.etl.engine import get_engine
        from bda_engine.etl.lake import run_etl

        engine = get_engine(s.etl_engine, s.spark_master)
        try:
            out["etl"] = run_etl(engine, s)
        finally:
            engine.close()
    if args.command in ("ocr", "all") and s.n_pdfs:
        from bda_engine.etl.ocr_batch import run_ocr_batch

        out["ocr"] = run_ocr_batch(s)
    if args.command in ("train", "all"):
        out["train"] = train(s)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
