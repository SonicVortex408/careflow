from polymarker_common.parser import parse_line, parse_report_text

REPORT_A = """CityCare Diagnostics Laboratory
Patient: Jane Example        Age/Sex: 41 Y / F
Collected: 2026-03-14
TEST                     RESULT    UNIT      REFERENCE
TSH                      5.8       uIU/mL    0.40 - 4.00   H
Free T4                  0.9       ng/dL     0.8 - 1.8
Free T3                  2.6       pg/mL     2.0 - 4.4
Anti-TPO                 88        IU/mL     < 35          H
Vitamin D (25-OH)        18        ng/mL     30 - 100      L
Vitamin B12              310       pg/mL     200 - 900
Ferritin                 12        ng/mL     15 - 150      L
Magnesium                1.9       mg/dL     1.7 - 2.4
Zinc                     72        ug/dL     60 - 120
Hemoglobin               12.9      g/dL      12 - 16
"""

REPORT_B = """Lab: Northside Pathology
Sex: Male  Age: 55
Sample date: 03/02/2026
| Thyroid Stimulating Hormone | 1.2 | mIU/L | 0.4-4.0 |
| Thyroxine, Free | 15.1 | pmol/L | 10-23 |
| 25-Hydroxyvitamin D: 62 nmol/L (50-125)
| Serum Ferritin | 210 | ug/L | 30-400 |
"""


def test_parse_columnar_report():
    report = parse_report_text(REPORT_A)
    keys = [r.marker_key for r in report.rows]
    assert keys == ["TSH", "FT4", "FT3", "TPOAB", "VITD", "B12", "FERRITIN", "MG", "ZINC"]
    tsh = report.rows[0]
    assert tsh.value == "5.8" and tsh.unit == "uIU/mL"
    assert tsh.reference_text == "0.40 - 4.00" and tsh.flag == "H"
    vitd = next(r for r in report.rows if r.marker_key == "VITD")
    assert vitd.value == "18"  # not the "25" inside "25-OH"
    assert report.metadata.age == 41 and report.metadata.sex == "F"
    assert report.metadata.collected_at == "2026-03-14"
    assert "Diagnostics" in report.metadata.lab_provider
    assert any("Hemoglobin" in line for line in report.unmatched_lines)


def test_parse_pipe_and_colon_layouts():
    report = parse_report_text(REPORT_B)
    by_key = {r.marker_key: r for r in report.rows}
    assert set(by_key) == {"TSH", "FT4", "VITD", "FERRITIN"}
    assert by_key["VITD"].value == "62" and by_key["VITD"].unit == "nmol/L"
    assert report.metadata.sex == "M" and report.metadata.age == 55
    assert report.metadata.lab_provider == "Northside Pathology"


def test_parse_line_with_spaced_unit_and_qualifier():
    row = parse_line("Anti TPO Antibodies   <9   IU / mL", 0)
    assert row.marker_key == "TPOAB"
    assert row.value == "9" and row.qualifier == "<"
    assert row.unit.replace(" ", "") == "IU/mL"


def test_parser_never_extracts_names():
    report = parse_report_text(REPORT_A)
    assert "Jane" not in str(report.metadata.to_dict())


def test_flag_between_value_and_unit_and_earliest_value_wins():
    report = parse_report_text(
        [
            "Investigation                     Observed Value    Units       Biological Ref. Interval",
            "TSH 3RD GENERATION                5.40 H            mIU/L       0.400 - 4.000",
            "FREE T3 (FT3)                     4.46              pmol/L      3.10 - 6.80",
            "VITAMIN D 25 OH                   9.37 L            ng/mL       20.0 - 50.1",
        ]
    )
    rows = {r.marker_key: r for r in report.rows}
    assert rows["TSH"].value == "5.40" and rows["TSH"].unit == "mIU/L" and rows["TSH"].flag == "H"
    assert rows["FT3"].value == "4.46" and rows["FT3"].unit == "pmol/L"
    assert (
        rows["VITD"].value == "9.37" and rows["VITD"].unit == "ng/mL" and rows["VITD"].flag == "L"
    )
    assert rows["TSH"].reference_text == "0.400 - 4.000"
