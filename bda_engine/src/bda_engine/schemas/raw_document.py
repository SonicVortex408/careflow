"""Schema 1 -- RawDocument (bronze layer).

The bronze-layer record of one uploaded/generated document, before any
OCR has run. This is also the target shape backend/src/models/Document.js
should grow into (today it only has a subset of these fields -- see
docs/WEEKS_1-3_STATUS_AND_PLAN.md section 1.1).
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from bda_engine.schemas.common import IngestStatus, SourceChannel

SCHEMA_VERSION = "1.0.0"


class RawDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION

    document_id: str
    patient_id: str
    sha256: str = Field(..., min_length=64, max_length=64)

    original_name: str
    stored_uri: str
    mime_type: str
    size_bytes: int = Field(..., ge=0)

    page_count: int = Field(..., ge=1)
    has_text_layer: bool

    source_channel: SourceChannel
    is_synthetic: bool = False

    ingest_status: IngestStatus = IngestStatus.UPLOADED
    job_id: str | None = None
    ocr_engine: str | None = None
    ocr_engine_version: str | None = None

    # Partition key for the Parquet lake (bronze/raw_documents/).
    ingest_date: date

    created_at: datetime
    updated_at: datetime

    error_code: str | None = None
    error_message: str | None = None
