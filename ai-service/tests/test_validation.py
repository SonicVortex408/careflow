"""
These are the path-traversal / cross-patient-read guards documented in
WEEKS_1-3_STATUS_AND_PLAN.md (Phase 0, item 5). Every case here is a
concrete attack shape, not an arbitrary edge case.
"""

import pytest

from app.core.validation import (
    InvalidFilename,
    InvalidPatientId,
    safe_filename,
    validate_patient_id,
)

VALID_ID = "507f1f77bcf86cd799439011"


def test_valid_object_id_passes_through_unchanged():
    assert validate_patient_id(VALID_ID) == VALID_ID


@pytest.mark.parametrize(
    "bad_id",
    [
        "../../etc/passwd",
        "../other_patient",
        "",
        "short",
        "zzzzzzzzzzzzzzzzzzzzzzzz",  # 24 chars, but not hex
        "507f1f77bcf86cd799439011extra",  # too long
        "507f1f77bcf86cd79943901",  # too short (23)
        "507f1f77bcf86cd7994390 1",  # embedded space
        None,
        123,
    ],
)
def test_invalid_patient_ids_are_rejected(bad_id):
    with pytest.raises(InvalidPatientId):
        validate_patient_id(bad_id)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("report.pdf", "report.pdf"),
        ("../../../etc/passwd", "passwd"),
        ("..\\..\\windows\\win.ini", "win.ini"),
        ("/absolute/path/x.txt", "x.txt"),
        ("C:\\Users\\x\\report.pdf", "report.pdf"),
    ],
)
def test_filename_traversal_is_stripped_to_a_basename(raw, expected):
    assert safe_filename(raw) == expected


def test_filename_unsafe_characters_are_replaced():
    result = safe_filename("weird<>:\"|?*name.pdf")
    assert "/" not in result
    assert "\\" not in result
    assert result.endswith(".pdf")


def test_filename_dotfile_and_empty_fall_back_safely():
    assert safe_filename("...") == "upload"
    with pytest.raises(InvalidFilename):
        safe_filename("")


def test_filename_is_length_bounded_and_keeps_extension():
    result = safe_filename("a" * 500 + ".pdf")
    assert len(result) <= 200
    assert result.endswith(".pdf")
