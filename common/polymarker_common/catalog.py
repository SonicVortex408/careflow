"""Biomarker catalog: the single source of truth for the nine target markers.

Every service (ai-service, bda_engine, graph_service seed generation) reads the
catalog from here so LOINC codes, aliases, canonical units and reference
intervals cannot drift between the operational and analytical paths.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from typing import Any

SYNTHETIC_DATA_LABEL = (
    "Derived from synthetic data, for research/demo purposes, not clinical guidance."
)

# Order is significant: it is the column order of every feature vector.
BIOMARKER_KEYS: tuple[str, ...] = (
    "TSH",
    "FT3",
    "FT4",
    "TPOAB",
    "VITD",
    "B12",
    "FERRITIN",
    "MG",
    "ZINC",
)


@dataclass(frozen=True)
class Range:
    low: float
    high: float

    def contains(self, value: float) -> bool:
        return self.low <= value <= self.high


@dataclass(frozen=True)
class EscalationRule:
    op: str
    value: float
    level: str
    reason: str
    evidence_level: str

    def triggered(self, value: float) -> bool:
        if self.op == "<":
            return value < self.value
        if self.op == ">":
            return value > self.value
        raise ValueError(f"Unsupported escalation operator: {self.op}")


@dataclass(frozen=True)
class Biomarker:
    key: str
    loinc: str
    loinc_name: str
    display: str
    long_name: str
    panel: str
    canonical_unit: str
    aliases: tuple[str, ...]
    units: dict[str, float]
    reference: Range
    reference_source: str
    plausible: Range
    escalation: tuple[EscalationRule, ...]
    reference_by_sex: dict[str, Range] = field(default_factory=dict)

    def reference_for(self, sex: str | None = None) -> Range:
        if sex:
            key = sex.strip().upper()[:1]
            if key in self.reference_by_sex:
                return self.reference_by_sex[key]
        return self.reference

    def log_stats(self) -> tuple[float, float]:
        """Mean and standard deviation of log(value) implied by the reference interval.

        A reference interval conventionally covers the central 95% of a healthy
        population, so on a log scale (lab values are right-skewed) the interval
        spans roughly +/-1.96 sd. Used as a population prior when no cohort
        statistics are available.
        """
        low = max(self.reference.low, self.plausible.low, 1e-3)
        high = max(self.reference.high, low * 1.5)
        mean = (math.log(low) + math.log(high)) / 2
        sd = (math.log(high) - math.log(low)) / 3.92
        return mean, sd


@lru_cache(maxsize=1)
def _raw_catalog() -> dict[str, Any]:
    text = (
        resources.files("polymarker_common")
        .joinpath("data/biomarkers.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(text)


def _build(key: str, spec: dict[str, Any]) -> Biomarker:
    return Biomarker(
        key=key,
        loinc=spec["loinc"],
        loinc_name=spec["loinc_name"],
        display=spec["display"],
        long_name=spec["long_name"],
        panel=spec["panel"],
        canonical_unit=spec["canonical_unit"],
        aliases=tuple(spec["aliases"]),
        units=dict(spec["units"]),
        reference=Range(spec["reference"]["low"], spec["reference"]["high"]),
        reference_source=spec["reference"].get("source", ""),
        plausible=Range(spec["plausible"]["low"], spec["plausible"]["high"]),
        escalation=tuple(EscalationRule(**rule) for rule in spec.get("escalation", [])),
        reference_by_sex={
            sex: Range(r["low"], r["high"]) for sex, r in spec.get("reference_by_sex", {}).items()
        },
    )


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Biomarker]:
    raw = _raw_catalog()["biomarkers"]
    catalog = {key: _build(key, raw[key]) for key in BIOMARKER_KEYS}
    missing = set(raw) - set(BIOMARKER_KEYS)
    if missing:
        raise ValueError(f"Catalog contains markers outside BIOMARKER_KEYS: {sorted(missing)}")
    return catalog


def get_biomarker(key: str) -> Biomarker:
    return load_catalog()[key]


def by_loinc(code: str) -> Biomarker | None:
    for marker in load_catalog().values():
        if marker.loinc == code:
            return marker
    return None


def prom_spec() -> dict[str, Any]:
    return _raw_catalog()["proms"]


def catalog_version() -> str:
    return _raw_catalog()["_meta"]["version"]


def catalog_as_dict() -> dict[str, Any]:
    """JSON-serialisable view of the catalog for API responses and the UI."""
    out: dict[str, Any] = {}
    for key, m in load_catalog().items():
        out[key] = {
            "key": key,
            "loinc": m.loinc,
            "display": m.display,
            "long_name": m.long_name,
            "panel": m.panel,
            "canonical_unit": m.canonical_unit,
            "reference": {"low": m.reference.low, "high": m.reference.high},
            "reference_by_sex": {
                s: {"low": r.low, "high": r.high} for s, r in m.reference_by_sex.items()
            },
            "reference_source": m.reference_source,
        }
    return out
