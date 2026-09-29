"""
Week 2 Step 2.4 acceptance: table reconstruction recovers every printed
row correctly from real text-layer word output, across every
render_pdf.py layout.
"""

import pytest
from bda_engine.generate.render_pdf import LAYOUTS

from app.ocr.common import Word
from app.ocr.table_reconstruct import (
    default_known_units,
    detect_column_bands,
    group_words_into_lines,
    reconstruct_rows,
)
from app.ocr.text_layer import extract_words


def _w(text, x0, x1, y0=0, y1=10):
    return Word(text=text, x0=x0, y0=y0, x1=x1, y1=y1, page_no=1, confidence=1.0)


class TestGroupWordsIntoLines:
    def test_words_on_same_line_are_grouped(self, clean_pdf_factory):
        path, _ = clean_pdf_factory(layout="single_column")
        pages = extract_words(path)
        lines = group_words_into_lines(list(pages[0].words))

        assert len(lines) > 1
        for line in lines:
            # Every word in a recovered line should be roughly on the
            # same y-position.
            y_centers = [(w.y0 + w.y1) / 2 for w in line]
            assert max(y_centers) - min(y_centers) < 10

    def test_lines_are_sorted_top_to_bottom(self, clean_pdf_factory):
        path, _ = clean_pdf_factory(layout="single_column")
        pages = extract_words(path)
        lines = group_words_into_lines(list(pages[0].words))

        tops = [min(w.y0 for w in line) for line in lines]
        assert tops == sorted(tops)

    def test_empty_input_returns_empty_list(self):
        assert group_words_into_lines([]) == []


class TestReconstructRows:
    @pytest.mark.parametrize("layout", LAYOUTS)
    def test_recovers_every_printed_row_across_all_layouts(self, clean_pdf_factory, layout):
        path, ground_truth_rows = clean_pdf_factory(layout=layout, max_rows=6)
        pages = extract_words(path)

        candidates = reconstruct_rows(pages)
        recovered_values = {c.value_raw for c in candidates}
        expected_values = {r.value_raw for r in ground_truth_rows}

        assert expected_values <= recovered_values, (
            f"{layout}: missing {expected_values - recovered_values}"
        )

    def test_recovered_unit_matches_ground_truth(self, clean_pdf_factory):
        path, ground_truth_rows = clean_pdf_factory(layout="boxed_table", max_rows=6)
        pages = extract_words(path)
        candidates = reconstruct_rows(pages)

        by_value = {c.value_raw: c for c in candidates}
        for row in ground_truth_rows:
            candidate = by_value.get(row.value_raw)
            assert candidate is not None, row.value_raw
            assert candidate.unit_raw == row.unit_raw, (
                f"{row.biomarker_key}: expected unit {row.unit_raw!r}, got {candidate.unit_raw!r}"
            )

    def test_row_index_is_sequential(self, clean_pdf_factory):
        path, _ = clean_pdf_factory(layout="single_column", max_rows=6)
        pages = extract_words(path)
        candidates = reconstruct_rows(pages)
        assert [c.row_index for c in candidates] == list(range(len(candidates)))

    def test_non_data_lines_are_skipped(self, clean_pdf_factory):
        # multi_panel prints panel-name header lines ("Thyroid Panel")
        # with no numeric token -- these must not become rows.
        path, ground_truth_rows = clean_pdf_factory(layout="multi_panel", max_rows=6)
        pages = extract_words(path)
        candidates = reconstruct_rows(pages)

        assert not any("Panel" in c.analyte_name_raw for c in candidates)
        assert len(candidates) == len(ground_truth_rows)

    def test_bbox_is_well_formed(self, clean_pdf_factory):
        path, _ = clean_pdf_factory(layout="boxed_table", max_rows=6)
        pages = extract_words(path)
        candidates = reconstruct_rows(pages)

        for c in candidates:
            x0, y0, x1, y1 = c.bbox
            assert x0 < x1
            assert y0 < y1

    def test_confidence_is_full_for_text_layer_source(self, clean_pdf_factory):
        path, _ = clean_pdf_factory(layout="single_column", max_rows=6)
        pages = extract_words(path)
        candidates = reconstruct_rows(pages)
        assert all(c.confidence == 1.0 for c in candidates)


class TestDetectColumnBands:
    def test_single_column_yields_one_band(self):
        words = [_w("a", 10, 20), _w("b", 25, 35), _w("c", 40, 50)]
        bands = detect_column_bands(words)
        assert len(bands) == 1

    def test_wide_gap_splits_into_two_bands(self):
        left = [_w("left1", 10, 30), _w("left2", 35, 55)]
        right = [_w("right1", 300, 320), _w("right2", 325, 345)]
        bands = detect_column_bands(left + right)
        assert len(bands) == 2
        assert bands[0][1] < bands[1][0]

    def test_empty_input_returns_empty_list(self):
        assert detect_column_bands([]) == []


class TestKnownUnits:
    def test_known_units_is_nonempty_and_normalized(self):
        units = default_known_units()
        assert len(units) > 5
        assert "mIU/L" in units or "miu/l" in {u.lower() for u in units}
