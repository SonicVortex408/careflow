"""Synthetic multi-source lab data lake for PolyMarker Analytics.

    uv run python -m bda_engine.scripts.generate_synthetic_data [--patients 50000] [--pdfs 500]

Produces (under BDA_DATA_DIR, default bda_engine/data/):

raw/patients.csv                          demographics (no names)
raw/lab_results/lab=<slug>/part-*.csv     four labs export CSV ...
raw/lab_results/lab=<slug>/part-*.jsonl   ... one exports JSON lines (source variety)
raw/intake/part-*.jsonl                   symptom intake forms with free-text answers
raw/pdf/<report_id>.pdf                   ~500 rendered reports, 4 layouts, ~35% scanned images
holdout/generator_params.json             the generative model (NEVER read by ETL/models)
holdout/pdf_ground_truth.jsonl            expected values/text for OCR evaluation
holdout/latent.parquet                    latent phenotype per patient (cluster evaluation only)

Heterogeneity is deliberate: lab-specific labels and units (conventional vs SI),
decimal commas, "<" detection limits, missing units, label typos, decimal-point
misreads, duplicate rows, partial panels, free-text PROM answers.

Validity threat (risk R2): PROMs are generated *from* the markers below, so any
model trained on this data partly rediscovers these rules. The parameters are
written to holdout/ so evaluation can compare discovered thresholds against the
truth and report the circularity explicitly.

Everything produced here is synthetic, for research/demo purposes, and is not
clinical guidance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from bda_engine.config import get_settings
from polymarker_common.catalog import BIOMARKER_KEYS, load_catalog
from polymarker_common.normalizer import clean_unit

# ---------------------------------------------------------------------------
# Lab sources: labels, units and formatting conventions differ per lab.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Lab:
    slug: str
    name: str
    fmt: str  # csv | jsonl
    decimal_comma: bool
    detection_limit_tpo: float | None
    labels: dict[str, str]
    units: dict[str, str]
    panel_rate: dict[str, float]


LABS: tuple[Lab, ...] = (
    Lab(
        "meridian",
        "Meridian Diagnostics",
        "csv",
        False,
        None,
        {
            "TSH": "TSH",
            "FT3": "Free T3",
            "FT4": "Free T4",
            "TPOAB": "Thyroid Peroxidase Antibodies",
            "VITD": "Vitamin D, 25-Hydroxy",
            "B12": "Vitamin B12",
            "FERRITIN": "Ferritin",
            "MG": "Magnesium",
            "ZINC": "Zinc",
        },
        {
            "TSH": "uIU/mL",
            "FT3": "pg/mL",
            "FT4": "ng/dL",
            "TPOAB": "IU/mL",
            "VITD": "ng/mL",
            "B12": "pg/mL",
            "FERRITIN": "ng/mL",
            "MG": "mg/dL",
            "ZINC": "ug/dL",
        },
        {"TPOAB": 0.65, "MG": 0.7, "ZINC": 0.45},
    ),
    Lab(
        "northside",
        "Northside Pathology",
        "csv",
        True,
        None,
        {
            "TSH": "Thyroid Stimulating Hormone",
            "FT3": "FT3",
            "FT4": "Thyroxine, Free",
            "TPOAB": "TPO Ab",
            "VITD": "25-OH Vitamin D",
            "B12": "Cobalamin",
            "FERRITIN": "Serum Ferritin",
            "MG": "Magnesium, Serum",
            "ZINC": "Zinc, Serum",
        },
        {
            "TSH": "mIU/L",
            "FT3": "pmol/L",
            "FT4": "pmol/L",
            "TPOAB": "kIU/L",
            "VITD": "nmol/L",
            "B12": "pmol/L",
            "FERRITIN": "ug/L",
            "MG": "mmol/L",
            "ZINC": "umol/L",
        },
        {"TPOAB": 0.55, "MG": 0.8, "ZINC": 0.5},
    ),
    Lab(
        "citycare",
        "CityCare Labs",
        "csv",
        False,
        None,
        {
            "TSH": "TSH 3RD GENERATION",
            "FT3": "FREE T3 (FT3)",
            "FT4": "FREE T4 (FT4)",
            "TPOAB": "ANTI-TPO",
            "VITD": "VITAMIN D 25 OH",
            "B12": "VITAMIN B12",
            "FERRITIN": "FERRITIN",
            "MG": "MAGNESIUM",
            "ZINC": "ZINC",
        },
        {
            "TSH": "mIU/L",
            "FT3": "pmol/L",
            "FT4": "pmol/L",
            "TPOAB": "IU/mL",
            "VITD": "ng/mL",
            "B12": "pmol/L",
            "FERRITIN": "ug/L",
            "MG": "mmol/L",
            "ZINC": "umol/L",
        },
        {"TPOAB": 0.6, "MG": 0.6, "ZINC": 0.4},
    ),
    Lab(
        "apex",
        "Apex Clinical Laboratory",
        "csv",
        False,
        9.0,
        {
            "TSH": "Thyrotropin",
            "FT3": "Triiodothyronine, Free",
            "FT4": "Free Thyroxine",
            "TPOAB": "Anti-TPO Antibodies",
            "VITD": "25-Hydroxyvitamin D",
            "B12": "Vitamin B12 (Cobalamin)",
            "FERRITIN": "Ferritin, Serum",
            "MG": "S. Magnesium",
            "ZINC": "Plasma Zinc",
        },
        {
            "TSH": "uIU/mL",
            "FT3": "pg/dL",
            "FT4": "ng/dL",
            "TPOAB": "IU/mL",
            "VITD": "ng/mL",
            "B12": "pg/mL",
            "FERRITIN": "ng/mL",
            "MG": "mEq/L",
            "ZINC": "mcg/dL",
        },
        {"TPOAB": 0.7, "MG": 0.75, "ZINC": 0.55},
    ),
    Lab(
        "riverside",
        "Riverside Health Labs",
        "jsonl",
        False,
        None,
        {
            "TSH": "s-TSH",
            "FT3": "Free Triiodothyronine",
            "FT4": "FT4",
            "TPOAB": "Anti Thyroid Peroxidase",
            "VITD": "Vitamin D Total",
            "B12": "Vit B12",
            "FERRITIN": "S. Ferritin",
            "MG": "Serum Mg",
            "ZINC": "Zinc, Plasma",
        },
        {
            "TSH": "mU/L",
            "FT3": "pmol/L",
            "FT4": "pmol/L",
            "TPOAB": "U/mL",
            "VITD": "nmol/L",
            "B12": "pmol/L",
            "FERRITIN": "ug/L",
            "MG": "mmol/L",
            "ZINC": "umol/L",
        },
        {"TPOAB": 0.5, "MG": 0.65, "ZINC": 0.35},
    ),
)
LAB_WEIGHTS = (0.3, 0.2, 0.2, 0.18, 0.12)
BASE_PANEL_RATE = 0.94

# ---------------------------------------------------------------------------
# Generative model (held out). Values in SI canonical units.
# ---------------------------------------------------------------------------

GENERATOR_PARAMS = {
    "latent_prevalence": {
        "malabsorption": 0.05,
        "autoimmune": {"base": 0.08, "female_extra": 0.06},
        "subclinical_hypo": {"base": 0.05, "autoimmune_extra": 0.25},
        "overt_hypo": {"base": 0.01, "autoimmune_extra": 0.06},
        "hyperthyroid": 0.015,
        "iron_deficiency": {
            "base": 0.05,
            "premenopausal_female_extra": 0.10,
            "malabsorption_extra": 0.25,
        },
        "vitd_deficiency": {"base": 0.14, "malabsorption_extra": 0.2},
        "b12_deficiency": {"base": 0.04, "age_over_60_extra": 0.03, "malabsorption_extra": 0.3},
        "mg_low": {"base": 0.05, "malabsorption_extra": 0.15},
        "zinc_low": {"base": 0.05, "malabsorption_extra": 0.3},
    },
    "marker_models": "log-normal per latent state; see _markers() for medians and sds",
    # Symptom dose-response: hinge functions on log markers. The *functional*
    # thresholds deliberately sit inside the laboratory reference intervals so
    # that functional-range discovery has something to find.
    "fatigue": {
        "intercept": -1.35,
        "tsh_hinge_above": 2.5,
        "tsh_weight": 0.8,
        "ft4_hinge_below": 12.0,
        "ft4_weight": 0.9,
        "ferritin_hinge_below": 45.0,
        "ferritin_weight": 1.0,
        "vitd_hinge_below": 60.0,
        "vitd_weight": 0.5,
        "b12_hinge_below": 260.0,
        "b12_weight": 0.7,
        "mg_hinge_below": 0.78,
        "mg_weight": 0.4,
        "ft4_hinge_above": 24.0,
        "hyper_weight": 0.8,
        "interaction_ferritin_below_30_and_tsh_above_2_5": 0.6,
        "female": 0.25,
        "age_per_year_from_45": 0.004,
        "noise_sd": 0.75,
        "severity_scale": {"offset": 6.0, "slope": 2.6, "noise_sd": 1.0},
    },
    "brain_fog": {
        "b12_weight": 1.1,
        "tsh_weight": 0.6,
        "ft4_weight": 0.8,
        "ferritin_weight": 0.4,
        "vitd_weight": 0.3,
        "noise_sd": 0.8,
        "level_quantiles": [0.28, 0.52, 0.76, 0.92],
    },
    "hair_loss": {
        "ferritin_weight": 0.9,
        "zinc_hinge_below": 10.5,
        "zinc_weight": 0.6,
        "tsh_weight": 0.7,
        "hyper_weight": 0.6,
        "female": 0.35,
        "noise_sd": 0.8,
        "level_quantiles": [0.5, 0.78, 0.93],
    },
    "noise": {
        "within_person_log_sd": 0.08,
        "label_typo_rate": 0.01,
        "missing_unit_rate": 0.01,
        "decimal_misread_rate": 0.003,
        "duplicate_row_rate": 0.005,
        "reports_per_patient": "1 + Poisson(0.35), max 3",
    },
}


def _hinge(x):
    return np.maximum(0.0, x)


def _latent(rng: np.random.Generator, n: int) -> pd.DataFrame:
    p = GENERATOR_PARAMS["latent_prevalence"]
    female = rng.random(n) < 0.6
    age = np.clip(rng.normal(46, 15, n), 18, 85).astype(int)
    malabs = rng.random(n) < p["malabsorption"]
    autoimmune = rng.random(n) < p["autoimmune"]["base"] + p["autoimmune"]["female_extra"] * female
    u = rng.random(n)
    sub_p = p["subclinical_hypo"]["base"] + p["subclinical_hypo"]["autoimmune_extra"] * autoimmune
    overt_p = p["overt_hypo"]["base"] + p["overt_hypo"]["autoimmune_extra"] * autoimmune
    hyper_p = np.full(n, p["hyperthyroid"])
    thyroid = np.where(
        u < overt_p,
        "overt_hypo",
        np.where(
            u < overt_p + hyper_p,
            "hyper",
            np.where(u < overt_p + hyper_p + sub_p, "subclinical", "euthyroid"),
        ),
    )
    iron = rng.random(n) < (
        p["iron_deficiency"]["base"]
        + p["iron_deficiency"]["premenopausal_female_extra"] * (female & (age < 50))
        + p["iron_deficiency"]["malabsorption_extra"] * malabs
    )
    vitd = (
        rng.random(n)
        < p["vitd_deficiency"]["base"] + p["vitd_deficiency"]["malabsorption_extra"] * malabs
    )
    b12 = rng.random(n) < (
        p["b12_deficiency"]["base"]
        + p["b12_deficiency"]["age_over_60_extra"] * (age > 60)
        + p["b12_deficiency"]["malabsorption_extra"] * malabs
    )
    mg = rng.random(n) < p["mg_low"]["base"] + p["mg_low"]["malabsorption_extra"] * malabs
    zinc = rng.random(n) < p["zinc_low"]["base"] + p["zinc_low"]["malabsorption_extra"] * malabs

    n_micro = iron.astype(int) + vitd + b12 + mg + zinc
    phenotype = np.select(
        [
            np.isin(thyroid, ["overt_hypo", "hyper"]),
            (thyroid == "subclinical") | autoimmune,
            malabs | (n_micro >= 2),
            iron,
            vitd | b12,
            mg | zinc,
        ],
        [
            "thyroid_overt",
            "thyroid_subclinical_autoimmune",
            "multi_micronutrient",
            "iron_deficient",
            "vitamin_deficient",
            "mineral_low",
        ],
        default="replete",
    )
    return pd.DataFrame(
        {
            "patient_id": [f"P{i:06d}" for i in range(n)],
            "sex": np.where(female, "F", "M"),
            "age": age,
            "malabsorption": malabs,
            "autoimmune": autoimmune,
            "thyroid_state": thyroid,
            "iron_deficient": iron,
            "vitd_deficient": vitd,
            "b12_deficient": b12,
            "mg_low": mg,
            "zinc_low": zinc,
            "phenotype": phenotype,
        }
    )


def _markers(rng: np.random.Generator, lat: pd.DataFrame) -> pd.DataFrame:
    """Patient-level mean marker values (SI)."""
    n = len(lat)
    th = lat["thyroid_state"].to_numpy()
    female = (lat["sex"] == "F").to_numpy()

    def lognorm(median, sd):
        return np.log(median) + rng.normal(0, 1, n) * sd

    ln_tsh = np.select(
        [th == "subclinical", th == "overt_hypo", th == "hyper"],
        [lognorm(6.2, 0.28), lognorm(22, 0.5), lognorm(0.06, 0.7)],
        default=lognorm(1.7, 0.42),
    )
    ln_ft4 = np.select(
        [th == "subclinical", th == "overt_hypo", th == "hyper"],
        [lognorm(13.2, 0.10), lognorm(7.5, 0.18), lognorm(32, 0.2)],
        default=lognorm(15.5, 0.11) - 0.05 * (ln_tsh - np.log(1.7)),
    )
    ln_ratio = (
        lognorm(0.33, 0.08)
        + np.log(0.88) * lat["iron_deficient"].to_numpy()
        + np.log(0.93) * lat["zinc_low"].to_numpy()
        + np.log(1.25) * (th == "hyper")
    )
    ln_ft3 = ln_ft4 + ln_ratio
    ln_tpo = np.where(lat["autoimmune"], lognorm(190, 0.9), lognorm(8, 0.6))
    ln_fer = np.where(
        lat["iron_deficient"],
        lognorm(9, 0.45),
        np.where(female, lognorm(55, 0.55), lognorm(130, 0.55)),
    )
    ln_vitd = np.where(lat["vitd_deficient"], lognorm(30, 0.3), lognorm(72, 0.3))
    ln_b12 = np.where(lat["b12_deficient"], lognorm(125, 0.25), lognorm(340, 0.32))
    mg = np.where(lat["mg_low"], rng.normal(0.63, 0.06, n), rng.normal(0.86, 0.06, n))
    zn = np.where(lat["zinc_low"], rng.normal(8.4, 1.1, n), rng.normal(13.8, 1.9, n))

    catalog = load_catalog()
    out = pd.DataFrame(
        {
            "TSH": np.exp(ln_tsh),
            "FT3": np.exp(ln_ft3),
            "FT4": np.exp(ln_ft4),
            "TPOAB": np.exp(ln_tpo),
            "VITD": np.exp(ln_vitd),
            "B12": np.exp(ln_b12),
            "FERRITIN": np.exp(ln_fer),
            "MG": mg,
            "ZINC": zn,
        }
    )
    for key in BIOMARKER_KEYS:
        pl = catalog[key].plausible
        out[key] = out[key].clip(max(pl.low, 1e-3) * 1.01, pl.high * 0.99)
    return out


def _proms(rng: np.random.Generator, m: pd.DataFrame, lat: pd.DataFrame) -> pd.DataFrame:
    f = GENERATOR_PARAMS["fatigue"]
    n = len(m)
    female = (lat["sex"] == "F").to_numpy()
    age = lat["age"].to_numpy()
    tsh_t = np.minimum(_hinge(np.log(m.TSH) - np.log(f["tsh_hinge_above"])) / np.log(4), 1.5)
    ft4_t = np.minimum(_hinge(np.log(f["ft4_hinge_below"]) - np.log(m.FT4)) / 0.4, 1.5)
    fer_t = np.minimum(
        _hinge(np.log(f["ferritin_hinge_below"]) - np.log(m.FERRITIN)) / np.log(4), 1.5
    )
    vitd_t = np.minimum(_hinge(np.log(f["vitd_hinge_below"]) - np.log(m.VITD)) / np.log(2.5), 1.5)
    b12_t = np.minimum(_hinge(np.log(f["b12_hinge_below"]) - np.log(m.B12)) / np.log(2.5), 1.5)
    mg_t = _hinge(f["mg_hinge_below"] - m.MG) / 0.15
    hyper_t = _hinge(np.log(m.FT4) - np.log(f["ft4_hinge_above"])) / 0.3
    inter = ((m.FERRITIN < 30) & (m.TSH > 2.5)).astype(float)

    fat = (
        f["intercept"]
        + f["tsh_weight"] * tsh_t
        + f["ft4_weight"] * ft4_t
        + f["ferritin_weight"] * fer_t
        + f["vitd_weight"] * vitd_t
        + f["b12_weight"] * b12_t
        + f["mg_weight"] * mg_t
        + f["hyper_weight"] * hyper_t
        + f["interaction_ferritin_below_30_and_tsh_above_2_5"] * inter
        + f["female"] * female
        + f["age_per_year_from_45"] * (age - 45)
        + rng.normal(0, f["noise_sd"], n)
    )
    s = f["severity_scale"]
    severity = np.clip(
        np.round(s["offset"] + s["slope"] * fat + rng.normal(0, s["noise_sd"], n)), 1, 10
    ).astype(int)

    b = GENERATOR_PARAMS["brain_fog"]
    fog = (
        b["b12_weight"] * b12_t
        + b["tsh_weight"] * tsh_t
        + b["ft4_weight"] * ft4_t
        + b["ferritin_weight"] * fer_t
        + b["vitd_weight"] * vitd_t
        + rng.normal(0, b["noise_sd"], n)
    )
    fog_levels = np.searchsorted(np.quantile(fog, b["level_quantiles"]), fog)

    h = GENERATOR_PARAMS["hair_loss"]
    zinc_t = _hinge(h["zinc_hinge_below"] - m.ZINC) / 2.0
    hair = (
        h["ferritin_weight"] * fer_t
        + h["zinc_weight"] * zinc_t
        + h["tsh_weight"] * tsh_t
        + h["hyper_weight"] * hyper_t
        + h["female"] * female
        + rng.normal(0, h["noise_sd"], n)
    )
    hair_levels = np.searchsorted(np.quantile(hair, h["level_quantiles"]), hair)

    fog_names = np.array(["never", "rarely", "sometimes", "often", "always"])
    hair_names = np.array(["none", "mild", "moderate", "severe"])
    return pd.DataFrame(
        {
            "fatigue_severity": severity,
            "brain_fog_frequency": fog_names[fog_levels],
            "hair_loss": hair_names[hair_levels],
        }
    )


# ---------------------------------------------------------------------------
# Raw exports
# ---------------------------------------------------------------------------

FOG_SYNONYMS = {
    "never": ["never", "Never", "not at all"],
    "rarely": ["rarely", "Rarely", "seldom"],
    "sometimes": ["sometimes", "Sometimes", "occasionally"],
    "often": ["often", "Often", "frequently", "most days"],
    "always": ["always", "Always", "constantly", "every day"],
}
HAIR_SYNONYMS = {
    "none": ["none", "None", "no"],
    "mild": ["mild", "Mild", "a little"],
    "moderate": ["moderate", "Moderate"],
    "severe": ["severe", "Severe", "a lot"],
}


def _decimals(value: float) -> int:
    if value >= 100:
        return 0
    if value >= 10:
        return 1
    if value >= 1:
        return 2
    return 3


def _fmt(value: float, comma: bool, decimals: int | None = None) -> str:
    d = _decimals(value) if decimals is None else decimals
    text = f"{value:.{d}f}"
    return text.replace(".", ",") if comma else text


def _typo(label: str, rng: random.Random) -> str:
    if len(label) < 5:
        return label
    i = rng.randrange(1, len(label) - 1)
    return label[:i] + label[i + 1 :]


def _lab_value(key: str, si_value: float, unit: str) -> float:
    return si_value / load_catalog()[key].units[clean_unit(unit)]


def _reference_text(key: str, unit: str, sex: str, comma: bool) -> str:
    marker = load_catalog()[key]
    ref = marker.reference_for(sex)
    lo = _lab_value(key, ref.low, unit)
    hi = _lab_value(key, ref.high, unit)
    if key == "TPOAB":
        return f"< {_fmt(hi, comma, 0)}"
    d = max(_decimals(lo), _decimals(hi)) if hi < 10 else _decimals(hi)
    return f"{_fmt(lo, comma, d)} - {_fmt(hi, comma, d)}"


def build_reports(
    rng: np.random.Generator, lat: pd.DataFrame, patient_markers: pd.DataFrame
) -> pd.DataFrame:
    counts = 1 + np.minimum(rng.poisson(0.35, len(lat)), 2)
    idx = np.repeat(np.arange(len(lat)), counts)
    seq = np.concatenate([np.arange(c) for c in counts])
    lab_idx = rng.choice(len(LABS), size=len(lat), p=LAB_WEIGHTS)[idx]
    base = pd.Timestamp("2023-01-01")
    first = rng.integers(0, 3 * 365 - 400, len(lat))[idx]
    days = first + seq * rng.integers(90, 200, len(idx))
    reports = pd.DataFrame(
        {
            "report_id": [f"R{i:07d}" for i in range(len(idx))],
            "patient_idx": idx,
            "patient_id": lat["patient_id"].to_numpy()[idx],
            "seq": seq,
            "lab_idx": lab_idx,
            "collected_at": (base + pd.to_timedelta(days, unit="D")).strftime("%Y-%m-%d"),
        }
    )
    reports["is_latest"] = reports["seq"] == reports.groupby("patient_idx")["seq"].transform("max")
    wp = GENERATOR_PARAMS["noise"]["within_person_log_sd"]
    month = pd.to_datetime(reports["collected_at"]).dt.month.to_numpy()
    for key in BIOMARKER_KEYS:
        mean = patient_markers[key].to_numpy()[idx]
        if key in ("MG", "ZINC"):
            val = mean * (1 + rng.normal(0, wp / 2, len(idx)))
        else:
            val = mean * np.exp(rng.normal(0, wp, len(idx)))
        if key == "VITD":  # seasonal swing, peaks late summer
            val = val * (1 + 0.12 * np.cos(2 * np.pi * (month - 8) / 12))
        pl = load_catalog()[key].plausible
        reports[key] = np.clip(val, max(pl.low, 1e-3) * 1.01, pl.high * 0.99)
    return reports


def write_lab_exports(reports: pd.DataFrame, lat: pd.DataFrame, raw_dir: Path, seed: int) -> dict:
    rng = np.random.default_rng(seed + 1)
    prng = random.Random(seed + 2)
    noise = GENERATOR_PARAMS["noise"]
    sex = lat["sex"].to_numpy()
    stats = {"rows": 0, "typos": 0, "missing_units": 0, "decimal_misreads": 0, "duplicates": 0}
    for li, lab in enumerate(LABS):
        sub = reports[reports["lab_idx"] == li]
        rows = []
        for key in BIOMARKER_KEYS:
            rate = lab.panel_rate.get(key, BASE_PANEL_RATE)
            present = rng.random(len(sub)) < rate
            part = sub[present]
            unit = lab.units[key]
            factor = load_catalog()[key].units[clean_unit(unit)]
            values = part[key].to_numpy() / factor
            ref_by_sex = {s: _reference_text(key, unit, s, lab.decimal_comma) for s in ("F", "M")}
            psex = sex[part["patient_idx"].to_numpy()]
            for rid, pid, date, v, s in zip(
                part["report_id"],
                part["patient_id"],
                part["collected_at"],
                values,
                psex,
                strict=True,
            ):
                label = lab.labels[key]
                if prng.random() < noise["label_typo_rate"]:
                    label = _typo(label, prng)
                    stats["typos"] += 1
                u = unit
                if prng.random() < noise["missing_unit_rate"]:
                    u = ""
                    stats["missing_units"] += 1
                shown = v
                if prng.random() < noise["decimal_misread_rate"]:
                    shown = v * 10
                    stats["decimal_misreads"] += 1
                if lab.detection_limit_tpo and key == "TPOAB" and v < lab.detection_limit_tpo:
                    value_text = f"<{_fmt(lab.detection_limit_tpo, lab.decimal_comma, 0)}"
                else:
                    value_text = _fmt(shown, lab.decimal_comma)
                ref = load_catalog()[key].reference_for(s)
                si = v * factor
                flag = "H" if si > ref.high else ("L" if si < ref.low else "")
                row = {
                    "report_id": rid,
                    "patient_id": pid,
                    "lab_provider": lab.name,
                    "collected_at": date,
                    "raw_label": label,
                    "raw_value": value_text,
                    "raw_unit": u,
                    "raw_reference": ref_by_sex[s],
                    "flag": flag,
                }
                rows.append(row)
                if prng.random() < noise["duplicate_row_rate"]:
                    rows.append(dict(row))
                    stats["duplicates"] += 1
        df = pd.DataFrame(rows).sort_values(["report_id", "raw_label"], kind="stable")
        stats["rows"] += len(df)
        out = raw_dir / "lab_results" / f"lab={lab.slug}"
        out.mkdir(parents=True, exist_ok=True)
        chunk = 100_000
        for i in range(0, len(df), chunk):
            part_df = df.iloc[i : i + chunk]
            if lab.fmt == "csv":
                part_df.to_csv(out / f"part-{i // chunk:03d}.csv", index=False)
            else:
                part_df.to_json(out / f"part-{i // chunk:03d}.jsonl", orient="records", lines=True)
    return stats


def write_intake(reports: pd.DataFrame, proms: pd.DataFrame, raw_dir: Path, seed: int) -> int:
    prng = random.Random(seed + 3)
    latest = reports[reports["is_latest"]]
    rows = []
    for rid, pid, date, pidx in zip(
        latest["report_id"],
        latest["patient_id"],
        latest["collected_at"],
        latest["patient_idx"],
        strict=True,
    ):
        p = proms.iloc[pidx]
        sev = int(p["fatigue_severity"])
        style = prng.random()
        fatigue = sev if style < 0.7 else (f"{sev}/10" if style < 0.9 else f"{sev} out of 10")
        answers = {
            "fatigue": fatigue,
            "brain_fog": prng.choice(FOG_SYNONYMS[p["brain_fog_frequency"]]),
            "hair_loss": prng.choice(HAIR_SYNONYMS[p["hair_loss"]]),
        }
        if prng.random() < 0.02:
            answers.pop(prng.choice(list(answers)))
        rows.append(
            {
                "form_id": f"F{rid[1:]}",
                "report_id": rid,
                "patient_id": pid,
                "submitted_at": date,
                "answers": answers,
            }
        )
    out = raw_dir / "intake"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "part-000.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return len(rows)


# ---------------------------------------------------------------------------
# PDFs (four layouts; a share rendered as noisy scanned images)
# ---------------------------------------------------------------------------

TEMPLATES = ("columns", "pipe_table", "colon_inline", "boxed_grid")


def _report_lines(template: str, lab: Lab, meta: dict, rows: list[dict]) -> list[str]:
    head = [
        lab.name,
        f"Patient: {meta['name']}    Age/Sex: {meta['age']} Y / {meta['sex']}",
        f"Collected: {meta['collected_at']}      Report ID: {meta['report_id']}",
        "",
    ]
    body = []
    if template == "columns":
        body.append(f"{'TEST':<32}{'RESULT':<12}{'UNIT':<12}{'REFERENCE':<18}FLAG")
        for r in rows:
            body.append(
                f"{r['label']:<32}{r['value']:<12}{r['unit']:<12}{r['reference']:<18}{r['flag']}"
            )
    elif template == "pipe_table":
        body.append("| Analyte | Result | Units | Reference range |")
        for r in rows:
            body.append(
                f"| {r['label']} | {r['value']} {r['flag']} | {r['unit']} | {r['reference']} |"
            )
    elif template == "colon_inline":
        for r in rows:
            flag = f" [{r['flag']}]" if r["flag"] else ""
            body.append(f"{r['label']}: {r['value']} {r['unit']} (ref {r['reference']}){flag}")
    else:  # boxed_grid: value first then label is NOT supported by labs; keep label-first grid
        body.append(
            f"{'Investigation':<34}{'Observed Value':<18}{'Units':<12}Biological Ref. Interval"
        )
        for r in rows:
            body.append(
                f"{r['label']:<34}{r['value'] + (' ' + r['flag'] if r['flag'] else ''):<18}{r['unit']:<12}{r['reference']}"
            )
    foot = ["", "Results should be interpreted by a qualified clinician.", "-- End of report --"]
    return head + body + foot


def _render_text_pdf(path: Path, lines: list[str], template: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    _, height = A4
    font = "Courier" if template in ("columns", "boxed_grid") else "Helvetica"
    y = height - 60
    for i, line in enumerate(lines):
        c.setFont(font + ("-Bold" if i == 0 else ""), 13 if i == 0 else 9)
        if template == "boxed_grid" and i >= 4 and line.strip():
            c.rect(36, y - 3, 523, 13, stroke=1, fill=0)
        c.drawString(40, y, line)
        y -= 16
    c.showPage()
    c.save()


def _render_scanned_pdf(path: Path, lines: list[str], rng: random.Random) -> None:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    font = ImageFont.truetype("DejaVuSansMono.ttf", 26)
    img = Image.new("L", (2000, 70 + 46 * len(lines)), 255)
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((60, 40 + 46 * i), line, fill=rng.randint(0, 50), font=font)
    img = img.rotate(rng.uniform(-0.8, 0.8), expand=False, fillcolor=255)
    if rng.random() < 0.5:
        img = img.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.3, 0.8)))
    img.convert("RGB").save(path, "PDF", resolution=200.0)


def write_pdfs(
    reports: pd.DataFrame,
    lat: pd.DataFrame,
    raw_dir: Path,
    holdout_dir: Path,
    n_pdfs: int,
    seed: int,
) -> int:
    from faker import Faker

    fake = Faker()
    Faker.seed(seed)
    prng = random.Random(seed + 4)

    out = raw_dir / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    sample = reports.sample(n=min(n_pdfs, len(reports)), random_state=seed)
    truth_path = holdout_dir / "pdf_ground_truth.jsonl"
    with open(truth_path, "w", encoding="utf-8") as fh:
        for k, rep in enumerate(sample.itertuples(index=False)):
            lab = LABS[rep.lab_idx]
            template = TEMPLATES[k % len(TEMPLATES)]
            scanned = prng.random() < 0.35
            sex = lat.at[rep.patient_idx, "sex"]
            rows = []
            for key in BIOMARKER_KEYS:
                if prng.random() > lab.panel_rate.get(key, BASE_PANEL_RATE):
                    continue
                unit = lab.units[key]
                si = getattr(rep, key)
                v = si / load_catalog()[key].units[clean_unit(unit)]
                ref = load_catalog()[key].reference_for(sex)
                rows.append(
                    {
                        "key": key,
                        "label": lab.labels[key],
                        "value": _fmt(v, False),
                        "unit": unit,
                        "reference": _reference_text(key, unit, sex, False),
                        "flag": "H" if si > ref.high else ("L" if si < ref.low else ""),
                        "value_si": float(_fmt(v, False))
                        * load_catalog()[key].units[clean_unit(unit)],
                    }
                )
            meta = {
                "name": fake.name(),
                "age": int(lat.at[rep.patient_idx, "age"]),
                "sex": sex,
                "collected_at": rep.collected_at,
                "report_id": rep.report_id,
            }
            lines = _report_lines(template, lab, meta, rows)
            path = out / f"{rep.report_id}.pdf"
            if scanned:
                _render_scanned_pdf(path, lines, prng)
            else:
                _render_text_pdf(path, lines, template)
            fh.write(
                json.dumps(
                    {
                        "report_id": rep.report_id,
                        "file": path.name,
                        "template": template,
                        "scanned": scanned,
                        "lab_provider": lab.name,
                        "age": meta["age"],
                        "sex": sex,
                        "collected_at": rep.collected_at,
                        "expected_text": "\n".join(lines),
                        "rows": [
                            {
                                k2: r[k2]
                                for k2 in ("key", "label", "value", "unit", "reference", "value_si")
                            }
                            for r in rows
                        ],
                    }
                )
                + "\n"
            )
    return len(sample)


def generate(n_patients: int, n_pdfs: int, seed: int, data_dir: Path) -> dict:
    rng = np.random.default_rng(seed)
    raw_dir = data_dir / "raw"
    holdout_dir = data_dir / "holdout"
    raw_dir.mkdir(parents=True, exist_ok=True)
    holdout_dir.mkdir(parents=True, exist_ok=True)

    lat = _latent(rng, n_patients)
    pmarkers = _markers(rng, lat)
    reports = build_reports(rng, lat, pmarkers)
    latest = reports[reports["is_latest"]].sort_values("patient_idx")
    proms = _proms(rng, latest[list(BIOMARKER_KEYS)].reset_index(drop=True), lat)

    current_year = 2026
    pd.DataFrame(
        {
            "patient_id": lat["patient_id"],
            "sex": lat["sex"],
            "birth_year": current_year - lat["age"],
            "site": [LABS[i].slug for i in rng.choice(len(LABS), size=n_patients, p=LAB_WEIGHTS)],
        }
    ).to_csv(raw_dir / "patients.csv", index=False)

    lab_stats = write_lab_exports(reports, lat, raw_dir, seed)
    n_forms = write_intake(reports, proms, raw_dir, seed)
    n_written = write_pdfs(reports, lat, raw_dir, holdout_dir, n_pdfs, seed) if n_pdfs else 0

    latent_out = lat.copy()
    latent_out[[f"true_{k}" for k in BIOMARKER_KEYS]] = latest[list(BIOMARKER_KEYS)].to_numpy()
    latent_out[["fatigue_severity", "brain_fog_frequency", "hair_loss"]] = proms.to_numpy()
    latent_out.to_parquet(holdout_dir / "latent.parquet", index=False)

    params = dict(GENERATOR_PARAMS, seed=seed, n_patients=n_patients)
    (holdout_dir / "generator_params.json").write_text(
        json.dumps(params, indent=2), encoding="utf-8"
    )
    summary = {
        "seed": seed,
        "patients": n_patients,
        "reports": int(len(reports)),
        "intake_forms": n_forms,
        "pdfs": n_written,
        "lab_rows": lab_stats,
        "phenotype_counts": lat["phenotype"].value_counts().to_dict(),
        "fatigue_ge_7_rate": round(float((proms["fatigue_severity"] >= 7).mean()), 4),
        "fingerprint": hashlib.sha256(
            pd.util.hash_pandas_object(
                latest[list(BIOMARKER_KEYS)].round(6), index=False
            ).values.tobytes()
        ).hexdigest()[:16],
    }
    (data_dir / "raw" / "_generation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    s = get_settings()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--patients", type=int, default=s.n_patients)
    parser.add_argument("--pdfs", type=int, default=s.n_pdfs)
    parser.add_argument("--seed", type=int, default=s.seed)
    parser.add_argument("--data-dir", type=Path, default=s.data_dir)
    args = parser.parse_args()
    summary = generate(args.patients, args.pdfs, args.seed, args.data_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
