"""
Schema 1-4 contract tests. These are the "four standardized schemas"
deliverable from Week 1 -- field lists here match
docs/WEEKS_1-3_STATUS_AND_PLAN.md section 3.1 exactly.
"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from bda_engine.schemas import (
    ALL_SCHEMAS,
    BiomarkerObservation,
    ExtractedReport,
    PromResponse,
    RawDocument,
)
from bda_engine.schemas.biomarker_observation import Provenance, Quality
from bda_engine.schemas.common import BiomarkerKey, MappingMethod, PromItemCode
from bda_engine.schemas.extracted_report import (
    ExtractedRow,
    ExtractionMeta,
    FieldConfidence,
)
from bda_engine.schemas.prom_response import ITEM_SCALES, PromDerived, PromItem

VALID_PATIENT_ID = "507f1f77bcf86cd799439011"


def _raw_document(**overrides):
    defaults = dict(
        document_id="doc-1",
        patient_id=VALID_PATIENT_ID,
        sha256="a" * 64,
        original_name="report.pdf",
        stored_uri="patient_documents/507f1f77bcf86cd799439011/report.pdf",
        mime_type="application/pdf",
        size_bytes=12345,
        page_count=2,
        has_text_layer=True,
        source_channel="patient_upload",
        ingest_date=date(2026, 1, 1),
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        updated_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    defaults.update(overrides)
    return RawDocument(**defaults)


class TestRawDocument:
    def test_minimal_valid_document(self):
        doc = _raw_document()
        assert doc.ingest_status.value == "uploaded"
        assert doc.is_synthetic is False

    def test_sha256_must_be_64_hex_chars(self):
        with pytest.raises(ValidationError):
            _raw_document(sha256="not-a-hash")

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            _raw_document(unexpected_field="x")

    def test_negative_size_rejected(self):
        with pytest.raises(ValidationError):
            _raw_document(size_bytes=-1)

    def test_zero_pages_rejected(self):
        with pytest.raises(ValidationError):
            _raw_document(page_count=0)

    def test_json_round_trip_serializes_enums_as_plain_strings(self):
        doc = _raw_document()
        dumped = doc.model_dump(mode="json")
        assert dumped["ingest_status"] == "uploaded"
        assert dumped["source_channel"] == "patient_upload"
        # Must be JSON-serializable with the stdlib encoder (no Enum leaks).
        import json
        json.dumps(dumped)


class TestExtractedReport:
    def _row(self, **overrides):
        defaults = dict(
            row_id="row-1",
            page_no=1,
            table_index=0,
            row_index=0,
            analyte_name_raw="Free T3",
            value_raw="4.2",
            value_numeric=4.2,
            is_numeric=True,
            unit_raw="pg/mL",
            reference_range_raw="2.3 - 4.2",
            confidence=FieldConfidence(analyte=0.95, value=0.99, unit=0.9, range=0.9),
        )
        defaults.update(overrides)
        return ExtractedRow(**defaults)

    def test_minimal_report_with_one_row(self):
        report = ExtractedReport(
            document_id="doc-1",
            patient_id=VALID_PATIENT_ID,
            extraction=ExtractionMeta(engine="text_layer", duration_ms=120),
            rows=[self._row()],
        )
        assert len(report.rows) == 1
        assert report.rows[0].comparator.value == "none"

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            FieldConfidence(analyte=1.5, value=0.5, unit=0.5, range=0.5)

    def test_row_defaults_needs_review_false(self):
        row = self._row()
        assert row.needs_review is False


class TestBiomarkerObservation:
    def _observation(self, **overrides):
        defaults = dict(
            observation_id="obs-1",
            document_id="doc-1",
            row_id="row-1",
            patient_id=VALID_PATIENT_ID,
            biomarker_key="FT3",
            loinc_code="3053-2",
            mapping_confidence=1.0,
            mapping_method="exact",
            value_canonical=4.2,
            unit_canonical="pmol/L",
            value_source=4.2,
            unit_source="pg/mL",
            observed_month=date(2026, 1, 1),
        )
        defaults.update(overrides)
        return BiomarkerObservation(**defaults)

    def test_minimal_observation(self):
        obs = self._observation()
        assert obs.biomarker_key == BiomarkerKey.FT3
        assert obs.quality.status.value == "ok"

    def test_unmapped_allows_null_biomarker_key(self):
        obs = self._observation(
            biomarker_key=None,
            loinc_code=None,
            mapping_confidence=0.0,
            mapping_method="unmapped",
            value_canonical=None,
            unit_canonical=None,
        )
        assert obs.biomarker_key is None
        assert obs.mapping_method == MappingMethod.UNMAPPED

    def test_mapping_confidence_bounds(self):
        with pytest.raises(ValidationError):
            self._observation(mapping_confidence=1.5)
        with pytest.raises(ValidationError):
            self._observation(mapping_confidence=-0.1)

    def test_quality_and_provenance_default_safely(self):
        obs = self._observation()
        assert obs.quality == Quality()
        assert obs.provenance == Provenance()


class TestPromResponse:
    def _items(self, fatigue=7, fog=2, hair=1):
        return [
            PromItem(
                item_code="FATIGUE_SEVERITY", value_raw=str(fatigue),
                value_numeric=fatigue, scale_min=1, scale_max=10, scale_type="nrs",
            ),
            PromItem(
                item_code="BRAIN_FOG_FREQUENCY", value_raw=str(fog),
                value_numeric=fog, scale_min=0, scale_max=4, scale_type="ordinal",
            ),
            PromItem(
                item_code="HAIR_LOSS", value_raw=str(hair),
                value_numeric=hair, scale_min=0, scale_max=4, scale_type="ordinal",
            ),
        ]

    def test_all_three_instruments_required(self):
        with pytest.raises(ValidationError, match="must include exactly"):
            PromResponse(
                response_id="r1",
                patient_id=VALID_PATIENT_ID,
                submitted_at=datetime(2026, 1, 1),
                survey_date=date(2026, 1, 1),
                items=self._items()[:2],
                derived=PromDerived(
                    fatigue_score=0.7, brain_fog_score=0.5,
                    hair_loss_score=0.25, composite_burden=0.48,
                ),
            )

    def test_valid_response_accepted(self):
        pr = PromResponse(
            response_id="r1",
            patient_id=VALID_PATIENT_ID,
            submitted_at=datetime(2026, 1, 1),
            survey_date=date(2026, 1, 1),
            items=self._items(),
            derived=PromDerived(
                fatigue_score=0.7, brain_fog_score=0.5,
                hair_loss_score=0.25, composite_burden=0.48,
            ),
        )
        assert pr.instrument == "CAREFLOW_PROM_V1"

    def test_item_value_outside_its_own_scale_rejected(self):
        with pytest.raises(ValidationError):
            PromItem(
                item_code="FATIGUE_SEVERITY", value_raw="15", value_numeric=15,
                scale_min=1, scale_max=10, scale_type="nrs",
            )

    def test_item_scales_cover_all_three_codes(self):
        assert set(ITEM_SCALES.keys()) == set(PromItemCode)
        assert ITEM_SCALES[PromItemCode.FATIGUE_SEVERITY] == ("nrs", 1, 10)
        assert ITEM_SCALES[PromItemCode.BRAIN_FOG_FREQUENCY] == ("ordinal", 0, 4)
        assert ITEM_SCALES[PromItemCode.HAIR_LOSS] == ("ordinal", 0, 4)


class TestAllSchemasExportJsonSchema:
    @pytest.mark.parametrize("name", list(ALL_SCHEMAS.keys()))
    def test_json_schema_export_does_not_raise(self, name):
        model = ALL_SCHEMAS[name]
        schema = model.model_json_schema()
        assert schema["title"] in (name, model.__name__)
        assert "properties" in schema
