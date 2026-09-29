"""Cohort analytics endpoints (all payloads carry the synthetic-data label).

POST /api/inference          cluster, band positions, calibrated risk, SHAP top-3
GET  /api/inference/cohort   2-D cohort map sample + cluster profiles
GET  /api/inference/bands    functional bands + risk curves for the gauges
GET  /api/inference/catalog  biomarker catalog + PROM definitions
GET  /api/inference/model    artifact manifest status + evaluation metrics
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import require_internal_key
from app.services.inference import run_inference
from app.services.model_registry import get_registry
from polymarker_common.catalog import SYNTHETIC_DATA_LABEL, catalog_as_dict, prom_spec

router = APIRouter(
    prefix="/api/inference", tags=["inference"], dependencies=[Depends(require_internal_key)]
)


class InferenceRequest(BaseModel):
    markers: dict[str, float]
    sex: str | None = None
    age: float | None = None
    proms: dict | None = None


@router.post("")
def inference(req: InferenceRequest):
    return run_inference(req.markers, sex=req.sex, age=req.age, proms=req.proms)


def _require_models():
    registry = get_registry()
    if not registry.available:
        raise HTTPException(status_code=503, detail="Model artifacts not available")
    return registry


@router.get("/cohort")
def cohort():
    r = _require_models()
    model = r.json("cluster_model")
    projection = r.json("cohort_projection")
    return {
        "label": SYNTHETIC_DATA_LABEL,
        "points": projection["points"],
        "explained_variance_ratio": projection["explained_variance_ratio"],
        "profiles": model["profiles"],
    }


@router.get("/bands")
def bands():
    r = _require_models()
    return r.json("functional_bands")


@router.get("/catalog")
def catalog():
    return {"biomarkers": catalog_as_dict(), "proms": prom_spec(), "label": SYNTHETIC_DATA_LABEL}


@router.get("/model")
def model_status():
    r = get_registry()
    status = r.status()
    if r.available:
        meta = r.json("risk_meta")
        report = r.json("training_report")
        status["metrics"] = {
            "risk": {
                t: {
                    k: m[k]
                    for k in ("auroc", "auprc", "brier_calibrated", "ece_calibrated", "prevalence")
                }
                for t, m in meta["metrics"].items()
            },
            "clustering": {
                "kmeans_k": report["clustering"]["kmeans"]["k"],
                "kmeans_silhouette": report["clustering"]["kmeans"]["silhouette"],
                "kmeans_davies_bouldin": report["clustering"]["kmeans"]["davies_bouldin"],
                "gmm_components": report["clustering"]["gmm"]["components"],
                "dbscan_noise_fraction": report["clustering"]["dbscan"]["noise_fraction"],
            },
            "global_importance": {t: v["markers"] for t, v in meta["global_importance"].items()},
        }
    return status
