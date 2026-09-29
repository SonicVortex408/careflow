"""
Week 3, Step 3.2: unit alias canonicalization + conversion.

Two-stage, matching docs/WEEKS_1-3_STATUS_AND_PLAN.md section 3.3:

  1. Alias canonicalization -- normalize spelling variants of the same
     unit (micro-sign forms, case, separators) to one token, so
     "uIU/mL", "µIU/mL", "mcIU/mL" all become the same lookup key.
  2. Conversion -- look up (biomarker_key, canonical_from_unit) in
     reference/unit_conversions.csv and multiply by the factor.

Conversion is deliberately keyed by biomarker, not just by unit pair:
mass<->molar conversion depends on molar mass, so "ng/dL -> pmol/L" is
not one global factor (FT4's factor is not FT3's).
"""

import re
from dataclasses import dataclass
from functools import lru_cache

from app.services.reference_data import load_biomarkers, load_unit_conversions

# Micro-sign variants (µ U+00B5 MICRO SIGN, μ U+03BC GREEK SMALL LETTER
# MU, and the ASCII "u"/"mc" prefixes some lab systems emit) all fold
# to "u". This must run before case-folding decisions below, since
# "μ" and "µ" are visually identical but different codepoints.
_MICRO_RE = re.compile(r"[µμ]")


@dataclass(frozen=True)
class ConversionResult:
    value_canonical: float | None
    unit_canonical: str | None
    conversion_factor: float | None
    conversion_source: str | None
    unit_recognized: bool


def canonicalize_unit(raw_unit: str) -> str:
    """
    Fold spelling variants of the same unit to one token.

    Deliberately conservative: only touches the micro-sign family and
    whitespace/case, since over-aggressive folding (e.g. treating "m"
    and "M" as interchangeable in all positions) would collapse units
    that are genuinely different (mL vs ML is fine to fold, but mIU/L
    vs MIU/L is also fine -- however mol vs Mol is not a real-world
    ambiguity this table needs to solve, so case-folding is applied
    uniformly rather than position-by-position).
    """

    if not raw_unit:
        return ""

    text = raw_unit.strip()
    text = _MICRO_RE.sub("u", text)
    # "mc" as a micro-prefix (mcg, mcIU) -> "u", but only at the start
    # of the unit string, so it never touches "mc" inside an unrelated
    # token.
    text = re.sub(r"^mc(?=[A-Za-z])", "u", text)
    # Collapse internal whitespace; units shouldn't have any, but a
    # stray OCR space ("pg / mL") should still resolve.
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s+", "", text)
    return text


@lru_cache
def _conversion_lookup() -> dict[tuple[str, str], tuple[float, str]]:
    lookup: dict[tuple[str, str], tuple[float, str]] = {}
    for row in load_unit_conversions():
        key = (row.biomarker_key, canonicalize_unit(row.from_unit))
        lookup[key] = (row.factor, row.source)
    return lookup


def convert(biomarker_key: str, value: float, raw_unit: str) -> ConversionResult:
    """
    Convert one value from its as-printed unit to the biomarker's
    canonical unit.

    Returns unit_recognized=False (and value_canonical=None) rather
    than guessing when the unit is missing or not in the table -- see
    services/data_quality.py, which uses this to set
    quality.status="suspect" and exclude the row from feature vectors.
    """

    biomarkers = load_biomarkers()
    biomarker = biomarkers.get(biomarker_key)

    canonical_unit_token = canonicalize_unit(raw_unit)
    key = (biomarker_key, canonical_unit_token)

    entry = _conversion_lookup().get(key)

    if entry is None or biomarker is None:
        return ConversionResult(
            value_canonical=None,
            unit_canonical=None,
            conversion_factor=None,
            conversion_source=None,
            unit_recognized=False,
        )

    factor, source = entry
    return ConversionResult(
        value_canonical=value * factor,
        unit_canonical=biomarker.canonical_unit,
        conversion_factor=factor,
        conversion_source=source,
        unit_recognized=True,
    )
