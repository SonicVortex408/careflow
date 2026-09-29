"""Schema 3 -- BiomarkerObservation (gold layer).

The normalized entity: one row per (document, biomarker) after Week 3's
LOINC mapping and unit conversion have run. `mapping_method` and
`quality.status` are what make a bad row auditable and excludable from
feature vectors, rather than silently poisoning downstream models.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from bda_engine.schemas.common import BiomarkerKey, MappingMethod, QualityStatus, RefBasis, Sex

SCHEMA_VERSION = "1.0.0"


class QualityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    detail: str | None = None


class Quality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: QualityStatus = QualityStatus.OK
    checks: list[QualityCheck] = Field(default_factory=list)


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ocr_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    needs_review: bool = False
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class BiomarkerObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION

    observation_id: str
    document_id: str
    row_id: str
    patient_id: str

    biomarker_key: BiomarkerKey | None = None  # None when mapping_method == unmapped
    loinc_code: str | None = None
    loinc_long_name: str | None = None
    mapping_confidence: float = Field(..., ge=0.0, le=1.0)
    mapping_method: MappingMethod

    value_canonical: float | None = None
    unit_canonical: str | None = None

    value_source: float
    unit_source: str
    conversion_factor: float | None = None
    conversion_source: str | None = None

    ref_low_canonical: float | None = None
    ref_high_canonical: float | None = None
    ref_basis: RefBasis | None = None

    lab_provider_id: str | None = None
    patient_age_years: float | None = Field(default=None, ge=0, le=130)
    patient_sex: Sex | None = None

    collected_at: datetime | None = None
    # Partition key for gold/biomarker_observations/.
    observed_month: date

    quality: Quality = Field(default_factory=Quality)
    provenance: Provenance = Field(default_factory=Provenance)

    is_synthetic: bool = False
