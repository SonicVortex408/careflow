"""Statistical data-quality and anomaly checks for one ingested report.

Checks (all deterministic, each recorded in the audit list whether it fires or not):

- ``implausible``      value outside assay/physiological limits -> error, value dropped
- ``decimal_misread``  value x10/x100 off from a plausible, in-reference value (OCR
                       lost or added a decimal point) -> warning
- ``unit_inferred``    unit missing/unknown and inferred -> warning
- ``low_confidence``   combined OCR x name x unit confidence below threshold -> warning
- ``duplicate``        marker reported more than once -> info (same) / warning (conflict)
- ``zscore_outlier``   |z| on log scale above threshold vs population statistics -> warning
- ``iqr_outlier``      outside Tukey fences (k=3) on log scale -> warning
- ``lab_flag_mismatch``lab H/L flag disagrees with the lab's own printed range -> info
- ``completeness``     share of the nine target markers present

Population statistics come from the bda_engine artifact (``population_stats.json``);
without them the catalog reference interval is used as a log-normal prior.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from polymarker_common.catalog import BIOMARKER_KEYS, load_catalog
from polymarker_common.normalizer import NormalizedResult

LOW_CONFIDENCE_THRESHOLD = 0.75
Z_THRESHOLD = 4.0
IQR_K = 3.0

_RANGE_NUMS = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:[.,]\d+)?)")


@dataclass
class QualityIssue:
    code: str
    severity: str  # info | warning | error
    marker: str | None
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QualityReport:
    accepted: list[NormalizedResult]
    issues: list[QualityIssue] = field(default_factory=list)
    completeness: float = 0.0
    missing_markers: list[str] = field(default_factory=list)
    checks_run: list[dict[str, Any]] = field(default_factory=list)

    @property
    def needs_clinician_attention(self) -> bool:
        return any(i.severity in ("warning", "error") for i in self.issues)

    def flagged_markers(self) -> set[str]:
        return {i.marker for i in self.issues if i.marker and i.severity != "info"}

    def to_dict(self) -> dict:
        return {
            "accepted": [r.to_dict() for r in self.accepted],
            "issues": [i.to_dict() for i in self.issues],
            "completeness": self.completeness,
            "missing_markers": self.missing_markers,
            "needs_clinician_attention": self.needs_clinician_attention,
            "checks_run": self.checks_run,
        }


# A reference interval describes healthy people; a clinical cohort is wider.
PRIOR_SD_INFLATION = 2.0


def default_population_stats() -> dict[str, dict[str, float]]:
    stats = {}
    for key, marker in load_catalog().items():
        mean, sd = marker.log_stats()
        sd *= PRIOR_SD_INFLATION
        stats[key] = {
            "log_mean": mean,
            "log_sd": sd,
            "log_q1": mean - 0.674 * sd,
            "log_q3": mean + 0.674 * sd,
        }
    return stats


def _safe_log(value: float) -> float:
    return math.log(max(value, 1e-3))


def _decimal_shift_candidate(key: str, value: float, sex: str | None) -> float | None:
    marker = load_catalog()[key]
    reference = marker.reference_for(sex)
    for factor in (0.1, 0.01, 10.0, 100.0):
        shifted = value * factor
        if reference.contains(shifted) and not reference.contains(value):
            return shifted
    return None


def _lab_flag_mismatch(result: NormalizedResult, flag: str | None) -> bool:
    if not flag or not result.lab_reference:
        return False
    m = _RANGE_NUMS.search(result.lab_reference)
    if not m:
        return False
    try:
        low = float(m.group(1).replace(",", "."))
        high = float(m.group(2).replace(",", "."))
        raw = float(str(result.raw_value).replace(",", "."))
    except ValueError:
        return False
    if flag.startswith("H") or flag == "↑":
        return raw <= high
    if flag.startswith("L") or flag == "↓":
        return raw >= low
    return False


def check_report(
    results: list[NormalizedResult],
    *,
    sex: str | None = None,
    population_stats: dict[str, dict[str, float]] | None = None,
    flags: dict[int, str | None] | None = None,
    expected: tuple[str, ...] = BIOMARKER_KEYS,
) -> QualityReport:
    catalog = load_catalog()
    stats = population_stats or default_population_stats()
    issues: list[QualityIssue] = []
    counters = {
        name: 0
        for name in (
            "implausible",
            "decimal_misread",
            "unit_inferred",
            "low_confidence",
            "duplicate",
            "zscore_outlier",
            "iqr_outlier",
            "lab_flag_mismatch",
        )
    }

    kept: dict[str, NormalizedResult] = {}
    for idx, result in enumerate(results):
        marker = catalog[result.key]

        if result.unit_inferred:
            counters["unit_inferred"] += 1
            issues.append(
                QualityIssue(
                    "unit_inferred",
                    "warning",
                    result.key,
                    f"{marker.display}: unit '{result.raw_unit or 'missing'}' could not be read reliably; "
                    "please confirm the unit on the original report.",
                )
            )

        if not marker.plausible.contains(result.value):
            shifted = _decimal_shift_candidate(result.key, result.value, sex)
            counters["implausible"] += 1
            detail = (
                f" A decimal-point misread is likely (would be {shifted:g} {marker.canonical_unit})."
                if shifted is not None
                else ""
            )
            if shifted is not None:
                counters["decimal_misread"] += 1
            issues.append(
                QualityIssue(
                    "implausible",
                    "error",
                    result.key,
                    f"{marker.display} value {result.value:g} {marker.canonical_unit} is outside "
                    f"physiologically plausible limits and was excluded.{detail}",
                )
            )
            continue

        if result.confidence < LOW_CONFIDENCE_THRESHOLD:
            counters["low_confidence"] += 1
            issues.append(
                QualityIssue(
                    "low_confidence",
                    "warning",
                    result.key,
                    f"{marker.display} was extracted with low confidence ({result.confidence:.2f}); "
                    "a clinician should verify it against the original document.",
                )
            )

        s = stats.get(result.key)
        if s:
            log_v = _safe_log(result.value)
            z = (log_v - s["log_mean"]) / s["log_sd"] if s["log_sd"] > 0 else 0.0
            if abs(z) > Z_THRESHOLD:
                counters["zscore_outlier"] += 1
                shifted = _decimal_shift_candidate(result.key, result.value, sex)
                hint = ""
                if shifted is not None:
                    counters["decimal_misread"] += 1
                    hint = f" Possible decimal misread (would be {shifted:g})."
                issues.append(
                    QualityIssue(
                        "zscore_outlier",
                        "warning",
                        result.key,
                        f"{marker.display} is an extreme value relative to the cohort (z={z:.1f}).{hint}",
                    )
                )
            iqr = s["log_q3"] - s["log_q1"]
            if iqr > 0 and not (s["log_q1"] - IQR_K * iqr <= log_v <= s["log_q3"] + IQR_K * iqr):
                counters["iqr_outlier"] += 1
                issues.append(
                    QualityIssue(
                        "iqr_outlier",
                        "warning",
                        result.key,
                        f"{marker.display} lies outside the cohort's interquartile fences.",
                    )
                )

        flag = (flags or {}).get(idx)
        if _lab_flag_mismatch(result, flag):
            counters["lab_flag_mismatch"] += 1
            issues.append(
                QualityIssue(
                    "lab_flag_mismatch",
                    "info",
                    result.key,
                    f"{marker.display}: the lab's '{flag}' flag does not match its printed range.",
                )
            )

        if result.key in kept:
            counters["duplicate"] += 1
            previous = kept[result.key]
            same = math.isclose(previous.value, result.value, rel_tol=0.05)
            issues.append(
                QualityIssue(
                    "duplicate",
                    "info" if same else "warning",
                    result.key,
                    f"{marker.display} appears more than once"
                    + (
                        "."
                        if same
                        else f" with conflicting values ({previous.value:g} vs {result.value:g}); "
                        "the higher-confidence value is kept."
                    ),
                )
            )
            if result.confidence <= previous.confidence:
                continue
        kept[result.key] = result

    missing = [k for k in expected if k not in kept]
    completeness = round((len(expected) - len(missing)) / len(expected), 3) if expected else 1.0
    if missing:
        issues.append(
            QualityIssue(
                "completeness",
                "info",
                None,
                "Not found on this report: " + ", ".join(catalog[k].display for k in missing) + ".",
            )
        )

    checks_run = [{"check": name, "fired": count} for name, count in counters.items()]
    checks_run.append({"check": "completeness", "value": completeness})
    ordered = [kept[k] for k in expected if k in kept]
    return QualityReport(
        accepted=ordered,
        issues=issues,
        completeness=completeness,
        missing_markers=missing,
        checks_run=checks_run,
    )
