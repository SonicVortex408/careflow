"""
Week 2, Step 2.4: table reconstruction.

Turns a flat list of Word objects (from either text_layer.py or an OCR
engine) into row candidates: {analyte_name_raw, value_raw, unit_raw,
reference_range_raw, bbox, confidence}. Works identically regardless
of which engine produced the words (see app/ocr/common.py).

Method: cluster words into visual lines by y-overlap (this handles
every render_pdf.py layout -- single-column running text, table cells,
and multi-panel headers all place one logical row's words on one
line), then classify tokens within a line left-to-right:

  1. the first token that is a PURE number (optionally prefixed with a
     comparator) is the value -- e.g. "20.7", "<0.01". A token that
     mixes letters and digits ("T3", "B12", "25(OH)") does not match,
     so it's never mistaken for the value.
  2. the token immediately after the value, IF its canonicalized form
     is a known unit (checked against reference/unit_conversions.csv's
     from_unit set), is the unit.
  3. everything before the value is the analyte name.
  4. everything after the unit is tried as a reference range (via
     services/ref_range.py); kept as reference_range_raw whether or
     not it actually parses -- parsing happens downstream, in the
     normalizer, not here.
  5. a line with no numeric token (a panel header, a page title) is
     not a data row and is skipped.
"""

import re
from dataclasses import dataclass

from app.ocr.common import Word
from app.services.units import canonicalize_unit

_VALUE_TOKEN_RE = re.compile(r"^[<>≤≥]?\d+\.?\d*$")


@dataclass(frozen=True)
class RowCandidate:
    page_no: int
    row_index: int
    analyte_name_raw: str
    value_raw: str
    unit_raw: str | None
    reference_range_raw: str | None
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1
    confidence: float  # mean word confidence across the line


def group_words_into_lines(words: list[Word]) -> list[list[Word]]:
    """Cluster words into visual lines by y-center overlap, then sort
    each line left-to-right. Words are assumed to already be from a
    single page (callers iterate PageWords.words per page)."""

    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (w.y0 + w.y1) / 2)

    lines: list[list[Word]] = []
    for word in sorted_words:
        y_center = (word.y0 + word.y1) / 2
        placed = False
        for line in lines:
            line_y_center = sum((w.y0 + w.y1) / 2 for w in line) / len(line)
            line_height = max(w.y1 - w.y0 for w in line)
            if abs(y_center - line_y_center) <= line_height * 0.6:
                line.append(word)
                placed = True
                break
        if not placed:
            lines.append([word])

    for line in lines:
        line.sort(key=lambda w: w.x0)

    lines.sort(key=lambda line: min(w.y0 for w in line))
    return lines


# A horizontal gap wider than this (in PDF points) between two
# adjacent words' x-ranges, present consistently down the page,
# indicates two side-by-side columns rather than one wide line -- e.g.
# render_pdf.py's two_column layout, where a left-column row and a
# right-column row land on the SAME y-position and would otherwise be
# merged into one nonsense line by group_words_into_lines alone.
MIN_COLUMN_GAP = 60.0


def detect_column_bands(words: list[Word]) -> list[tuple[float, float]]:
    """Returns a list of (x_min, x_max) bands. Finds gaps in the
    horizontal extent of all words on a page; a gap wider than
    MIN_COLUMN_GAP splits the page into separate column bands. Single-
    column layouts (the common case) return one band covering
    everything -- this function only changes behavior when there's
    real evidence of side-by-side columns."""

    if not words:
        return []

    # Build the union of x-intervals words occupy, merging overlaps,
    # to find genuine full-height gaps rather than being thrown off by
    # a single short word.
    intervals = sorted((w.x0, w.x1) for w in words)
    merged = [intervals[0]]
    for x0, x1 in intervals[1:]:
        last_x0, last_x1 = merged[-1]
        if x0 - last_x1 <= MIN_COLUMN_GAP:
            merged[-1] = (last_x0, max(last_x1, x1))
        else:
            merged.append((x0, x1))

    return merged


def _band_for_word(word: Word, bands: list[tuple[float, float]]) -> int:
    center = (word.x0 + word.x1) / 2
    for i, (band_x0, band_x1) in enumerate(bands):
        if band_x0 - 1 <= center <= band_x1 + 1:
            return i
    # Shouldn't happen (bands are built from the words themselves), but
    # fall back to the nearest band rather than crashing.
    return min(range(len(bands)), key=lambda i: abs(center - (bands[i][0] + bands[i][1]) / 2))


def _known_units() -> set[str]:
    from app.services.reference_data import load_unit_conversions

    return {canonicalize_unit(row.from_unit) for row in load_unit_conversions()}


def parse_line_to_row(line: list[Word], known_units: set[str]) -> RowCandidate | None:
    if not line:
        return None

    value_index = next(
        (i for i, w in enumerate(line) if _VALUE_TOKEN_RE.match(w.text)), None
    )
    if value_index is None:
        return None  # not a data row (header, panel title, ...)

    analyte_tokens = line[:value_index]
    if not analyte_tokens:
        return None  # a bare number with no label isn't a usable row

    value_word = line[value_index]
    remainder = line[value_index + 1:]

    unit_word = None
    if remainder and canonicalize_unit(remainder[0].text) in known_units:
        unit_word = remainder[0]
        remainder = remainder[1:]

    range_text = " ".join(w.text for w in remainder).strip() or None

    all_line_words = analyte_tokens + [value_word] + ([unit_word] if unit_word else []) + remainder
    x0 = min(w.x0 for w in all_line_words)
    y0 = min(w.y0 for w in all_line_words)
    x1 = max(w.x1 for w in all_line_words)
    y1 = max(w.y1 for w in all_line_words)
    mean_confidence = sum(w.confidence for w in all_line_words) / len(all_line_words)

    return RowCandidate(
        page_no=line[0].page_no,
        row_index=0,  # assigned by the caller across the whole document
        analyte_name_raw=" ".join(w.text for w in analyte_tokens),
        value_raw=value_word.text,
        unit_raw=unit_word.text if unit_word else None,
        reference_range_raw=range_text,
        bbox=(x0, y0, x1, y1),
        confidence=mean_confidence,
    )


def reconstruct_rows(pages, known_units: set[str] | None = None) -> list[RowCandidate]:
    """pages: an iterable of PageWords (app/ocr/common.py)."""

    known_units = known_units if known_units is not None else _known_units()

    rows = []
    row_index = 0
    for page in pages:
        page_words = list(page.words)
        bands = detect_column_bands(page_words)

        # Process each column band independently -- see MIN_COLUMN_GAP's
        # docstring. A single-column page yields exactly one band
        # covering the whole width, so this is a no-op there.
        band_words: list[list[Word]] = [[] for _ in bands]
        for word in page_words:
            band_words[_band_for_word(word, bands)].append(word)

        for one_band_words in band_words:
            lines = group_words_into_lines(one_band_words)
            for line in lines:
                candidate = parse_line_to_row(line, known_units)
                if candidate is not None:
                    rows.append(
                        RowCandidate(
                            page_no=candidate.page_no,
                            row_index=row_index,
                            analyte_name_raw=candidate.analyte_name_raw,
                            value_raw=candidate.value_raw,
                            unit_raw=candidate.unit_raw,
                            reference_range_raw=candidate.reference_range_raw,
                            bbox=candidate.bbox,
                            confidence=candidate.confidence,
                        )
                    )
                    row_index += 1
    return rows
