"""Population-level clustering (Week 7): K-Means, Gaussian mixture, DBSCAN.

All three run on the standardized 9-marker vector (log scale for skewed markers).

* K-Means - k chosen by silhouette on a sample; exported (scaler + centroids) as
  the online assignment model.
* GMM     - components chosen by BIC; exported for soft membership probabilities.
* DBSCAN  - density-based discovery of non-standard sub-clusters and noise on a
  sample; eps from the k-distance curve. Not used online (no predict), reported
  in the evaluation.

Cluster profiles (median markers, symptom prevalence) are what the UI and the
GraphRAG prompt show. Names are generated from which markers deviate most from
the population median; they describe patterns, not diagnoses.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import NearestNeighbors

from bda_engine.features.build import EPS, LOG_MARKERS
from polymarker_common.catalog import BIOMARKER_KEYS, load_catalog

K_RANGE = range(3, 10)
SAMPLE = 12_000


def cluster_matrix(values: pd.DataFrame) -> np.ndarray:
    cols = []
    for k in BIOMARKER_KEYS:
        v = values[k].to_numpy(dtype=float)
        cols.append(np.log(np.maximum(v, EPS)) if k in LOG_MARKERS else v)
    return np.column_stack(cols)


def _sample(n: int, size: int, rng: np.random.Generator) -> np.ndarray:
    return rng.choice(n, size=min(n, size), replace=False)


def _name_cluster(z_medians: dict[str, float]) -> str:
    catalog = load_catalog()
    parts = []
    for k, z in sorted(z_medians.items(), key=lambda kv: -abs(kv[1]))[:2]:
        if abs(z) < 0.6:
            continue
        parts.append(f"{'high' if z > 0 else 'low'} {catalog[k].display}")
    if not parts:
        return "Balanced profile"
    text = ", ".join(parts)
    return text[0].upper() + text[1:]


def fit_clusters(values: pd.DataFrame, symptoms: pd.DataFrame, seed: int) -> dict:
    """values: imputed SI markers (one row per patient); symptoms: binary targets + severity."""
    rng = np.random.default_rng(seed)
    raw = cluster_matrix(values)
    mean, std = raw.mean(axis=0), raw.std(axis=0)
    Z = (raw - mean) / std
    idx = _sample(len(Z), SAMPLE, rng)
    Zs = Z[idx]

    kmeans_scores = []
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=5, random_state=seed).fit(Zs)
        kmeans_scores.append(
            {
                "k": k,
                "silhouette": float(
                    silhouette_score(Zs, km.labels_, sample_size=5000, random_state=seed)
                ),
                "davies_bouldin": float(davies_bouldin_score(Zs, km.labels_)),
                "calinski_harabasz": float(calinski_harabasz_score(Zs, km.labels_)),
                "inertia": float(km.inertia_),
            }
        )
    best_k = max(kmeans_scores, key=lambda s: s["silhouette"])["k"]
    kmeans = KMeans(n_clusters=best_k, n_init=10, random_state=seed).fit(Z)
    labels = kmeans.labels_

    gmm_scores = []
    for k in K_RANGE:
        g = GaussianMixture(n_components=k, covariance_type="full", random_state=seed).fit(Zs)
        gmm_scores.append({"k": k, "bic": float(g.bic(Zs))})
    best_g = min(gmm_scores, key=lambda s: s["bic"])["k"]
    gmm = GaussianMixture(n_components=best_g, covariance_type="full", random_state=seed).fit(Z)
    gmm_labels = gmm.predict(Z)

    # DBSCAN on a sample: eps = 90th percentile of the min_samples-NN distance.
    min_samples = 25
    d_idx = _sample(len(Z), 8000, rng)
    Zd = Z[d_idx]
    nn = NearestNeighbors(n_neighbors=min_samples).fit(Zd)
    kdist = np.sort(nn.kneighbors(Zd)[0][:, -1])
    eps = float(np.quantile(kdist, 0.9))
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(Zd)
    db_labels = db.labels_
    db_clusters = sorted(set(db_labels) - {-1})
    db_profile = []
    for c in db_clusters:
        mask = db_labels == c
        sub_sym = symptoms.iloc[d_idx[mask]]
        db_profile.append(
            {
                "cluster": int(c),
                "size": int(mask.sum()),
                "fatigue_rate": float(sub_sym["fatigue"].mean()),
            }
        )
    db_metrics = {
        "eps": eps,
        "min_samples": min_samples,
        "n_clusters": len(db_clusters),
        "noise_fraction": float((db_labels == -1).mean()),
        "noise_fatigue_rate": float(symptoms.iloc[d_idx[db_labels == -1]]["fatigue"].mean())
        if (db_labels == -1).any()
        else None,
        "core_fatigue_rate": float(symptoms.iloc[d_idx[db_labels != -1]]["fatigue"].mean())
        if (db_labels != -1).any()
        else None,
        "clusters": db_profile,
    }
    if len(db_clusters) >= 2:
        core = db_labels != -1
        db_metrics["silhouette_core"] = float(
            silhouette_score(Zd[core], db_labels[core], sample_size=4000, random_state=seed)
        )

    pop_median = np.median(Z, axis=0)
    profiles = []
    for c in range(best_k):
        mask = labels == c
        z_med = dict(
            zip(BIOMARKER_KEYS, (np.median(Z[mask], axis=0) - pop_median).tolist(), strict=True)
        )
        sub = values[mask]
        sym = symptoms[mask]
        profiles.append(
            {
                "cluster": c,
                "name": _name_cluster(z_med),
                "size": int(mask.sum()),
                "share": round(float(mask.mean()), 4),
                "median_markers": {k: round(float(sub[k].median()), 3) for k in BIOMARKER_KEYS},
                "z_median": {k: round(v, 3) for k, v in z_med.items()},
                "fatigue_rate": round(float(sym["fatigue"].mean()), 4),
                "brain_fog_rate": round(float(sym["brain_fog"].mean()), 4),
                "hair_loss_rate": round(float(sym["hair_loss"].mean()), 4),
                "mean_fatigue_severity": round(float(sym["fatigue_severity"].mean()), 2),
            }
        )

    pca = PCA(n_components=2, random_state=seed).fit(Z)
    proj_idx = _sample(len(Z), 2000, rng)
    xy = pca.transform(Z[proj_idx])
    projection = {
        "components": pca.components_.tolist(),
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "points": [
            {
                "x": round(float(x), 3),
                "y": round(float(y), 3),
                "cluster": int(labels[i]),
                "fatigue": int(symptoms["fatigue"].iloc[i]),
            }
            for (x, y), i in zip(xy, proj_idx, strict=True)
        ],
    }
    full_metrics = {
        "kmeans": {
            "k": best_k,
            "silhouette": float(silhouette_score(Z, labels, sample_size=10000, random_state=seed)),
            "davies_bouldin": float(davies_bouldin_score(Z, labels)),
            "calinski_harabasz": float(calinski_harabasz_score(Z, labels)),
            "selection": kmeans_scores,
        },
        "gmm": {
            "components": best_g,
            "silhouette": float(
                silhouette_score(Z, gmm_labels, sample_size=10000, random_state=seed)
            ),
            "davies_bouldin": float(davies_bouldin_score(Z, gmm_labels)),
            "selection": gmm_scores,
        },
        "dbscan": db_metrics,
    }
    model = {
        "features": list(BIOMARKER_KEYS),
        "log_markers": list(LOG_MARKERS),
        "eps": EPS,
        "scaler": {"mean": mean.tolist(), "std": std.tolist()},
        "kmeans": {"centroids": kmeans.cluster_centers_.tolist()},
        "gmm": {
            "weights": gmm.weights_.tolist(),
            "means": gmm.means_.tolist(),
            "covariances": gmm.covariances_.tolist(),
        },
        "profiles": profiles,
    }
    return {
        "model": model,
        "projection": projection,
        "metrics": full_metrics,
        "labels": labels,
        "gmm_labels": gmm_labels,
        "dbscan_sample": {"index": d_idx.tolist(), "labels": db_labels.tolist()},
    }
