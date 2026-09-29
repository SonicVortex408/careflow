"""
Week 3, Step 3.3: reference-range string parsing.

Parses the free-text reference range as printed on a lab report into
(ref_low, ref_high, ref_operator). Handles, in priority order: a
sex-stratified range ("Male: 13-150 Female: 12-100"), a bounded range
("0.4 - 4.0", en/em dash, "to"), and an open-ended bound ("<4.0",
">150", "up to 4.0"). A labelled prefix ("Normal:", "Reference range:")
is stripped first.

Deliberately does NOT attempt to parse banded qualitative text (e.g.
"Deficient/Insufficient/Sufficient" for vitamin D) into numeric
cutpoints: those cutpoints vary by guideline body and are not
something this project has a citable source for per biomarker. Banded
text is reported as unparsed (parsed=False) rather than guessed --
same principle as normalizer.py's "never guess" floor.
"""

import re
from dataclasses import dataclass

from app.services.common_types import Comparator

_PREFIX_RE = re.compile(
    r"^\s*(normal|reference\s*range|ref\.?\s*range|reference\s*interval|ref\.?\s*interval)\s*:\s*",
    re.IGNORECASE,
)

_SEX_STRATIFIED_RE = re.compile(
    r"(male|female|men|women)\s*:?\s*"
    r"([\d.]+)\s*(?:-|–|—|to)\s*([\d.]+)",
    re.IGNORECASE,
)

_BOUNDED_RANGE_RE = re.compile(
    r"^\s*([\d.]+)\s*(?:-|–|—|to)\s*([\d.]+)\s*$",
    re.IGNORECASE,
)

_UPPER_BOUND_RE = re.compile(
    r"^\s*(?:[<≤]|up\s*to)\s*([\d.]+)\s*$",
    re.IGNORECASE,
)

_LOWER_BOUND_RE = re.compile(
    r"^\s*(?:[>≥]|(?:greater|more)\s*than)\s*([\d.]+)\s*$",
    re.IGNORECASE,
)

_SEX_ALIASES = {
    "male": "male", "men": "male",
    "female": "female", "women": "female",
}


@dataclass(frozen=True)
class RefRangeResult:
    ref_low: float | None
    ref_high: float | None
    ref_operator: Comparator
    parsed: bool
    matched_segment: str | None  # which sex-stratified segment was used, if any


def _strip_prefix(text: str) -> str:
    return _PREFIX_RE.sub("", text.strip())


def parse_reference_range(raw: str, patient_sex: str | None = None) -> RefRangeResult:
    if not raw or not raw.strip():
        return RefRangeResult(None, None, Comparator.NONE, False, None)

    text = _strip_prefix(raw)

    # Sex-stratified: "Male: 13-150 Female: 12-100". Find all
    # sex-labelled segments; if the patient's sex is known and present,
    # use that segment. Otherwise fall through to the generic bounded-
    # range attempt (which will fail on this multi-segment string and
    # correctly report parsed=False rather than guess a sex).
    sex_matches = list(_SEX_STRATIFIED_RE.finditer(text))
    if sex_matches:
        normalized_sex = _SEX_ALIASES.get((patient_sex or "").strip().lower())
        if normalized_sex:
            for match in sex_matches:
                label = _SEX_ALIASES.get(match.group(1).lower())
                if label == normalized_sex:
                    low, high = float(match.group(2)), float(match.group(3))
                    return RefRangeResult(
                        ref_low=min(low, high),
                        ref_high=max(low, high),
                        ref_operator=Comparator.NONE,
                        parsed=True,
                        matched_segment=match.group(0),
                    )
        # Sex unknown or not found among the labelled segments: do not
        # guess which one applies.
        return RefRangeResult(None, None, Comparator.NONE, False, None)

    bounded = _BOUNDED_RANGE_RE.match(text)
    if bounded:
        low, high = float(bounded.group(1)), float(bounded.group(2))
        return RefRangeResult(
            ref_low=min(low, high),
            ref_high=max(low, high),
            ref_operator=Comparator.NONE,
            parsed=True,
            matched_segment=None,
        )

    upper = _UPPER_BOUND_RE.match(text)
    if upper:
        return RefRangeResult(
            ref_low=None,
            ref_high=float(upper.group(1)),
            ref_operator=Comparator.LT,
            parsed=True,
            matched_segment=None,
        )

    lower = _LOWER_BOUND_RE.match(text)
    if lower:
        return RefRangeResult(
            ref_low=float(lower.group(1)),
            ref_high=None,
            ref_operator=Comparator.GT,
            parsed=True,
            matched_segment=None,
        )

    # Banded qualitative text, or a format this parser does not know --
    # report unparsed rather than guess.
    return RefRangeResult(None, None, Comparator.NONE, False, None)
