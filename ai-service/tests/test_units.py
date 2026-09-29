"""
Week 3 Step 3.2 acceptance criteria: unit alias canonicalization, and
conversion keyed by biomarker (not a global unit-pair table, since
mass<->molar factors depend on molar mass).
"""

import pytest

from app.services.reference_data import load_unit_conversions
from app.services.units import canonicalize_unit, convert


class TestCanonicalizeUnit:
    @pytest.mark.parametrize(
        "variant",
        ["uIU/mL", "µIU/mL", "μIU/mL", "mcIU/mL"],
    )
    def test_tsh_microsign_variants_fold_to_one_token(self, variant):
        # These four spellings of the same unit must all canonicalize
        # identically -- the exact example from the brief.
        canonical = canonicalize_unit(variant)
        assert canonical == canonicalize_unit("uIU/mL")

    def test_stray_space_around_slash_is_removed(self):
        assert canonicalize_unit("pg / mL") == canonicalize_unit("pg/mL")

    def test_empty_unit_returns_empty_string(self):
        assert canonicalize_unit("") == ""
        assert canonicalize_unit(None) == ""


class TestConvert:
    def test_tsh_all_microsign_variants_convert_identically(self):
        results = [
            convert("TSH", 2.5, "uIU/mL"),
            convert("TSH", 2.5, "µIU/mL"),
            convert("TSH", 2.5, "μIU/mL"),
            convert("TSH", 2.5, "mcIU/mL"),
        ]
        for r in results:
            assert r.unit_recognized is True
            assert r.value_canonical == pytest.approx(2.5)
            assert r.unit_canonical == "mIU/L"

    def test_ft4_ng_dl_conversion_matches_published_factor(self):
        # 1 ng/dL = 12.87 pmol/L (verified against a published clinical
        # chemistry source -- see reference/unit_conversions.csv).
        result = convert("FT4", 1.0, "ng/dL")
        assert result.value_canonical == pytest.approx(12.87)
        assert result.unit_canonical == "pmol/L"

    def test_ft4_pg_ml_is_derived_consistently_with_ng_dl(self):
        # 1 pg/mL = 0.1 ng/dL, so its factor must be 0.1 x the ng/dL factor.
        ng_dl = convert("FT4", 1.0, "ng/dL")
        pg_ml = convert("FT4", 10.0, "pg/mL")  # 10 pg/mL = 1 ng/dL
        assert pg_ml.value_canonical == pytest.approx(ng_dl.value_canonical, rel=1e-6)

    def test_magnesium_meq_l_uses_divalent_ion_factor(self):
        # 1 mEq/L = 0.5 mmol/L for Mg2+ (valence 2).
        result = convert("MAGNESIUM", 2.0, "mEq/L")
        assert result.value_canonical == pytest.approx(1.0)

    def test_unrecognized_unit_does_not_guess(self):
        result = convert("TSH", 2.5, "furlongs/fortnight")
        assert result.unit_recognized is False
        assert result.value_canonical is None
        assert result.conversion_factor is None

    def test_unrecognized_biomarker_does_not_guess(self):
        result = convert("NOT_A_REAL_BIOMARKER", 2.5, "mIU/L")
        assert result.unit_recognized is False

    def test_value_already_in_canonical_unit_passes_through(self):
        result = convert("TSH", 3.1, "mIU/L")
        assert result.unit_recognized is True
        assert result.value_canonical == pytest.approx(3.1)


class TestRoundTripAllConversionRows:
    """Property test: every row in reference/unit_conversions.csv must
    round-trip (source -> canonical -> source) without loss."""

    def test_round_trip_recovers_original_value(self):
        rows = load_unit_conversions()
        assert len(rows) >= 21

        for row in rows:
            original = 7.0
            result = convert(row.biomarker_key, original, row.from_unit)
            assert result.unit_recognized, (
                f"{row.biomarker_key} {row.from_unit} not recognized by convert()"
            )
            recovered = result.value_canonical / row.factor
            assert recovered == pytest.approx(original, rel=1e-9), (
                f"{row.biomarker_key} {row.from_unit} failed to round-trip"
            )

    def test_every_row_has_a_nonempty_source_reachable_via_convert(self):
        rows = load_unit_conversions()
        for row in rows:
            result = convert(row.biomarker_key, 1.0, row.from_unit)
            assert result.conversion_source, row.biomarker_key
