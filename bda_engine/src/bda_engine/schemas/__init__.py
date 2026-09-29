from bda_engine.schemas.biomarker_observation import BiomarkerObservation
from bda_engine.schemas.extracted_report import ExtractedReport
from bda_engine.schemas.prom_response import PromResponse
from bda_engine.schemas.raw_document import RawDocument

ALL_SCHEMAS = {
    "raw_document": RawDocument,
    "extracted_report": ExtractedReport,
    "biomarker_observation": BiomarkerObservation,
    "prom_response": PromResponse,
}

__all__ = [
    "RawDocument",
    "ExtractedReport",
    "BiomarkerObservation",
    "PromResponse",
    "ALL_SCHEMAS",
]
