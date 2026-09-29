"""Schema 2 -- ExtractedReport (silver layer).

The canonical OCR/parse output for one document: verbatim from the page,
nothing normalized yet. `rows[]` is the join key Week 3's normalizer
consumes -- one row per biomarker occurrence, still carrying the raw
analyte string, raw unit, and raw reference range exactly as printed.
Keeping raw and normalized separate (see BiomarkerObservation) is what
makes a bad LOINC mapping auditable later: you can always see what the
page actually said.
"""


from pydantic import BaseModel, ConfigDict, Field

from bda_engine.schemas.common import Comparator, FlagRaw, Sex

SCHEMA_VERSION = "1.0.0"


class PageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_no: int = Field(..., ge=1)
    width: float
    height: float
    rotation: float = 0.0
    mean_word_confidence: float | None = Field(
        default=None, ge=0.0, le=100.0
    )


class ExtractionMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str          # "text_layer" | "tesseract" | "paddle" | "layoutlmv3"
    engine_version: str | None = None
    layout_model: str | None = None
    duration_ms: int = Field(..., ge=0)
    pages: list[PageInfo] = Field(default_factory=list)


class PatientContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_years: float | None = Field(default=None, ge=0, le=130)
    age_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    sex: Sex | None = None
    sex_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class LabInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_name_raw: str | None = None
    provider_id: str | None = None
    accession_no: str | None = None
    collected_at: str | None = None  # ISO date/datetime string, best-effort parse
    reported_at: str | None = None


class PanelInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    panel_name_raw: str
    page_no: int = Field(..., ge=1)
    table_index: int = Field(..., ge=0)


class BBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x0: float
    y0: float
    x1: float
    y1: float


class FieldConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analyte: float = Field(..., ge=0.0, le=1.0)
    value: float = Field(..., ge=0.0, le=1.0)
    unit: float = Field(..., ge=0.0, le=1.0)
    range: float = Field(..., ge=0.0, le=1.0)


class ExtractedRow(BaseModel):
    """One biomarker occurrence, exactly as it appeared on the page."""

    model_config = ConfigDict(extra="forbid")

    row_id: str
    page_no: int = Field(..., ge=1)
    table_index: int = Field(..., ge=0)
    row_index: int = Field(..., ge=0)

    analyte_name_raw: str

    value_raw: str
    value_numeric: float | None = None
    comparator: Comparator = Comparator.NONE
    is_numeric: bool

    unit_raw: str | None = None

    reference_range_raw: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    ref_operator: Comparator | None = None

    flag_raw: FlagRaw | None = None
    method_raw: str | None = None

    bbox: BBox | None = None
    confidence: FieldConfidence
    needs_review: bool = False


class ExtractedReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION

    document_id: str
    patient_id: str

    extraction: ExtractionMeta
    patient_context: PatientContext = Field(default_factory=PatientContext)
    lab: LabInfo = Field(default_factory=LabInfo)
    panels: list[PanelInfo] = Field(default_factory=list)
    rows: list[ExtractedRow] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
