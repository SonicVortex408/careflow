"""
Small shared enums for the Week 2/3 services (OCR extraction,
normalization). Deliberately a tiny standalone copy of the same
concept in bda_engine/src/bda_engine/schemas/common.py, not an import
of it -- ai-service does not depend on the bda_engine package (see
app/services/reference_data.py's module docstring for why).
"""

from enum import Enum


class Comparator(str, Enum):
    LT = "<"
    GT = ">"
    EQ = "="
    NONE = "none"


class QualityStatus(str, Enum):
    OK = "ok"
    SUSPECT = "suspect"
    REJECTED = "rejected"


class FlagRaw(str, Enum):
    HIGH = "H"
    LOW = "L"
    NORMAL = "N"
