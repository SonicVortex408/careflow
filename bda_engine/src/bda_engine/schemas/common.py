"""Shared enums and small value types used across all four schemas.

Field lists here are the contract every later phase (OCR extraction,
normalization, the ai-service worker tasks) codes against. Treat any
addition as a schema-version bump -- see SCHEMA_VERSION in each schema
module.
"""

from enum import Enum


class SourceChannel(str, Enum):
    PATIENT_UPLOAD = "patient_upload"
    SYNTHETIC = "synthetic"
    BULK = "bulk"


class IngestStatus(str, Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    OCR_RUNNING = "ocr_running"
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    READY = "ready"
    FAILED = "failed"


class Comparator(str, Enum):
    LT = "<"
    GT = ">"
    EQ = "="
    NONE = "none"


class FlagRaw(str, Enum):
    HIGH = "H"
    LOW = "L"
    NORMAL = "N"


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class BiomarkerKey(str, Enum):
    """The 9 analytes in scope (docs/ARCHITECTURE.md section 1)."""

    TSH = "TSH"
    FT3 = "FT3"
    FT4 = "FT4"
    ANTI_TPO = "ANTI_TPO"
    VIT_D_25OH = "VIT_D_25OH"
    VIT_B12 = "VIT_B12"
    FERRITIN = "FERRITIN"
    MAGNESIUM = "MAGNESIUM"
    ZINC = "ZINC"


class MappingMethod(str, Enum):
    EXACT = "exact"
    SYNONYM = "synonym"
    FUZZY = "fuzzy"
    MANUAL = "manual"
    UNMAPPED = "unmapped"


class RefBasis(str, Enum):
    LAB_STATED = "lab_stated"
    FALLBACK_DEFAULT = "fallback_default"


class QualityStatus(str, Enum):
    OK = "ok"
    SUSPECT = "suspect"
    REJECTED = "rejected"


class PromItemCode(str, Enum):
    FATIGUE_SEVERITY = "FATIGUE_SEVERITY"
    BRAIN_FOG_FREQUENCY = "BRAIN_FOG_FREQUENCY"
    HAIR_LOSS = "HAIR_LOSS"


class PromScaleType(str, Enum):
    NRS = "nrs"       # numeric rating scale, e.g. 1-10
    ORDINAL = "ordinal"  # fixed labelled steps, e.g. 0-4 frequency/severity
