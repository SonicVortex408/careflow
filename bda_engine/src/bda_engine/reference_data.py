"""
Loaders for the reference/ data files: biomarkers.yaml,
analyte_synonyms.csv, unit_conversions.csv, lab_providers.csv.

This is the single place that knows the on-disk shape of reference/, so
both the synthetic generator (bda_engine) and the normalizer
(ai-service, which reads these same files -- see
ai-service/app/services/normalizer.py) can share it without duplicating
parsing logic. ai-service does not depend on bda_engine as a package
(kept as a separate uv project per ARCHITECTURE.md decision 4), so its
normalizer re-implements a thin loader against the same files; this
module is bda_engine's own copy, used by the generator and by this
package's tests.
"""

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

# reference/ lives at the repo root (sibling to ai-service/, backend/,
# bda_engine/), not inside bda_engine/, so it can be shared as plain
# data: both this generator package and ai-service's Week 3 normalizer
# (app/services/reference_data.py, a separate tiny loader, not an
# import of this module) read the same LOINC codes, conversion
# factors, and synonym tables without ai-service taking a Python
# dependency on bda_engine's heavier deps (pandas, faker, reportlab,
# duckdb, the pyspark extra) -- see ARCHITECTURE.md decision 4.
# bda_engine/src/bda_engine/reference_data.py -> repo root is 3 levels up.
REFERENCE_DIR = Path(__file__).resolve().parents[3] / "reference"


@dataclass(frozen=True)
class BiomarkerRef:
    key: str
    loinc_code: str
    loinc_long_name: str
    canonical_unit: str
    molar_mass_g_mol: float | None
    plausible_min: float
    plausible_max: float
    default_ref_low: float
    default_ref_high: float
    source: str


@dataclass(frozen=True)
class SynonymRow:
    biomarker_key: str
    variant: str
    source: str


@dataclass(frozen=True)
class ConversionRow:
    biomarker_key: str
    from_unit: str
    to_unit: str
    factor: float
    source: str


@dataclass(frozen=True)
class LabProviderRow:
    provider_id: str
    canonical_name: str
    name_variant: str
    source: str


@lru_cache
def load_biomarkers(path: Path | None = None) -> dict[str, BiomarkerRef]:
    path = path or (REFERENCE_DIR / "biomarkers.yaml")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    result = {}
    for key, entry in raw.items():
        result[key] = BiomarkerRef(
            key=key,
            loinc_code=entry["loinc_code"],
            loinc_long_name=entry["loinc_long_name"],
            canonical_unit=entry["canonical_unit"],
            molar_mass_g_mol=entry.get("molar_mass_g_mol"),
            plausible_min=entry["plausible_min"],
            plausible_max=entry["plausible_max"],
            default_ref_low=entry["default_ref_low"],
            default_ref_high=entry["default_ref_high"],
            source=entry["source"],
        )
    return result


@lru_cache
def load_synonyms(path: Path | None = None) -> tuple[SynonymRow, ...]:
    path = path or (REFERENCE_DIR / "analyte_synonyms.csv")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return tuple(
            SynonymRow(
                biomarker_key=row["biomarker_key"],
                variant=row["variant"],
                source=row["source"],
            )
            for row in reader
        )


@lru_cache
def load_unit_conversions(path: Path | None = None) -> tuple[ConversionRow, ...]:
    path = path or (REFERENCE_DIR / "unit_conversions.csv")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return tuple(
            ConversionRow(
                biomarker_key=row["biomarker_key"],
                from_unit=row["from_unit"],
                to_unit=row["to_unit"],
                factor=float(row["factor"]),
                source=row["source"],
            )
            for row in reader
        )


@lru_cache
def load_lab_providers(path: Path | None = None) -> tuple[LabProviderRow, ...]:
    path = path or (REFERENCE_DIR / "lab_providers.csv")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return tuple(
            LabProviderRow(
                provider_id=row["provider_id"],
                canonical_name=row["canonical_name"],
                name_variant=row["name_variant"],
                source=row["source"],
            )
            for row in reader
        )
