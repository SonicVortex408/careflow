"""
Text canonicalization for analyte-name matching (Week 3, Step 3.1).

This is the shared normalization every stage of the mapping cascade in
normalizer.py runs both the raw OCR string AND every reference/
analyte_synonyms.csv variant through, so the two sides are always
compared on equal footing. Keeping this in one function is what makes
the cascade's stages consistent -- if input and corpus were normalized
differently, "the same" analyte could fail to match itself.
"""

import re

_PUNCTUATION_RE = re.compile(r"[.,;:()\[\]/\\_+-]")
_WHITESPACE_RE = re.compile(r"\s+")

# Matrix/qualifier words that appear on lab reports but carry no
# analyte-identifying information -- dropped after tokenizing.
_STOPWORDS = {
    "serum", "plasma", "level", "levels", "total", "test", "quant",
    "quantitative", "s", "lab", "value", "result",
}

# Token-level abbreviation expansion. Applied to *both* the input and
# the reference corpus at lookup-table build time, so it only needs to
# be correct once. Keys and values are already lowercased tokens.
_ABBREVIATIONS = {
    "vit": "vitamin",
    "ab": "antibody",
    "abs": "antibody",
}


def canonicalize(raw: str) -> str:
    """
    Lowercase, strip punctuation to spaces, collapse whitespace.

    Deliberately does NOT drop stopwords or expand abbreviations --
    that's canonicalize_full()'s job. This lighter form is used for the
    "exact" match stage, which is meant to catch a raw string that is
    already (almost) exactly a known variant, before any lossy
    normalization is applied.
    """

    text = raw.strip().lower()
    text = _PUNCTUATION_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def tokenize(canonical: str) -> list[str]:
    return canonical.split(" ") if canonical else []


def canonicalize_full(raw: str) -> str:
    """
    canonicalize() plus stopword removal and abbreviation expansion.
    Used for the "synonym" match stage and as the basis for fuzzy
    matching.
    """

    tokens = tokenize(canonicalize(raw))
    tokens = [_ABBREVIATIONS.get(t, t) for t in tokens]
    tokens = [t for t in tokens if t and t not in _STOPWORDS]
    return " ".join(tokens)


def token_join_candidates(canonical: str) -> list[str]:
    """
    Generate repair candidates for OCR word-splitting, e.g.
    "Tr iodothyronine Free" or "Free T 3" -- a real token got broken
    into two by a stray space. For each adjacent pair of tokens, try
    merging them into one and return the resulting string (token
    count - 1 each), one candidate per adjacent pair, plus a single
    candidate with every space removed.

    This is deliberately separate from fuzzy matching: a token-join
    candidate is retried as an *exact* lookup (normalizer.py stage 3)
    before any approximate scoring happens, because a full-string
    fuzzy comparison after a wrong split would be no closer to the
    truth than the original.
    """

    tokens = tokenize(canonical)
    if len(tokens) < 2:
        return []

    candidates = []
    for i in range(len(tokens) - 1):
        merged = tokens[: i] + [tokens[i] + tokens[i + 1]] + tokens[i + 2:]
        candidates.append(" ".join(merged))

    candidates.append("".join(tokens))  # fully joined, no spaces at all

    return candidates


def strip_spaces(canonical: str) -> str:
    return canonical.replace(" ", "")
