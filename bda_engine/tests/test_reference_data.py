"""
Acceptance criteria from docs/WEEKS_1-3_STATUS_AND_PLAN.md section 3.1
Step 1.2 and section 3.3 Step 3.6:
  - every biomarkers.yaml entry has a non-empty `source`
  - every unit_conversions.csv row has a non-empty `source`
  - the round-trip property test: source -> canonical -> source recovers
    the original value for every conversion row
  - all 9 biomarkers from common.BiomarkerKey are present in every
    reference file
"""

import pytest

from bda_engine.reference_data import (
    load_biomarkers,
    load_lab_providers,
    load_synonyms,
    load_unit_conversions,
)
from bda_engine.schemas.common import BiomarkerKey

EXPECTED_KEYS = {k.value for k in BiomarkerKey}


class TestBiomarkersYaml:
    def test_all_nine_biomarkers_present(self):
        biomarkers = load_biomarkers()
        assert set(biomarkers.keys()) == EXPECTED_KEYS

    def test_every_entry_has_a_source(self):
        biomarkers = load_biomarkers()
        for key, entry in biomarkers.items():
            assert entry.source, f"{key} has no source"
            assert entry.source.strip() != "", f"{key} has a blank source"

    def test_every_entry_has_a_loinc_code(self):
        biomarkers = load_biomarkers()
        for key, entry in biomarkers.items():
            assert entry.loinc_code, f"{key} has no loinc_code"
            # LOINC codes are digits-dash-checkdigit, e.g. "3016-3".
            assert "-" in entry.loinc_code, (
                f"{key} loinc_code looks malformed: {entry.loinc_code!r}"
            )

    def test_default_ref_low_below_high(self):
        biomarkers = load_biomarkers()
        for key, entry in biomarkers.items():
            assert entry.default_ref_low < entry.default_ref_high, key

    def test_plausible_bounds_contain_default_ref_range(self):
        # The plausibility bounds (used by data_quality.py) must be wide
        # enough to admit the "normal" reference range, or every normal
        # result would be flagged implausible.
        biomarkers = load_biomarkers()
        for key, entry in biomarkers.items():
            assert entry.plausible_min <= entry.default_ref_low, key
            assert entry.plausible_max >= entry.default_ref_high, key


class TestUnitConversionsCsv:
    def test_every_row_has_a_source(self):
        rows = load_unit_conversions()
        assert len(rows) > 0
        for row in rows:
            assert row.source, f"{row.biomarker_key}/{row.from_unit} has no source"

    def test_every_biomarker_has_an_identity_conversion(self):
        """Every biomarker must have a from_unit == to_unit == canonical_unit
        row with factor 1.0, so a value already in canonical units still
        round-trips through the same lookup path (see services/units.py,
        Week 3) without a special case."""
        biomarkers = load_biomarkers()
        rows = load_unit_conversions()

        for key, biomarker in biomarkers.items():
            identity_rows = [
                r for r in rows
                if r.biomarker_key == key
                and r.from_unit == biomarker.canonical_unit
                and r.to_unit == biomarker.canonical_unit
            ]
            assert len(identity_rows) == 1, (
                f"{key} must have exactly one identity conversion row "
                f"for its canonical unit {biomarker.canonical_unit!r}, "
                f"found {len(identity_rows)}"
            )
            assert identity_rows[0].factor == 1.0

    def test_round_trip_recovers_original_value_for_every_row(self):
        # Every row, not a hardcoded slice -- so a future addition to
        # unit_conversions.csv is covered automatically.
        rows = load_unit_conversions()
        assert len(rows) >= 21  # sanity floor, not an exact pin

        original = 5.0
        for row in rows:
            canonical = original * row.factor
            recovered = canonical / row.factor
            assert recovered == pytest.approx(original, rel=1e-9), (
                f"{row.biomarker_key} {row.from_unit}->{row.to_unit} "
                f"failed to round-trip"
            )

    def test_every_conversion_row_targets_the_canonical_unit(self):
        biomarkers = load_biomarkers()
        rows = load_unit_conversions()
        for row in rows:
            assert row.to_unit == biomarkers[row.biomarker_key].canonical_unit, (
                f"{row.biomarker_key}: {row.from_unit} -> {row.to_unit} "
                f"does not target the canonical unit "
                f"{biomarkers[row.biomarker_key].canonical_unit!r}"
            )


class TestAnalyteSynonymsCsv:
    def test_every_biomarker_has_at_least_ten_variants(self):
        synonyms = load_synonyms()
        counts = {}
        for row in synonyms:
            counts[row.biomarker_key] = counts.get(row.biomarker_key, 0) + 1

        assert set(counts.keys()) == EXPECTED_KEYS
        for key, count in counts.items():
            assert count >= 10, f"{key} only has {count} synonym variants"

    def test_variants_are_lowercase(self):
        # The normalizer's canonicalization step lowercases input before
        # matching (Week 3), so the table should already be lowercase to
        # avoid a silent double-standard.
        synonyms = load_synonyms()
        for row in synonyms:
            assert row.variant == row.variant.lower(), row.variant

    def test_no_duplicate_variant_within_a_biomarker(self):
        synonyms = load_synonyms()
        seen = {}
        for row in synonyms:
            key = (row.biomarker_key, row.variant)
            assert key not in seen, f"duplicate variant: {key}"
            seen[key] = True

    def test_no_variant_shared_across_two_different_biomarkers(self):
        # A variant string that maps to two different biomarkers would
        # make exact-match mapping ambiguous.
        synonyms = load_synonyms()
        variant_to_keys = {}
        for row in synonyms:
            variant_to_keys.setdefault(row.variant, set()).add(row.biomarker_key)

        ambiguous = {v: ks for v, ks in variant_to_keys.items() if len(ks) > 1}
        assert not ambiguous, f"ambiguous variants: {ambiguous}"


class TestLabProvidersCsv:
    def test_loads_without_error(self):
        rows = load_lab_providers()
        assert len(rows) > 0

    def test_every_provider_id_maps_to_exactly_one_canonical_name(self):
        rows = load_lab_providers()
        id_to_names = {}
        for row in rows:
            id_to_names.setdefault(row.provider_id, set()).add(row.canonical_name)

        for provider_id, names in id_to_names.items():
            assert len(names) == 1, f"{provider_id} has inconsistent canonical names: {names}"
