import math

import pytest

from polymarker_common.catalog import BIOMARKER_KEYS, by_loinc, load_catalog
from polymarker_common.normalizer import (
    clean_unit,
    convert_to_canonical,
    match_name,
    normalize_result,
    parse_value,
)


def test_catalog_has_the_nine_markers_with_loinc():
    catalog = load_catalog()
    assert tuple(catalog) == BIOMARKER_KEYS
    assert {m.loinc for m in catalog.values()} == {
        "3016-3",
        "3051-0",
        "3024-7",
        "8099-4",
        "62292-8",
        "2132-9",
        "2276-4",
        "19123-9",
        "5763-8",
    }
    assert by_loinc("2276-4").key == "FERRITIN"


@pytest.mark.parametrize(
    "label,key",
    [
        ("FT3", "FT3"),
        ("Free T3", "FT3"),
        ("Triiodothyronine, Free", "FT3"),
        ("Free Thyroxine (FT4)", "FT4"),
        ("TSH 3rd Generation", "TSH"),
        ("Thyroid Peroxidase Antibodies", "TPOAB"),
        ("Anti-TPO", "TPOAB"),
        ("25-OH Vitamin D", "VITD"),
        ("Vitamin D, 25-Hydroxy", "VITD"),
        ("Vitamin B12 (Cobalamin)", "B12"),
        ("Ferritin, Serum", "FERRITIN"),
        ("S. Magnesium", "MG"),
        ("Zinc, Plasma", "ZINC"),
    ],
)
def test_match_name_variants(label, key):
    match = match_name(label)
    assert match is not None, label
    assert match.key == key


def test_fuzzy_match_has_lower_confidence():
    match = match_name("Ferritn")  # OCR dropped a letter
    assert match is not None and match.key == "FERRITIN"
    assert match.method == "fuzzy"
    assert match.confidence < 0.95


def test_non_target_labels_are_ignored():
    assert match_name("Hemoglobin") is None
    assert match_name("Total Cholesterol") is None
    assert match_name("") is None


@pytest.mark.parametrize(
    "key,value,unit,expected",
    [
        ("FT4", 1.0, "ng/dL", 12.87),
        ("FT3", 3.0, "pg/mL", 4.608),
        ("VITD", 30, "ng/mL", 74.88),
        ("B12", 400, "pg/mL", 295.12),
        ("MG", 2.0, "mg/dL", 0.8228),
        ("MG", 1.6, "mEq/L", 0.8),
        ("ZINC", 80, "µg/dL", 12.24),
        ("ZINC", 80, "mcg/dL", 12.24),
        ("TSH", 2.1, "µIU/mL", 2.1),
        ("FERRITIN", 45, "ng/mL", 45),
    ],
)
def test_unit_conversion(key, value, unit, expected):
    conv = convert_to_canonical(load_catalog()[key], value, unit)
    assert not conv.inferred
    assert math.isclose(conv.value, expected, rel_tol=1e-3)


def test_missing_unit_is_inferred_and_flagged():
    # 1.1 without a unit can only be a plausible free T4 in ng/dL.
    conv = convert_to_canonical(load_catalog()["FT4"], 1.1, None)
    assert conv.inferred
    assert conv.confidence < 1
    assert math.isclose(conv.value, 1.1 * 12.87, rel_tol=1e-3)


def test_parse_value_variants():
    assert parse_value("4,2") == (4.2, None)
    assert parse_value("<0.5") == (0.5, "<")
    assert parse_value("≥ 10") == (10.0, ">=")
    with pytest.raises(ValueError):
        parse_value("n/a")


def test_clean_unit():
    assert clean_unit(" µIU / mL ") == "uiu/ml"
    assert clean_unit("mcg/dL") == "ug/dl"


def test_normalize_result_uses_sex_specific_reference():
    female = normalize_result("Ferritin", "20", "ng/mL", sex="F")
    male = normalize_result("Ferritin", "20", "ng/mL", sex="M")
    assert female.reference_low == 15 and male.reference_low == 30
    assert female.confidence == 1.0
