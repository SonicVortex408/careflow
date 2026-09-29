"""
Week 3, Step 3.1: analyte name -> LOINC-coded biomarker mapping.

A deterministic cascade, cheapest and most certain stage first. Each
stage records how the match was found (`mapping_method`) and a
confidence; the first stage that hits wins:

  1. exact    -- lightly-canonicalized input equals a known variant
  2. synonym  -- fully-canonicalized (stopwords/abbreviations
                 normalized) input equals a known variant
  3. synonym  -- same, after a deterministic OCR word-split repair
                 (token-join) -- handles "Free T 3" -> "free t3"
  4. fuzzy    -- rapidfuzz similarity against every known variant,
                 order-insensitive and space-insensitive -- handles
                 "Tr iodothyronine Free" -> "free t3" (a dropped
                 letter *and* a bad word split)
  5. unmapped -- below the fuzzy floor; never guess

See tests/test_normalizer.py for the adversarial cases this is built
against (they are the acceptance criteria from
docs/WEEKS_1-3_STATUS_AND_PLAN.md section 3.3).
"""

from dataclasses import dataclass
from functools import lru_cache

from rapidfuzz import fuzz

from app.services.reference_data import load_biomarkers, load_synonyms
from app.services.text_normalize import (
    canonicalize,
    canonicalize_full,
    strip_spaces,
    token_join_candidates,
)

# Score thresholds for the fuzzy stage (0-100, rapidfuzz's native scale).
FUZZY_ACCEPT_THRESHOLD = 92.0
FUZZY_REVIEW_THRESHOLD = 80.0


@dataclass(frozen=True)
class MappingResult:
    biomarker_key: str | None
    loinc_code: str | None
    loinc_long_name: str | None
    mapping_method: str  # exact | synonym | fuzzy | unmapped
    mapping_confidence: float  # 0.0-1.0
    needs_review: bool
    matched_variant: str | None  # what it matched against, for debugging/audit


@dataclass(frozen=True)
class _CorpusEntry:
    biomarker_key: str
    light: str
    full: str
    full_stripped: str


@lru_cache
def _light_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in load_synonyms():
        key = canonicalize(row.variant)
        lookup.setdefault(key, row.biomarker_key)
    # Every biomarker also matches its own key literally (e.g. "FT3").
    for biomarker_key in load_biomarkers():
        lookup.setdefault(canonicalize(biomarker_key), biomarker_key)
    return lookup


@lru_cache
def _full_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in load_synonyms():
        key = canonicalize_full(row.variant)
        lookup.setdefault(key, row.biomarker_key)
    for biomarker_key in load_biomarkers():
        lookup.setdefault(canonicalize_full(biomarker_key), biomarker_key)
    return lookup


@lru_cache
def _fuzzy_corpus() -> tuple[_CorpusEntry, ...]:
    entries = []
    seen = set()
    for row in load_synonyms():
        full = canonicalize_full(row.variant)
        dedupe_key = (row.biomarker_key, full)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        entries.append(
            _CorpusEntry(
                biomarker_key=row.biomarker_key,
                light=canonicalize(row.variant),
                full=full,
                full_stripped=strip_spaces(full),
            )
        )
    return tuple(entries)


def _fuzzy_match(full_canonical: str) -> tuple[str | None, float, str | None]:
    """Returns (biomarker_key_or_None, best_score_0_to_100, matched_variant)."""

    stripped = strip_spaces(full_canonical)

    best_score = 0.0
    best_key = None
    best_variant = None

    for entry in _fuzzy_corpus():
        # token_set_ratio: order-insensitive, tolerant of extra/missing
        # words (catches "free t3" vs "t3 free" and near-variants).
        score_tokens = fuzz.token_set_ratio(full_canonical, entry.full)
        # plain ratio on space-stripped forms: tolerant of a stray
        # space landing in the middle of a word from bad OCR
        # segmentation ("triodothyroninefree" vs "triiodothyroninefree")
        # -- a case token_set_ratio alone does not handle well, because
        # splitting mid-word does not produce a token the corpus knows.
        score_stripped = fuzz.ratio(stripped, entry.full_stripped)

        score = max(score_tokens, score_stripped)

        if score > best_score:
            best_score = score
            best_key = entry.biomarker_key
            best_variant = entry.full

    return best_key, best_score, best_variant


def map_analyte_name(raw: str) -> MappingResult:
    """Map one raw, as-printed analyte name string to a biomarker."""

    biomarkers = load_biomarkers()

    def _result(biomarker_key, method, confidence, needs_review, matched_variant):
        ref = biomarkers.get(biomarker_key) if biomarker_key else None
        return MappingResult(
            biomarker_key=biomarker_key,
            loinc_code=ref.loinc_code if ref else None,
            loinc_long_name=ref.loinc_long_name if ref else None,
            mapping_method=method,
            mapping_confidence=confidence,
            needs_review=needs_review,
            matched_variant=matched_variant,
        )

    if not raw or not raw.strip():
        return _result(None, "unmapped", 0.0, True, None)

    # Stage 1: exact (lightly canonicalized).
    light = canonicalize(raw)
    if light in _light_lookup():
        return _result(_light_lookup()[light], "exact", 1.0, False, light)

    # Stage 2: synonym (fully canonicalized).
    full = canonicalize_full(raw)
    if full in _full_lookup():
        return _result(_full_lookup()[full], "synonym", 0.95, False, full)

    # Stage 3: synonym via deterministic OCR word-split repair.
    for candidate in token_join_candidates(full):
        if candidate in _full_lookup():
            return _result(_full_lookup()[candidate], "synonym", 0.9, False, candidate)

    # Stage 4: fuzzy.
    best_key, best_score, best_variant = _fuzzy_match(full)

    if best_score >= FUZZY_ACCEPT_THRESHOLD:
        return _result(best_key, "fuzzy", best_score / 100.0, False, best_variant)

    if best_score >= FUZZY_REVIEW_THRESHOLD:
        return _result(best_key, "fuzzy", best_score / 100.0, True, best_variant)

    # Stage 5: never guess below the floor.
    return _result(None, "unmapped", 0.0, True, None)
