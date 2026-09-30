"""Lab-report text -> canonical JSON.

The OCR layer (text layer, Tesseract, PaddleOCR or LayoutLMv3) produces lines of
text, optionally with a per-line confidence. This module turns those lines into
``RawRow`` records (label / value / unit / reference / flag) and extracts report
metadata (age, sex, lab provider, collection date). It deliberately does *not*
extract patient names or identifiers: identity comes from the authenticated
session, never from document content.

Layouts differ between labs (``Name  Value  Unit  Range`` columns, ``Name: value
unit (range)``, pipe tables, trailing H/L flags), so a row is recognised by
trying every numeric token as the value boundary and keeping the split whose
label best matches a catalog alias.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from polymarker_common.catalog import load_catalog
from polymarker_common.normalizer import clean_unit, match_name

_VALUE_TOKEN = re.compile(
    r"(?<![A-Za-z0-9.,\-/])"  # not glued to a word / previous number / unit
    r"(?P<qual>[<>]=?|≤|≥)?\s*"
    r"(?P<num>\d+(?:[.,]\d+)?)"
    r"(?![0-9]|[.,]\d|[A-Za-z]|-[A-Za-z]|\s*-\s*OH\b|\s+OH\b|\s*\(OH\))"
)
_RANGE = re.compile(
    r"(?P<low>\d+(?:[.,]\d+)?)\s*(?:-|–|—|to)\s*(?P<high>\d+(?:[.,]\d+)?)"
    r"|(?P<op>[<>]=?|≤|≥|up to)\s*(?P<bound>\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_FLAG = re.compile(r"(?:^|\s)(H|L|HH|LL|HIGH|LOW|A|\*|↑|↓)(?=\s|$)", re.IGNORECASE)
_SEPARATORS = re.compile(r"[|\t]+|\s{2,}|(?<=[A-Za-z)])\s*:\s+")

_AGE = [
    re.compile(r"\bage\s*(?:/\s*sex)?\s*[:\-]?\s*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,3})\s*(?:y|yr|yrs|years?)\b(?:\s*old)?", re.IGNORECASE),
]
_SEX = [
    re.compile(r"\b(?:sex|gender)\s*[:\-]?\s*(male|female|m|f)\b", re.IGNORECASE),
    re.compile(
        r"\bage\s*/\s*sex\s*[:\-]?\s*\d{1,3}\s*(?:y\w*)?\s*/\s*(m|f|male|female)\b", re.IGNORECASE
    ),
]
_PROVIDER = re.compile(
    r"^\s*(?:laboratory|lab|performing lab|provider|testing site)\s*(?:name)?\s*[:\-]\s*(.+?)\s*$",
    re.IGNORECASE,
)
_PROVIDER_HINT = re.compile(
    r"(laborator|diagnostic|patholog|clinical lab|\blabs?\b)", re.IGNORECASE
)
_DATE = re.compile(
    r"\b(?:collected|collection(?:\s+date)?|sample\s+(?:date|drawn)|specimen\s+date|drawn)"
    r"\s*(?:on|at)?\s*[:\-]?\s*"
    r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
    re.IGNORECASE,
)


@dataclass
class RawRow:
    label: str
    value: str
    qualifier: str | None
    unit: str | None
    reference_text: str | None
    flag: str | None
    line_no: int
    line: str
    marker_key: str
    label_confidence: float
    ocr_confidence: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReportMetadata:
    age: int | None = None
    sex: str | None = None
    lab_provider: str | None = None
    collected_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParsedReport:
    metadata: ReportMetadata
    rows: list[RawRow] = field(default_factory=list)
    unmatched_lines: list[str] = field(default_factory=list)
    line_count: int = 0

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "rows": [r.to_dict() for r in self.rows],
            "unmatched_lines": self.unmatched_lines,
            "line_count": self.line_count,
        }


def _known_units(marker_key: str) -> set[str]:
    return set(load_catalog()[marker_key].units)


def _extract_unit(remainder: str, marker_key: str) -> tuple[str | None, str]:
    """Return (unit, rest_after_unit). Tolerates 'ng / mL' spacing."""
    known = _known_units(marker_key)
    tokens = remainder.strip().split()
    # Some layouts print the H/L flag between the value and the unit ("5.40 H mIU/L").
    skipped: list[str] = []
    while tokens and _FLAG.fullmatch(f" {tokens[0]}") and clean_unit(tokens[0]) not in known:
        skipped.append(tokens.pop(0))
    for width in (3, 2, 1):
        if len(tokens) >= width:
            candidate = "".join(tokens[:width])
            if clean_unit(candidate) in known:
                return candidate, " ".join(skipped + tokens[width:])
    if tokens and re.search(r"[A-Za-zµμ]", tokens[0]) and "/" in tokens[0]:
        # A unit-looking token we do not know: keep it so the normalizer flags it.
        return tokens[0], " ".join(skipped + tokens[1:])
    return None, remainder


def _split_candidates(line: str):
    for match in _VALUE_TOKEN.finditer(line):
        label = line[: match.start()].strip(" :.-–=\t|")
        if not label or not re.search(r"[A-Za-z]", label):
            continue
        yield match, label


def parse_line(line: str, line_no: int = 0, ocr_confidence: float = 1.0) -> RawRow | None:
    text = _SEPARATORS.sub("  ", line.replace(" ", " ")).strip()
    if not text:
        return None
    best = None
    for match, label in _split_candidates(text):
        name = match_name(label)
        if name is None:
            continue
        # Highest label confidence wins; on ties the EARLIEST value wins, so a
        # longer "label" that has swallowed the real value (e.g. "Free T3 4.46
        # pmol/L 3.10") can never beat the true split.
        score = (name.confidence, -match.start())
        if best is None or score > best[0]:
            best = (score, match, label, name)
    if best is None:
        return None
    _, match, label, name = best
    remainder = text[match.end() :]
    unit, rest = _extract_unit(remainder, name.key)
    reference_text = None
    range_match = _RANGE.search(rest)
    if range_match:
        reference_text = range_match.group(0).strip()
        rest = rest[: range_match.start()] + rest[range_match.end() :]
    flag_match = _FLAG.search(rest)
    flag = flag_match.group(1).upper() if flag_match else None
    return RawRow(
        label=label,
        value=match.group("num"),
        qualifier=match.group("qual"),
        unit=unit,
        reference_text=reference_text,
        flag=flag,
        line_no=line_no,
        line=line.strip(),
        marker_key=name.key,
        label_confidence=name.confidence,
        ocr_confidence=ocr_confidence,
    )


def parse_metadata(lines: list[str]) -> ReportMetadata:
    meta = ReportMetadata()
    joined = "\n".join(lines)
    for pattern in _AGE:
        m = pattern.search(joined)
        if m:
            age = int(m.group(1))
            if 0 < age < 120:
                meta.age = age
                break
    for pattern in _SEX:
        m = pattern.search(joined)
        if m:
            meta.sex = m.group(1)[0].upper()
            break
    for line in lines:
        m = _PROVIDER.match(line)
        if m:
            meta.lab_provider = m.group(1)[:120]
            break
    if meta.lab_provider is None:
        for line in lines[:5]:
            stripped = line.strip()
            if stripped and _PROVIDER_HINT.search(stripped) and len(stripped) < 80:
                meta.lab_provider = stripped
                break
    m = _DATE.search(joined)
    if m:
        meta.collected_at = m.group(1)
    return meta


def parse_report_text(
    text: str | list[str],
    line_confidences: list[float] | None = None,
) -> ParsedReport:
    lines = text.splitlines() if isinstance(text, str) else list(text)
    report = ParsedReport(metadata=parse_metadata(lines), line_count=len(lines))
    for i, line in enumerate(lines):
        conf = line_confidences[i] if line_confidences and i < len(line_confidences) else 1.0
        row = parse_line(line, i, conf)
        if row is not None:
            report.rows.append(row)
        elif line.strip():
            report.unmatched_lines.append(line.strip())
    return report
