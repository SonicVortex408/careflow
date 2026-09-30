"""Week 13 evaluation - data, OCR and ML metrics.

    cd bda_engine && uv run python ../evaluation/run_bda_eval.py

Reads the bda_engine lake + holdout (generator ground truth) and the model
artifacts; writes evaluation/results/bda_metrics.json and evaluation/figures/*.png.
The holdout is read ONLY here, never by ETL or training.
"""

from __future__ import annotations

import json
import os
import re
import time
from multiprocessing import Pool
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xgboost as xgb  # noqa: E402
from rapidfuzz.distance import Levenshtein  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    adjusted_rand_score,
    average_precision_score,
    brier_score_loss,
    normalized_mutual_info_score,
    roc_auc_score,
    roc_curve,
)

from bda_engine.config import get_settings  # noqa: E402
from bda_engine.features.build import FeatureSpec, build_features, targets  # noqa: E402
from bda_engine.models.risk import calibration_curve, expected_calibration_error  # noqa: E402
from bda_engine.pipeline import load_training_frame  # noqa: E402
from polymarker_common.catalog import BIOMARKER_KEYS, SYNTHETIC_DATA_LABEL, load_catalog  # noqa: E402

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
RES = HERE / "results"
FIG.mkdir(exist_ok=True)
RES.mkdir(exist_ok=True)

BLUE, ORANGE, GREY, INK = "#2a78d6", "#eb6834", "#c3c2b7", "#0b0b0b"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "figure.dpi": 150})


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _ocr_one(args):
    from polymarker_common.ocr import extract_text
    from polymarker_common.pipeline import ingest_lines

    path, truth = args
    t0 = time.perf_counter()
    ocr = extract_text(path)
    out = ingest_lines(ocr.lines, ocr.line_confidences, ocr_method=ocr.method)
    hyp, ref = _norm(ocr.text), _norm(truth["expected_text"])
    got = {b["key"]: b for b in out["biomarkers"]}
    fields = []
    for r in truth["rows"]:
        b = got.get(r["key"])
        fields.append({
            "key": r["key"],
            "found": b is not None,
            "value_ok": b is not None and abs(b["value"] - r["value_si"]) <= 0.01 * abs(r["value_si"]) + 1e-6,
            "low_confidence": b is not None and b["confidence"] < 0.75,
        })
    spurious = [k for k in got if k not in {r["key"] for r in truth["rows"]}]
    return {
        "report_id": truth["report_id"], "template": truth["template"], "scanned": truth["scanned"],
        "method": ocr.method, "seconds": time.perf_counter() - t0,
        "cer": Levenshtein.distance(hyp, ref) / max(1, len(ref)),
        "wer": Levenshtein.distance(hyp.split(), ref.split()) / max(1, len(ref.split())),
        "fields": fields, "spurious": spurious,
        "meta_ok": {
            "sex": out["metadata"]["sex"] == truth["sex"],
            "age": out["metadata"]["age"] == truth["age"],
            "lab": (out["metadata"]["lab_provider"] or "").strip() == truth["lab_provider"],
            "date": out["metadata"]["collected_at"] == truth["collected_at"],
        },
        "name_leak": any(tok in json.dumps(out) for tok in truth["expected_text"].split("\n")[1].split("Age")[0].replace("Patient:", "").split()),
    }


def eval_ocr(s) -> dict:
    truth = [json.loads(line) for line in open(s.holdout_dir / "pdf_ground_truth.jsonl", encoding="utf-8")]
    jobs = [(str(s.raw_dir / "pdf" / t["file"]), t) for t in truth]
    os.environ["OMP_THREAD_LIMIT"] = "1"
    t0 = time.perf_counter()
    with Pool(os.cpu_count() or 2) as pool:
        docs = pool.map(_ocr_one, jobs, chunksize=4)
    elapsed = time.perf_counter() - t0

    def summarize(subset):
        fields = [f for d in subset for f in d["fields"]]
        n_found = sum(f["found"] for f in fields)
        n_ok = sum(f["value_ok"] for f in fields)
        spurious = sum(len(d["spurious"]) for d in subset)
        return {
            "documents": len(subset),
            "cer_mean": round(float(np.mean([d["cer"] for d in subset])), 4),
            "wer_mean": round(float(np.mean([d["wer"] for d in subset])), 4),
            "field_recall": round(n_found / max(1, len(fields)), 4),
            "field_value_accuracy": round(n_ok / max(1, len(fields)), 4),
            "field_precision": round(n_ok / max(1, n_found + spurious), 4),
            "wrong_values_flagged_low_confidence": round(
                sum(f["low_confidence"] for f in fields if f["found"] and not f["value_ok"])
                / max(1, sum(1 for f in fields if f["found"] and not f["value_ok"])), 4),
            "seconds_per_doc": round(float(np.mean([d["seconds"] for d in subset])), 3),
        }

    result = {"overall": summarize(docs), "text_layer": summarize([d for d in docs if not d["scanned"]]),
              "scanned": summarize([d for d in docs if d["scanned"]]),
              "by_template": {t: summarize([d for d in docs if d["template"] == t]) for t in sorted({d["template"] for d in docs})},
              "metadata_accuracy": {k: round(float(np.mean([d["meta_ok"][k] for d in docs])), 4) for k in ("sex", "age", "lab", "date")},
              "patient_name_leaks": int(sum(d["name_leak"] for d in docs)),
              "wall_seconds": round(elapsed, 1), "workers": os.cpu_count()}
    per_marker = {}
    for k in BIOMARKER_KEYS:
        fs = [f for d in docs for f in d["fields"] if f["key"] == k]
        per_marker[k] = round(sum(f["value_ok"] for f in fs) / max(1, len(fs)), 4)
    result["value_accuracy_by_marker"] = per_marker
    return result


def eval_clustering(s, manifest, df) -> dict:
    latent = pd.read_parquet(s.holdout_dir / "latent.parquet")[["patient_id", "phenotype"]]
    assign = pd.read_parquet(s.data_dir / "evaluation" / "cluster_assignments.parquet").merge(latent, on="patient_id")
    dbs = pd.read_parquet(s.data_dir / "evaluation" / "dbscan_sample.parquet").merge(latent, on="patient_id")
    report = json.loads((s.artifact_dir / manifest["artifacts"]["training_report"]["path"]).read_text())["clustering"]
    out = {
        "kmeans": {k: report["kmeans"][k] for k in ("k", "silhouette", "davies_bouldin", "calinski_harabasz")}
        | {"ari_vs_latent_phenotype": adjusted_rand_score(assign["phenotype"], assign["kmeans"]),
           "nmi_vs_latent_phenotype": normalized_mutual_info_score(assign["phenotype"], assign["kmeans"])},
        "gmm": {k: report["gmm"][k] for k in ("components", "silhouette", "davies_bouldin")}
        | {"ari_vs_latent_phenotype": adjusted_rand_score(assign["phenotype"], assign["gmm"]),
           "nmi_vs_latent_phenotype": normalized_mutual_info_score(assign["phenotype"], assign["gmm"])},
        "dbscan": {k: report["dbscan"][k] for k in ("eps", "min_samples", "n_clusters", "noise_fraction",
                                                   "noise_fatigue_rate", "core_fatigue_rate")},
        "kmeans_selection": report["kmeans"]["selection"],
    }
    # noise points vs phenotype
    noise = dbs[dbs["dbscan"] == -1]
    out["dbscan"]["noise_phenotype_mix"] = noise["phenotype"].value_counts(normalize=True).round(3).to_dict()
    out["dbscan"]["core_phenotype_mix"] = dbs[dbs["dbscan"] != -1]["phenotype"].value_counts(normalize=True).round(3).to_dict()
    ct = pd.crosstab(assign["kmeans"], assign["phenotype"], normalize="index").round(3)
    out["kmeans_vs_phenotype"] = ct.to_dict(orient="index")

    model = json.loads((s.artifact_dir / manifest["artifacts"]["cluster_model"]["path"]).read_text())
    z = np.array([[p["z_median"][k] for k in BIOMARKER_KEYS] for p in model["profiles"]])
    names = [f"{p['name']} ({round(p['fatigue_rate'] * 100)}% tired)" for p in model["profiles"]]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    lim = np.abs(z).max()
    im = ax.imshow(z, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(len(BIOMARKER_KEYS)), [load_catalog()[k].display for k in BIOMARKER_KEYS], rotation=35, ha="right")
    ax.set_yticks(range(len(names)), names)
    fig.colorbar(im, ax=ax, label="median z vs cohort")
    ax.set_title("K-Means cluster profiles (synthetic cohort)")
    fig.tight_layout()
    fig.savefig(FIG / "cluster_profiles.png")
    plt.close(fig)

    sel = pd.DataFrame(report["kmeans"]["selection"])
    fig, ax = plt.subplots(figsize=(4.5, 3))
    ax.plot(sel["k"], sel["silhouette"], color=BLUE, lw=2, marker="o", ms=5)
    ax.set_xlabel("k")
    ax.set_ylabel("silhouette")
    ax.set_title("K-Means model selection")
    fig.tight_layout()
    fig.savefig(FIG / "kmeans_selection.png")
    plt.close(fig)
    return out


def eval_risk(s, manifest, df) -> dict:
    spec = FeatureSpec.from_dict(json.loads((s.artifact_dir / manifest["artifacts"]["feature_spec"]["path"]).read_text()))
    meta = json.loads((s.artifact_dir / manifest["artifacts"]["risk_meta"]["path"]).read_text())
    X, _ = build_features(df, spec)
    Y = targets(df)
    idx = np.load(s.data_dir / "evaluation" / "risk_test_index.npz")
    out = {}
    fig_roc, ax_roc = plt.subplots(figsize=(4.2, 3.6))
    fig_cal, ax_cal = plt.subplots(figsize=(4.2, 3.6))
    colors = {"fatigue": BLUE, "brain_fog": ORANGE, "hair_loss": "#1baf7a"}
    labels = {"fatigue": "Strong tiredness", "brain_fog": "Frequent brain fog", "hair_loss": "Noticeable hair loss"}
    for t in ("fatigue", "brain_fog", "hair_loss"):
        te = idx[t]
        booster = xgb.Booster()
        booster.load_model(str(s.artifact_dir / manifest["artifacts"][f"risk_{t}"]["path"]))
        dm = xgb.DMatrix(X.iloc[te])
        p_raw = booster.predict(dm)
        cal = meta["calibration"][t]
        p = np.interp(p_raw, cal["x"], cal["y"])
        y = Y[t].to_numpy()[te]
        # labs-only ablation (drop age/sex contributions) is approximated by the marker share of |SHAP|
        contribs = booster.predict(dm, pred_contribs=True)[:, :-1]
        cols = list(X.columns)
        demo_share = float(np.abs(contribs[:, [cols.index("age"), cols.index("sex_female")]]).sum() / np.abs(contribs).sum())
        out[t] = {
            "auroc": roc_auc_score(y, p_raw), "auprc": average_precision_score(y, p_raw),
            "brier": brier_score_loss(y, p), "ece": expected_calibration_error(y, p),
            "baseline_logistic_auroc": meta["metrics"][t]["baseline_logistic_auroc"],
            "prevalence": float(y.mean()), "n_test": int(len(te)),
            "demographic_share_of_abs_shap": round(demo_share, 4),
            "top_markers_by_mean_abs_shap": list(meta["global_importance"][t]["markers"])[:4],
        }
        fpr, tpr, _ = roc_curve(y, p_raw)
        ax_roc.plot(fpr, tpr, lw=2, color=colors[t], label=f"{labels[t]} (AUROC {out[t]['auroc']:.2f})")
        curve = calibration_curve(y, p)
        ax_cal.plot([c["mean_predicted"] for c in curve], [c["observed"] for c in curve], lw=2, marker="o", ms=4,
                    color=colors[t], label=f"{labels[t]} (ECE {out[t]['ece']:.3f})")
    for ax, title, xl, yl in ((ax_roc, "ROC (held-out test split)", "False positive rate", "True positive rate"),
                              (ax_cal, "Calibration (isotonic)", "Mean predicted probability", "Observed rate")):
        ax.plot([0, 1], [0, 1], color=GREY, lw=1, ls="--")
        ax.set_title(title)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.legend(fontsize=7, frameon=False)
    for fig, name in ((fig_roc, "roc_curves.png"), (fig_cal, "calibration.png")):
        fig.tight_layout()
        fig.savefig(FIG / name)
        plt.close(fig)

    import shap

    booster = xgb.Booster()
    booster.load_model(str(s.artifact_dir / manifest["artifacts"]["risk_fatigue"]["path"]))
    sample = X.iloc[idx["fatigue"][:2000]]
    sv = shap.TreeExplainer(booster).shap_values(sample)
    plt.figure()
    shap.summary_plot(sv, sample, show=False, max_display=12, plot_size=(7, 4.5))
    plt.title("SHAP - strong tiredness model (synthetic test split)")
    plt.tight_layout()
    plt.savefig(FIG / "shap_fatigue_beeswarm.png")
    plt.close("all")
    return out


TRUE_THRESHOLDS = {  # from holdout/generator_params.json -> fatigue model hinges
    "TSH": ("upper", "tsh_hinge_above"),
    "FT4": ("lower", "ft4_hinge_below"),
    "FERRITIN": ("lower", "ferritin_hinge_below"),
    "VITD": ("lower", "vitd_hinge_below"),
    "B12": ("lower", "b12_hinge_below"),
    "MG": ("lower", "mg_hinge_below"),
}


def eval_bands(s, manifest) -> dict:
    params = json.loads((s.holdout_dir / "generator_params.json").read_text())["fatigue"]
    bands = json.loads((s.artifact_dir / manifest["artifacts"]["functional_bands"]["path"]).read_text())["bands"]
    rows = {}
    fig, axes = plt.subplots(2, 3, figsize=(9, 5.2))
    for ax, (key, (edge, param)) in zip(axes.flat, TRUE_THRESHOLDS.items(), strict=True):
        b = bands[key]
        f = b["functional"] or {}
        truth = params[param]
        found = f.get("high") if edge == "upper" else f.get("low")
        ci = f.get("high_ci") if edge == "upper" else f.get("low_ci")
        ref = b["reference"]["high"] if edge == "upper" else b["reference"]["low"]
        rows[key] = {
            "edge": edge, "generator_threshold": truth, "discovered": found, "discovered_ci90": ci,
            "lab_reference_edge": ref,
            "relative_error": round(abs(found - truth) / truth, 4) if found else None,
            "truth_within_ci": bool(ci and ci[0] <= truth <= ci[1]),
            "narrower_than_reference": bool(found and ((edge == "lower" and found > ref) or (edge == "upper" and found < ref))),
        }
        xs = [p["value"] for p in b["risk_curve"]]
        ys = [p["risk"] * 100 for p in b["risk_curve"]]
        ax.plot(xs, ys, color=BLUE, lw=2)
        ax.axvline(truth, color=INK, lw=1.2, ls="--", label="generator threshold")
        if found:
            ax.axvline(found, color=ORANGE, lw=1.5, label="discovered edge")
        ax.axvspan(b["reference"]["low"], b["reference"]["high"], color="#cde2fb", alpha=0.5, lw=0, label="lab range")
        if key in ("TSH", "FERRITIN", "B12", "VITD"):
            ax.set_xscale("log")
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
            ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_title(f"{load_catalog()[key].display} ({b['unit']})", fontsize=9)
        ax.set_ylabel("tiredness risk %")
    axes.flat[0].legend(fontsize=6, frameon=False)
    fig.suptitle("Functional-band discovery vs hidden generator thresholds (synthetic data)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "functional_bands_vs_truth.png")
    plt.close(fig)
    rel = [r["relative_error"] for r in rows.values() if r["relative_error"] is not None]
    return {"per_marker": rows, "median_relative_error": round(float(np.median(rel)), 4),
            "truth_within_ci_rate": round(float(np.mean([r["truth_within_ci"] for r in rows.values()])), 4),
            "narrower_than_reference_rate": round(float(np.mean([r["narrower_than_reference"] for r in rows.values()])), 4)}


def eval_etl(s) -> dict:
    gen = json.loads((s.raw_dir / "_generation_summary.json").read_text())
    out = {"generated": gen["lab_rows"], "reports": gen["reports"], "patients": gen["patients"]}
    for engine in ("duckdb", "spark"):
        path = s.lake_dir / "audit" / f"etl_summary_{engine}.json"
        if path.exists():
            out[engine] = json.loads(path.read_text())
    audit = out.get("duckdb", out.get("spark", {})).get("audit_totals", {})
    injected = gen["lab_rows"]
    out["reconciliation"] = {
        "duplicates_injected": injected["duplicates"], "duplicates_removed": audit.get("duplicates_removed"),
        "missing_units_injected": injected["missing_units"], "units_inferred": audit.get("unit_inferred"),
        "decimal_misreads_injected": injected["decimal_misreads"], "decimal_misread_suspects": audit.get("decimal_misread_suspect"),
        "label_typos_injected": injected["typos"], "rows_left_unmapped": audit.get("unmapped_rows"),
        "typo_recovery_rate": round(1 - audit.get("unmapped_rows", 0) / max(1, injected["typos"]), 4),
    }
    return out


def main() -> None:
    s = get_settings()
    manifest = json.loads((s.artifact_dir / "manifest.json").read_text())
    df = load_training_frame(s)
    results = {"label": SYNTHETIC_DATA_LABEL, "model_version": {k: manifest[k] for k in ("semver", "seed", "created_at")}}
    t = time.perf_counter()
    results["etl"] = eval_etl(s)
    results["functional_bands"] = eval_bands(s, manifest)
    results["clustering"] = eval_clustering(s, manifest, df)
    results["risk"] = eval_risk(s, manifest, df)
    results["ocr"] = eval_ocr(s)
    results["seconds"] = round(time.perf_counter() - t, 1)
    (RES / "bda_metrics.json").write_text(json.dumps(results, indent=2, default=float), encoding="utf-8")
    print(json.dumps({k: results[k] for k in ("functional_bands", "risk")}, indent=1, default=float)[:3000])
    print(json.dumps(results["ocr"]["overall"], indent=1), json.dumps(results["ocr"]["scanned"], indent=1))


if __name__ == "__main__":
    main()
