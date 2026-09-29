import pytest

from polymarker_common.normalizer import normalize_result
from polymarker_common.proms import Proms
from polymarker_common.quality import check_report


def _full_panel(**overrides):
    rows = {
        "TSH": ("TSH", "2.1", "mIU/L"),
        "FT3": ("Free T3", "3.1", "pg/mL"),
        "FT4": ("Free T4", "1.2", "ng/dL"),
        "TPOAB": ("Anti-TPO", "12", "IU/mL"),
        "VITD": ("Vitamin D", "32", "ng/mL"),
        "B12": ("Vitamin B12", "450", "pg/mL"),
        "FERRITIN": ("Ferritin", "60", "ng/mL"),
        "MG": ("Magnesium", "2.0", "mg/dL"),
        "ZINC": ("Zinc", "85", "ug/dL"),
    }
    rows.update(overrides)
    return [normalize_result(*r) for r in rows.values()]


def test_clean_panel_passes():
    report = check_report(_full_panel())
    assert report.completeness == 1.0
    assert not report.needs_clinician_attention
    assert len(report.accepted) == 9
    assert {c["check"] for c in report.checks_run} >= {
        "implausible",
        "zscore_outlier",
        "iqr_outlier",
    }


def test_implausible_value_is_excluded_with_decimal_hint():
    # OCR dropped the decimal point: "1.9" read as "19" mg/dL magnesium.
    report = check_report(_full_panel(MG=("Magnesium", "19", "mg/dL")))
    codes = {(i.code, i.marker) for i in report.issues}
    assert ("implausible", "MG") in codes
    assert "decimal" in next(i.message for i in report.issues if i.code == "implausible")
    assert "MG" not in {r.key for r in report.accepted}


def test_zscore_outlier_flagged():
    report = check_report(_full_panel(TSH=("TSH", "190", "mIU/L")))
    assert any(i.code == "zscore_outlier" and i.marker == "TSH" for i in report.issues)


def test_duplicate_conflict_keeps_one():
    results = _full_panel() + [normalize_result("Ferritin", "90", "ng/mL")]
    report = check_report(results)
    dup = [i for i in report.issues if i.code == "duplicate"]
    assert dup and dup[0].severity == "warning"
    assert sum(1 for r in report.accepted if r.key == "FERRITIN") == 1


def test_missing_markers_reduce_completeness():
    report = check_report(_full_panel()[:5])
    assert report.completeness == pytest.approx(5 / 9, abs=1e-3)
    assert report.missing_markers == ["B12", "FERRITIN", "MG", "ZINC"]


def test_inferred_unit_warns():
    report = check_report(_full_panel(FT4=("Free T4", "1.2", None)))
    assert any(i.code == "unit_inferred" and i.marker == "FT4" for i in report.issues)
    assert report.needs_clinician_attention


def test_proms_validation_and_targets():
    p = Proms.from_dict(
        {"fatigue_severity": 8, "brain_fog_frequency": "Often", "hair_loss": "mild"}
    )
    assert p.encoded() == {"fatigue_severity": 8, "brain_fog_score": 3, "hair_loss_score": 1}
    assert p.targets() == {"fatigue": 1, "brain_fog": 1, "hair_loss": 0}
    with pytest.raises(ValueError):
        Proms.from_dict(
            {"fatigue_severity": 11, "brain_fog_frequency": "never", "hair_loss": "none"}
        )
