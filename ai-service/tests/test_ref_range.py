"""
Week 3 Step 3.3 acceptance: every reference-range format listed in
docs/WEEKS_1-3_STATUS_AND_PLAN.md section 3.3, in priority order.
"""

import pytest

from app.services.common_types import Comparator
from app.services.ref_range import parse_reference_range


class TestBoundedRanges:
    @pytest.mark.parametrize(
        "raw",
        [
            "0.4 - 4.0",
            "0.4-4.0",
            "0.4 – 4.0",   # en dash
            "0.4 — 4.0",   # em dash
            "0.4 to 4.0",
        ],
    )
    def test_bounded_range_formats(self, raw):
        result = parse_reference_range(raw)
        assert result.parsed is True
        assert result.ref_low == pytest.approx(0.4)
        assert result.ref_high == pytest.approx(4.0)
        assert result.ref_operator == Comparator.NONE

    def test_normal_prefix_is_stripped(self):
        result = parse_reference_range("Normal: 0.4-4.0")
        assert result.parsed is True
        assert result.ref_low == pytest.approx(0.4)
        assert result.ref_high == pytest.approx(4.0)

    def test_reference_range_prefix_is_stripped(self):
        result = parse_reference_range("Reference range: 0.4-4.0")
        assert result.parsed is True
        assert result.ref_low == pytest.approx(0.4)


class TestOpenEndedBounds:
    def test_less_than(self):
        result = parse_reference_range("<4.0")
        assert result.parsed is True
        assert result.ref_operator == Comparator.LT
        assert result.ref_high == pytest.approx(4.0)
        assert result.ref_low is None

    def test_less_than_or_equal_symbol(self):
        result = parse_reference_range("≤4.0")  # <=
        assert result.parsed is True
        assert result.ref_operator == Comparator.LT
        assert result.ref_high == pytest.approx(4.0)

    def test_greater_than(self):
        result = parse_reference_range(">150")
        assert result.parsed is True
        assert result.ref_operator == Comparator.GT
        assert result.ref_low == pytest.approx(150)
        assert result.ref_high is None

    def test_up_to_phrasing(self):
        result = parse_reference_range("up to 4.0")
        assert result.parsed is True
        assert result.ref_operator == Comparator.LT
        assert result.ref_high == pytest.approx(4.0)


class TestSexStratifiedRanges:
    RAW = "Male: 13-150 Female: 12-100"

    def test_male_selects_male_segment(self):
        result = parse_reference_range(self.RAW, patient_sex="male")
        assert result.parsed is True
        assert result.ref_low == pytest.approx(13)
        assert result.ref_high == pytest.approx(150)

    def test_female_selects_female_segment(self):
        result = parse_reference_range(self.RAW, patient_sex="female")
        assert result.parsed is True
        assert result.ref_low == pytest.approx(12)
        assert result.ref_high == pytest.approx(100)

    def test_unknown_sex_does_not_guess(self):
        result = parse_reference_range(self.RAW, patient_sex=None)
        assert result.parsed is False
        assert result.ref_low is None
        assert result.ref_high is None

    def test_sex_alias_men_women_also_works(self):
        raw = "Men: 13-150 Women: 12-100"
        result = parse_reference_range(raw, patient_sex="female")
        assert result.parsed is True
        assert result.ref_low == pytest.approx(12)


class TestUnparseableInput:
    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "Deficient/Insufficient/Sufficient",
            "See lab notes",
            "N/A",
        ],
    )
    def test_unparseable_text_is_not_guessed(self, raw):
        result = parse_reference_range(raw)
        assert result.parsed is False
        assert result.ref_low is None
        assert result.ref_high is None
        assert result.ref_operator == Comparator.NONE
