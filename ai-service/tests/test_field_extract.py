"""
Week 2 Step 2.6 acceptance: age/sex/accession/lab-provider extraction,
against real generator page text (render_pdf.py's _draw_header prints
"Patient: {age}Y / {sex}" and "Accession: {accession}").
"""

import pdfplumber
import pytest

from app.ocr.field_extract import (
    extract_accession,
    extract_age,
    extract_lab_provider,
    extract_sex,
)
from app.services.reference_data import load_lab_providers


@pytest.fixture
def page_text(clean_pdf_factory):
    path, _ = clean_pdf_factory(layout="single_column")
    with pdfplumber.open(path) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


class TestExtractAgeSex:
    def test_combined_age_sex_from_real_report(self, page_text):
        # clean_pdf_factory renders patient_age_years=45.0, patient_sex="female"
        age = extract_age(page_text)
        sex = extract_sex(page_text)
        assert age.value == "45"
        assert age.confidence > 0
        assert sex.value == "female"
        assert sex.confidence > 0

    @pytest.mark.parametrize(
        "raw,expected_age,expected_sex",
        [
            ("Patient: 42Y / M", "42", "male"),
            ("Patient: 67Y/F", "67", "female"),
            ("Age: 30", "30", None),
            ("Sex: Female", None, "female"),
            ("Gender: M", None, "male"),
        ],
    )
    def test_various_formats(self, raw, expected_age, expected_sex):
        age = extract_age(raw)
        sex = extract_sex(raw)
        assert age.value == expected_age
        assert sex.value == expected_sex

    def test_no_match_returns_none_with_zero_confidence(self):
        result = extract_age("no age info here at all")
        assert result.value is None
        assert result.confidence == 0.0


class TestExtractAccession:
    def test_extracts_from_real_report(self, page_text):
        result = extract_accession(page_text)
        assert result.value == "ACC-1"

    def test_no_accession_present(self):
        result = extract_accession("nothing relevant here")
        assert result.value is None


class TestExtractLabProvider:
    def test_extracts_from_real_report_header(self, page_text):
        known = sorted({r.canonical_name for r in load_lab_providers()})
        result = extract_lab_provider(page_text, known)
        assert result.value == "Meridian Health Labs"
        assert result.confidence >= 0.9

    def test_no_known_providers_returns_none(self):
        result = extract_lab_provider("Some Lab Inc.", [])
        assert result.value is None
        assert result.confidence == 0.0

    def test_empty_text_returns_none(self):
        known = sorted({r.canonical_name for r in load_lab_providers()})
        result = extract_lab_provider("", known)
        assert result.value is None

    def test_unrelated_text_does_not_match(self):
        known = sorted({r.canonical_name for r in load_lab_providers()})
        result = extract_lab_provider("This document has nothing to do with any lab.", known)
        assert result.value is None
