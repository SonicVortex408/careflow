"""
Week 3 acceptance criteria (docs/WEEKS_1-3_STATUS_AND_PLAN.md section 3.3):
  - the adversarial variant set maps correctly, including the exact
    "Tr iodothyronine Free" case from the brief
  - never map with mapping_method == "unmapped" silently -- unmapped is
    a valid, expected outcome for garbage input, not an error
  - zero *wrong* mappings on this set (a wrong biomarker_key is worse
    than an honest unmapped)
"""

import pytest

from app.services.normalizer import map_analyte_name


class TestCleanInputs:
    @pytest.mark.parametrize(
        "raw,expected_key,expected_method",
        [
            ("TSH", "TSH", "exact"),
            ("FT3", "FT3", "exact"),
            ("FT4", "FT4", "exact"),
            ("Free T3", "FT3", "exact"),
            ("Free T4", "FT4", "exact"),
            ("Ferritin", "FERRITIN", "exact"),
            ("Magnesium", "MAGNESIUM", "exact"),
            ("Zinc", "ZINC", "exact"),
            ("Vitamin B12", "VIT_B12", "exact"),
            ("Cobalamin", "VIT_B12", "exact"),
        ],
    )
    def test_clean_variant_maps_exactly(self, raw, expected_key, expected_method):
        result = map_analyte_name(raw)
        assert result.biomarker_key == expected_key
        assert result.mapping_method == expected_method
        assert result.mapping_confidence >= 0.95
        assert result.loinc_code is not None


class TestAdversarialVariants:
    """The exact adversarial set from the plan doc, plus the brief's own
    "Tr iodothyronine Free" example verbatim."""

    @pytest.mark.parametrize(
        "raw,expected_key",
        [
            ("Tr iodothyronine Free", "FT3"),   # the brief's own example
            ("FT3", "FT3"),
            ("Free T 3", "FT3"),                # OCR word-split
            ("T3,Free", "FT3"),
            ("25(OH) Vit-D", "VIT_D_25OH"),
            ("Anti TPO Ab", "ANTI_TPO"),
            ("Vit B-12", "VIT_B12"),
        ],
    )
    def test_adversarial_variant_maps_to_correct_biomarker(self, raw, expected_key):
        result = map_analyte_name(raw)
        assert result.biomarker_key == expected_key, (
            f"{raw!r} mapped to {result.biomarker_key!r} "
            f"(method={result.mapping_method}, score={result.mapping_confidence}, "
            f"matched={result.matched_variant!r}), expected {expected_key!r}"
        )
        assert result.mapping_method != "unmapped"
        assert result.loinc_code is not None


class TestUnmappedBehavior:
    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "Random Unrelated Text About Nothing Medical",
            "Complete Blood Count",
            "xyzzy plugh qwerty",
        ],
    )
    def test_garbage_input_is_unmapped_not_guessed(self, raw):
        result = map_analyte_name(raw)
        assert result.mapping_method == "unmapped"
        assert result.biomarker_key is None
        assert result.loinc_code is None
        assert result.mapping_confidence == 0.0
        assert result.needs_review is True

    def test_none_like_empty_string_is_unmapped(self):
        result = map_analyte_name("")
        assert result.mapping_method == "unmapped"


class TestNoCrossBiomarkerConfusion:
    """The two thyroid-hormone pairs (FT3/FT4) and (TSH/Anti-TPO) are the
    likeliest source of a wrong-not-unmapped mapping. Confirm each
    variant lands on its own biomarker, never its sibling."""

    @pytest.mark.parametrize(
        "raw,expected_key,forbidden_key",
        [
            ("Free T3", "FT3", "FT4"),
            ("Free T4", "FT4", "FT3"),
            ("Free Thyroxine", "FT4", "FT3"),
            ("Free Triiodothyronine", "FT3", "FT4"),
            ("TSH", "TSH", "ANTI_TPO"),
            ("Anti-TPO", "ANTI_TPO", "TSH"),
        ],
    )
    def test_no_confusion_between_similar_thyroid_markers(self, raw, expected_key, forbidden_key):
        result = map_analyte_name(raw)
        assert result.biomarker_key == expected_key
        assert result.biomarker_key != forbidden_key


class TestMappingResultShape:
    def test_exact_match_has_full_confidence(self):
        result = map_analyte_name("TSH")
        assert result.mapping_confidence == 1.0
        assert result.needs_review is False

    def test_unmapped_never_returns_a_loinc_code(self):
        result = map_analyte_name("not a real analyte at all")
        assert result.loinc_code is None
        assert result.loinc_long_name is None
