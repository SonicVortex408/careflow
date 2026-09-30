"""Entity + unit normalization: raw lab strings -> LOINC-coded, SI-unit values.

Two steps, each carrying a confidence so that downstream quality checks and the
clinician review screen can see *why* a value is trusted or not:

1. ``match_name`` maps a lab-specific label ("FT3", "Triiodothyronine, Free",
   "25-OH Vit D") onto one of the nine catalog keys / LOINC codes.
2. ``convert_to_canonical`` converts the numeric result into the canonical SI
   unit (e.g. ng/dL -> pmol/L for free T4). A missing or unrecognised unit is
   *inferred* from the plausible range and flagged with lower confidence
   rather than silently assumed.
"""

from __future__ import annotations

import difflib
import math
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache

from polymarker_common.catalog import Biomarker, load_catalog

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_FUZZY_CUTOFF = 0.84


def _clean_label(text: str) -> str:
    text = text.lower().replace("µ", "u").replace("μ", "u")
    text = text.replace("(", " ").replace(")", " ")
    text = _NON_ALNUM.sub(" ", text)
    return " ".join(text.split())


@lru_cache(maxsize=1)
def _alias_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for key, marker in load_catalog().items():
        for alias in (*marker.aliases, marker.display, marker.long_name):
            index[_clean_label(alias)] = key
    return index


@dataclass(frozen=True)
class NameMatch:
    key: str
    loinc: str
    confidence: float
    method: str  # exact | contains | fuzzy


def match_name(raw_label: str) -> NameMatch | None:
    """Map a raw lab label onto a catalog key, or None if it is not one of ours."""
    label = _clean_label(raw_label)
    if not label:
        return None
    index = _alias_index()
    catalog = load_catalog()

    if label in index:
        key = index[label]
        return NameMatch(key, catalog[key].loinc, 1.0, "exact")

    # Labels often carry qualifiers ("Vitamin B12, serum (CLIA)"). Accept the
    # longest alias that appears as a whole-word prefix of the label.
    best: tuple[int, str] | None = None
    padded = f" {label} "
    for alias, key in index.items():
        if len(alias) < 3:
            continue
        if padded.startswith(f" {alias} "):
            if best is None or len(alias) > best[0]:
                best = (len(alias), key)
    if best is not None:
        key = best[1]
        return NameMatch(key, catalog[key].loinc, 0.95, "contains")

    close = difflib.get_close_matches(label, list(index), n=1, cutoff=_FUZZY_CUTOFF)
    if close:
        key = index[close[0]]
        ratio = difflib.SequenceMatcher(None, label, close[0]).ratio()
        return NameMatch(key, catalog[key].loinc, round(0.9 * ratio, 3), "fuzzy")
    return None


def clean_unit(raw_unit: str | None) -> str:
    if not raw_unit:
        return ""
    unit = raw_unit.strip().lower()
    unit = unit.replace("µ", "u").replace("μ", "u").replace("mcg", "ug").replace("mμ", "mu")
    unit = unit.replace(" ", "").replace("per", "/")
    unit = unit.replace("litre", "l").replace("liter", "l")
    unit = unit.rstrip(".")
    return unit


_VALUE_RE = re.compile(r"^\s*([<>]=?|≤|≥)?\s*(-?\d+(?:[.,]\d+)?)\s*$")


def parse_value(raw: str | float | int) -> tuple[float, str | None]:
    """Parse "4.2", "4,2", "<0.5" -> (value, qualifier). Raises ValueError."""
    if isinstance(raw, (int, float)):
        if isinstance(raw, float) and math.isnan(raw):
            raise ValueError("NaN value")
        return float(raw), None
    match = _VALUE_RE.match(str(raw))
    if not match:
        raise ValueError(f"Unparseable value: {raw!r}")
    qualifier = match.group(1)
    if qualifier == "≤":
        qualifier = "<="
    elif qualifier == "≥":
        qualifier = ">="
    return float(match.group(2).replace(",", ".")), qualifier


@dataclass(frozen=True)
class Conversion:
    value: float
    unit: str
    factor: float
    source_unit: str
    confidence: float
    inferred: bool


def _log_distance_to_reference(marker: Biomarker, value: float) -> float:
    ref = marker.reference
    low = max(ref.low, marker.plausible.low, 1e-3)
    if low <= value <= ref.high:
        return 0.0
    target = low if value < low else ref.high
    return abs(math.log(max(value, 1e-6)) - math.log(target))


def convert_to_canonical(marker: Biomarker, value: float, raw_unit: str | None) -> Conversion:
    unit = clean_unit(raw_unit)
    if unit in marker.units:
        factor = marker.units[unit]
        return Conversion(
            value=value * factor,
            unit=marker.canonical_unit,
            factor=factor,
            source_unit=raw_unit or "",
            confidence=1.0,
            inferred=False,
        )

    # Unknown or missing unit: pick the known unit that yields a plausible value
    # closest to the reference interval. Always flagged as inferred.
    candidates = []
    for candidate_unit, factor in marker.units.items():
        converted = value * factor
        if marker.plausible.contains(converted):
            candidates.append(
                (_log_distance_to_reference(marker, converted), candidate_unit, factor)
            )
    if not candidates:
        return Conversion(
            value=value,
            unit=marker.canonical_unit,
            factor=1.0,
            source_unit=raw_unit or "",
            confidence=0.2,
            inferred=True,
        )
    candidates.sort()
    _, best_unit, factor = candidates[0]
    # Ambiguity lowers confidence: several units giving in-reference values.
    ambiguous = sum(1 for d, _, _ in candidates if d == 0.0) > 1
    return Conversion(
        value=value * factor,
        unit=marker.canonical_unit,
        factor=factor,
        source_unit=best_unit,
        confidence=0.45 if ambiguous else 0.6,
        inferred=True,
    )


@dataclass
class NormalizedResult:
    key: str
    loinc: str
    display: str
    value: float
    unit: str
    raw_label: str
    raw_value: str
    raw_unit: str
    qualifier: str | None
    name_confidence: float
    unit_confidence: float
    ocr_confidence: float
    unit_inferred: bool
    reference_low: float
    reference_high: float
    lab_reference: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return round(self.name_confidence * self.unit_confidence * self.ocr_confidence, 3)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["confidence"] = self.confidence
        return data


def normalize_result(
    raw_label: str,
    raw_value: str | float,
    raw_unit: str | None = None,
    *,
    sex: str | None = None,
    ocr_confidence: float = 1.0,
    lab_reference: str | None = None,
) -> NormalizedResult | None:
    """Normalise one raw lab row. Returns None when the label is not a target marker."""
    match = match_name(raw_label)
    if match is None:
        return None
    marker = load_catalog()[match.key]
    value, qualifier = parse_value(raw_value)
    conversion = convert_to_canonical(marker, value, raw_unit)
    reference = marker.reference_for(sex)
    notes: list[str] = []
    if conversion.inferred:
        notes.append(
            f"Unit '{raw_unit or 'missing'}' not recognised; assumed {conversion.source_unit or 'canonical'}"
        )
    if match.method == "fuzzy":
        notes.append(f"Label '{raw_label}' matched approximately to {marker.display}")
    return NormalizedResult(
        key=match.key,
        loinc=match.loinc,
        display=marker.display,
        value=round(conversion.value, 4),
        unit=conversion.unit,
        raw_label=raw_label,
        raw_value=str(raw_value),
        raw_unit=raw_unit or "",
        qualifier=qualifier,
        name_confidence=match.confidence,
        unit_confidence=conversion.confidence,
        ocr_confidence=max(0.0, min(1.0, ocr_confidence)),
        unit_inferred=conversion.inferred,
        reference_low=reference.low,
        reference_high=reference.high,
        lab_reference=lab_reference,
        notes=notes,
    )


def to_canonical_value(key: str, value: float, raw_unit: str | None) -> float:
    """Vectorisable helper used by the ETL: convert a single value, NaN if impossible."""
    marker = load_catalog()[key]
    conversion = convert_to_canonical(marker, value, raw_unit)
    return conversion.value if conversion.confidence > 0.2 else float("nan")
