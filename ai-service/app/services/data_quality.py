"""
Week 3, Step 3.4: per-observation quality checks.

Each check is independent and returns a QualityCheck(name, passed,
detail); run_quality_checks() combines them into an overall
QualityStatus. Severity policy (deliberately conservative -- see
"never guess" in normalizer.py):

  REJECTED  the value cannot be trusted at all: no canonical value
            (unrecognized unit) or grossly outside physiological
            plausibility (almost certainly an OCR/unit error, e.g. a
            misplaced decimal point or wrong unit assumed).
  SUSPECT   the value itself may be fine, but something around it is
            inconsistent and a human should look: the reference range
            didn't parse sensibly, the printed H/L/N flag disagrees
            with where the value actually sits, or the same analyte
            appears more than once in the same report.
  OK        no check raised a concern.

REJECTED and SUSPECT rows are excluded from
gold/patient_feature_vectors/ (Week 1 Step 3.5) -- a rejected or
suspect number must never silently enter a feature vector.
"""

from collections import Counter
from dataclasses import dataclass

from app.services.common_types import FlagRaw, QualityStatus
from app.services.reference_data import load_biomarkers


@dataclass(frozen=True)
class QualityCheck:
    name: str
    passed: bool
    detail: str | None = None


@dataclass(frozen=True)
class QualityResult:
    status: QualityStatus
    checks: tuple[QualityCheck, ...]


def check_plausibility(biomarker_key: str, value_canonical: float | None) -> QualityCheck:
    if value_canonical is None:
        return QualityCheck("plausibility", passed=False, detail="no canonical value")

    biomarker = load_biomarkers().get(biomarker_key)
    if biomarker is None:
        return QualityCheck(
            "plausibility", passed=False,
            detail=f"unknown biomarker {biomarker_key!r}",
        )

    if biomarker.plausible_min <= value_canonical <= biomarker.plausible_max:
        return QualityCheck("plausibility", passed=True)

    return QualityCheck(
        "plausibility", passed=False,
        detail=(
            f"{value_canonical} outside plausible range "
            f"[{biomarker.plausible_min}, {biomarker.plausible_max}] "
            f"for {biomarker_key}"
        ),
    )


def check_ref_range_order(ref_low: float | None, ref_high: float | None) -> QualityCheck:
    if ref_low is None or ref_high is None:
        # Not every row has a parsed range (open-ended bounds, or the
        # range failed to parse) -- that's not itself a quality defect.
        return QualityCheck("ref_range_order", passed=True, detail="no bounded range to check")

    if ref_low < ref_high:
        return QualityCheck("ref_range_order", passed=True)

    return QualityCheck(
        "ref_range_order", passed=False,
        detail=f"ref_low ({ref_low}) is not below ref_high ({ref_high})",
    )


def check_flag_agreement(
    value_canonical: float | None,
    ref_low: float | None,
    ref_high: float | None,
    flag_raw: FlagRaw | None,
) -> QualityCheck:
    if flag_raw is None or value_canonical is None or ref_low is None or ref_high is None:
        return QualityCheck("flag_agreement", passed=True, detail="insufficient data to check")

    if flag_raw == FlagRaw.HIGH and value_canonical <= ref_high:
        return QualityCheck(
            "flag_agreement", passed=False,
            detail=f"flagged H but {value_canonical} is within/below range high {ref_high}",
        )
    if flag_raw == FlagRaw.LOW and value_canonical >= ref_low:
        return QualityCheck(
            "flag_agreement", passed=False,
            detail=f"flagged L but {value_canonical} is within/above range low {ref_low}",
        )
    if flag_raw == FlagRaw.NORMAL and not (ref_low <= value_canonical <= ref_high):
        return QualityCheck(
            "flag_agreement", passed=False,
            detail=f"flagged N but {value_canonical} is outside [{ref_low}, {ref_high}]",
        )

    return QualityCheck("flag_agreement", passed=True)


def check_duplicate_analyte(biomarker_key: str, sibling_biomarker_keys: list[str]) -> QualityCheck:
    """sibling_biomarker_keys: the biomarker_key of every OTHER row in
    the same report (i.e. not including this row itself)."""

    count = Counter(sibling_biomarker_keys)[biomarker_key]
    if count == 0:
        return QualityCheck("duplicate_analyte", passed=True)

    return QualityCheck(
        "duplicate_analyte", passed=False,
        detail=f"{biomarker_key} appears {count + 1} times in this report",
    )


def run_quality_checks(
    biomarker_key: str | None,
    value_canonical: float | None,
    ref_low: float | None = None,
    ref_high: float | None = None,
    flag_raw: FlagRaw | None = None,
    sibling_biomarker_keys: list[str] | None = None,
) -> QualityResult:
    if biomarker_key is None:
        # Unmapped rows have no biomarker to quality-check against --
        # they are already excluded from gold/ by mapping_method alone.
        return QualityResult(
            status=QualityStatus.REJECTED,
            checks=(QualityCheck("mapped", passed=False, detail="unmapped analyte"),),
        )

    checks = [
        check_plausibility(biomarker_key, value_canonical),
        check_ref_range_order(ref_low, ref_high),
        check_flag_agreement(value_canonical, ref_low, ref_high, flag_raw),
        check_duplicate_analyte(biomarker_key, sibling_biomarker_keys or []),
    ]

    plausibility_ok = checks[0].passed

    if not plausibility_ok:
        status = QualityStatus.REJECTED
    elif not all(c.passed for c in checks):
        status = QualityStatus.SUSPECT
    else:
        status = QualityStatus.OK

    return QualityResult(status=status, checks=tuple(checks))
