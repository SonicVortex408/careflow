"""
Week 3 Step 3.4 acceptance: plausibility, ref-range order, flag
agreement, duplicate-analyte checks, and the overall severity policy
(REJECTED excludes from gold/, SUSPECT flags for review).
"""

from app.services.common_types import FlagRaw, QualityStatus
from app.services.data_quality import (
    check_duplicate_analyte,
    check_flag_agreement,
    check_plausibility,
    check_ref_range_order,
    run_quality_checks,
)


class TestPlausibility:
    def test_normal_tsh_value_passes(self):
        assert check_plausibility("TSH", 2.5).passed is True

    def test_wildly_high_tsh_fails(self):
        # A TSH of 5000 mIU/L is essentially never real -- almost
        # certainly a unit mix-up or decimal-point OCR slip.
        assert check_plausibility("TSH", 5000).passed is False

    def test_none_value_fails(self):
        assert check_plausibility("TSH", None).passed is False

    def test_unknown_biomarker_fails(self):
        assert check_plausibility("NOT_REAL", 2.5).passed is False


class TestRefRangeOrder:
    def test_low_below_high_passes(self):
        assert check_ref_range_order(0.4, 4.0).passed is True

    def test_low_equal_high_fails(self):
        assert check_ref_range_order(4.0, 4.0).passed is False

    def test_low_above_high_fails(self):
        assert check_ref_range_order(5.0, 4.0).passed is False

    def test_missing_bounds_does_not_fail(self):
        # An open-ended bound (<4.0) has no ref_low -- that's not a defect.
        assert check_ref_range_order(None, 4.0).passed is True
        assert check_ref_range_order(0.4, None).passed is True


class TestFlagAgreement:
    def test_high_flag_with_value_above_range_agrees(self):
        result = check_flag_agreement(5.0, 0.4, 4.0, FlagRaw.HIGH)
        assert result.passed is True

    def test_high_flag_with_value_inside_range_disagrees(self):
        result = check_flag_agreement(2.0, 0.4, 4.0, FlagRaw.HIGH)
        assert result.passed is False

    def test_low_flag_with_value_below_range_agrees(self):
        assert check_flag_agreement(0.1, 0.4, 4.0, FlagRaw.LOW).passed is True

    def test_low_flag_with_value_inside_range_disagrees(self):
        assert check_flag_agreement(2.0, 0.4, 4.0, FlagRaw.LOW).passed is False

    def test_normal_flag_with_value_inside_range_agrees(self):
        assert check_flag_agreement(2.0, 0.4, 4.0, FlagRaw.NORMAL).passed is True

    def test_normal_flag_with_value_outside_range_disagrees(self):
        assert check_flag_agreement(5.0, 0.4, 4.0, FlagRaw.NORMAL).passed is False

    def test_no_flag_present_does_not_fail(self):
        assert check_flag_agreement(5.0, 0.4, 4.0, None).passed is True


class TestDuplicateAnalyte:
    def test_no_siblings_passes(self):
        assert check_duplicate_analyte("TSH", []).passed is True

    def test_no_matching_sibling_passes(self):
        assert check_duplicate_analyte("TSH", ["FT3", "FT4"]).passed is True

    def test_matching_sibling_fails(self):
        result = check_duplicate_analyte("TSH", ["TSH", "FT3"])
        assert result.passed is False
        assert "2 times" in result.detail


class TestRunQualityChecks:
    def test_clean_observation_is_ok(self):
        result = run_quality_checks(
            biomarker_key="TSH", value_canonical=2.5,
            ref_low=0.4, ref_high=4.0, flag_raw=FlagRaw.NORMAL,
            sibling_biomarker_keys=["FT3", "FT4"],
        )
        assert result.status == QualityStatus.OK
        assert all(c.passed for c in result.checks)

    def test_implausible_value_is_rejected(self):
        result = run_quality_checks(biomarker_key="TSH", value_canonical=5000)
        assert result.status == QualityStatus.REJECTED

    def test_unmapped_biomarker_is_rejected(self):
        result = run_quality_checks(biomarker_key=None, value_canonical=2.5)
        assert result.status == QualityStatus.REJECTED

    def test_flag_disagreement_alone_is_suspect_not_rejected(self):
        result = run_quality_checks(
            biomarker_key="TSH", value_canonical=2.0,
            ref_low=0.4, ref_high=4.0, flag_raw=FlagRaw.HIGH,
        )
        assert result.status == QualityStatus.SUSPECT

    def test_duplicate_alone_is_suspect_not_rejected(self):
        result = run_quality_checks(
            biomarker_key="TSH", value_canonical=2.0,
            sibling_biomarker_keys=["TSH"],
        )
        assert result.status == QualityStatus.SUSPECT
