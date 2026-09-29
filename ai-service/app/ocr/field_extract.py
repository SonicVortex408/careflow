"""
Week 2, Step 2.6: lab metadata extraction -- the brief's explicit list:
patient age, patient sex, lab provider, plus accession/collection dates
(biomarker name/result/unit/reference range come from
table_reconstruct.py's rows, not from here).

Works on the full page text (not individual words), since these
fields are typically a single labelled line rather than a table row.
Every extractor returns (value, confidence) or (None, 0.0) -- never a
guess with a confidence of 1.0 when the match was fuzzy.
"""

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

# "42Y/M", "42 Y / F", "Age: 42", "Age 42Y"
_AGE_SEX_COMBINED_RE = re.compile(r"(\d{1,3})\s*Y(?:ears?)?\s*/\s*([MF])\b", re.IGNORECASE)
_AGE_LABEL_RE = re.compile(r"\bAge\s*:?\s*(\d{1,3})\b", re.IGNORECASE)
_SEX_LABEL_RE = re.compile(r"\b(?:Sex|Gender)\s*:?\s*(Male|Female|M|F)\b", re.IGNORECASE)

_ACCESSION_RE = re.compile(r"\bAccession\s*:?\s*([A-Z0-9-]+)\b", re.IGNORECASE)

_SEX_MAP = {"m": "male", "male": "male", "f": "female", "female": "female"}


@dataclass(frozen=True)
class ExtractedField:
    value: str | None
    confidence: float


def extract_age(text: str) -> ExtractedField:
    combined = _AGE_SEX_COMBINED_RE.search(text)
    if combined:
        return ExtractedField(value=combined.group(1), confidence=0.95)

    labelled = _AGE_LABEL_RE.search(text)
    if labelled:
        return ExtractedField(value=labelled.group(1), confidence=0.9)

    return ExtractedField(value=None, confidence=0.0)


def extract_sex(text: str) -> ExtractedField:
    combined = _AGE_SEX_COMBINED_RE.search(text)
    if combined:
        return ExtractedField(value=_SEX_MAP[combined.group(2).lower()], confidence=0.95)

    labelled = _SEX_LABEL_RE.search(text)
    if labelled:
        return ExtractedField(value=_SEX_MAP[labelled.group(1).lower()], confidence=0.9)

    return ExtractedField(value=None, confidence=0.0)


def extract_accession(text: str) -> ExtractedField:
    match = _ACCESSION_RE.search(text)
    if match:
        return ExtractedField(value=match.group(1), confidence=0.9)
    return ExtractedField(value=None, confidence=0.0)


def extract_lab_provider(text: str, known_providers: list[str]) -> ExtractedField:
    """known_providers: canonical lab provider names (or name variants)
    to fuzzy-match against, e.g. from
    reference/lab_providers.csv (via app/services/reference_data.py).
    Only searches the first ~25% of the text (or first 500 chars),
    matching where a report's letterhead actually appears."""

    if not text or not known_providers:
        return ExtractedField(value=None, confidence=0.0)

    header_region = text[: max(500, len(text) // 4)]

    best_score = 0.0
    best_provider = None
    for provider in known_providers:
        score = fuzz.partial_ratio(provider.lower(), header_region.lower())
        if score > best_score:
            best_score = score
            best_provider = provider

    if best_score >= 90:
        return ExtractedField(value=best_provider, confidence=best_score / 100.0)
    if best_score >= 75:
        return ExtractedField(value=best_provider, confidence=best_score / 100.0)

    return ExtractedField(value=None, confidence=0.0)
