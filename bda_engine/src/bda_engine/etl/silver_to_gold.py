"""
Week 3, Step 3.5: uniform feature vectors.

Pivots biomarker_observations (one row per patient x biomarker x
panel) into gold/patient_feature_vectors/ (one row per patient x
panel_date), with:
  - a FIXED column order (the 9 biomarkers in BiomarkerKey enum order,
    always the same regardless of which markers a given panel
    happened to include) -- a model consuming this can rely on
    column position, not on which markers happened to be present.
  - an explicit <marker>_missing indicator per biomarker, rather than
    a silently-imputed value -- imputation is a modeling decision and
    belongs in a later feature-engineering step (Phase 4), never here.
  - a <marker>_zscore against the cohort mean/std computed from this
    same dataset (documented as such -- it is a synthetic-cohort
    z-score, not a clinically validated one).

Only rows with quality_status == "ok" are pivoted in -- a REJECTED or
SUSPECT observation must never silently enter a feature vector (see
app/services/data_quality.py's docstring on the ai-service side, which
states the same policy for the mirror-image reason).
"""

import pandas as pd

from bda_engine.schemas.common import BiomarkerKey

BIOMARKER_ORDER = [k.value for k in BiomarkerKey]


def pivot_to_feature_vectors(observations: pd.DataFrame) -> pd.DataFrame:
    """observations: a biomarker_observations-shaped DataFrame (as
    produced by generate_synthetic_data.py or, eventually, the
    ai-service worker pipeline). Must have columns: patient_id,
    biomarker_key, value_canonical, observed_month, quality_status."""

    required = {
        "patient_id", "biomarker_key", "value_canonical",
        "observed_month", "quality_status",
    }
    missing_cols = required - set(observations.columns)
    if missing_cols:
        raise ValueError(f"observations is missing required columns: {missing_cols}")

    ok = observations[observations["quality_status"] == "ok"].copy()

    # Cohort mean/std per biomarker, computed once over all OK rows in
    # this dataset -- NOT per panel_date, so a single early panel
    # doesn't get a degenerate zero-variance z-score.
    stats = ok.groupby("biomarker_key")["value_canonical"].agg(["mean", "std"]).to_dict("index")

    panels = ok[["patient_id", "observed_month"]].drop_duplicates()

    rows = []
    for _, panel in panels.iterrows():
        patient_id, observed_month = panel["patient_id"], panel["observed_month"]
        panel_obs = ok[
            (ok["patient_id"] == patient_id) & (ok["observed_month"] == observed_month)
        ]
        values_by_key = dict(zip(
            panel_obs["biomarker_key"], panel_obs["value_canonical"], strict=False,
        ))

        row = {"patient_id": patient_id, "observed_month": observed_month}
        for key in BIOMARKER_ORDER:
            value = values_by_key.get(key)
            row[f"{key}_value"] = value
            row[f"{key}_missing"] = value is None

            if value is None or key not in stats:
                row[f"{key}_zscore"] = None
            else:
                mean, std = stats[key]["mean"], stats[key]["std"]
                row[f"{key}_zscore"] = float((value - mean) / std) if std and std > 0 else 0.0

        rows.append(row)

    result = pd.DataFrame(rows)

    # Fixed column order: patient_id, observed_month, then each
    # biomarker's (value, missing, zscore) triple in BIOMARKER_ORDER.
    ordered_cols = ["patient_id", "observed_month"]
    for key in BIOMARKER_ORDER:
        ordered_cols += [f"{key}_value", f"{key}_missing", f"{key}_zscore"]

    return result[ordered_cols] if not result.empty else pd.DataFrame(columns=ordered_cols)


def write_feature_vectors(observations: pd.DataFrame, out_path) -> pd.DataFrame:
    from pathlib import Path

    out_path = Path(out_path)
    feature_df = pivot_to_feature_vectors(observations)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_parquet(out_path, index=False)
    return feature_df
