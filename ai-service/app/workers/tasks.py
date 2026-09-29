"""
Week 2, Step 2.2: the Celery task wrapping the pipeline.

One task, not the four-stage chain (ocr -> normalize -> quality ->
persist) originally sketched in docs/ARCHITECTURE.md's sequence
diagram: app/ocr/pipeline.py's process_document() already runs those
four stages in-process in well under a second for a single-digit-page
document (see tests/test_pipeline.py), so splitting them into separate
queued Celery stages would add broker round-trips without buying
anything -- there's no independent unit of work to parallelize between
"OCR this document" and "normalize its rows" the way there is between
"OCR page 1" and "OCR page 2" of the same document.

Per-page fan-out (chord(ocr_page.s(p) for p in pages)) for large
multi-page documents is the concrete case where a real chain/chord
would earn its complexity -- not implemented here; app/ocr/raster.py
and tesseract_engine.py already operate per-page internally, so this
is a matter of adding a chord around them, not a redesign, when a
multi-page corpus makes it worth it (see
docs/WEEKS_1-3_STATUS_AND_PLAN.md Week 2 acceptance criteria for the
throughput targets that would motivate this).

Idempotency: keyed by the document's sha256 (computed by the caller,
e.g. backend's documentController.js or a bulk-ingest script) as part
of `document_id` construction upstream -- this task itself is a pure
function of (pdf_path, document_id, patient_id) and does not persist
anything itself (see the module docstring below on why).
"""

from pathlib import Path

from celery.utils.log import get_task_logger

from app.ocr.pipeline import DocumentResult, UnsupportedDocumentError, process_document
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


def _serialize_result(result: DocumentResult) -> dict:
    """Celery results must be JSON-serializable (the default backend
    serializer) -- process_document() returns frozen dataclasses, which
    aren't, so convert explicitly rather than relying on a serializer
    that happens to handle dataclasses today."""

    return {
        "document_id": result.document_id,
        "patient_id": result.patient_id,
        "has_text_layer": result.has_text_layer,
        "patient_age": result.patient_age,
        "patient_sex": result.patient_sex,
        "accession": result.accession,
        "lab_provider": result.lab_provider,
        "warnings": result.warnings,
        "observations": [
            {
                "row_id": obs.row_id,
                "biomarker_key": obs.biomarker_key,
                "loinc_code": obs.loinc_code,
                "mapping_method": obs.mapping_method,
                "mapping_confidence": obs.mapping_confidence,
                "value_canonical": obs.value_canonical,
                "unit_canonical": obs.unit_canonical,
                "value_source": obs.value_source,
                "unit_source": obs.unit_source,
                "ref_low_canonical": obs.ref_low_canonical,
                "ref_high_canonical": obs.ref_high_canonical,
                "quality_status": obs.quality_status,
                "needs_review": obs.needs_review,
                "analyte_name_raw": obs.analyte_name_raw,
                "value_raw": obs.value_raw,
                "reference_range_raw": obs.reference_range_raw,
                "ocr_confidence": obs.ocr_confidence,
            }
            for obs in result.observations
        ],
    }


@celery_app.task(
    bind=True,
    name="app.workers.tasks.process_document_task",
    max_retries=3,
    default_retry_delay=30,
)
def process_document_task(self, pdf_path: str, document_id: str, patient_id: str) -> dict:
    logger.info("processing document_id=%s patient_id=%s", document_id, patient_id)

    try:
        result = process_document(Path(pdf_path), document_id=document_id, patient_id=patient_id)
        return _serialize_result(result)

    except UnsupportedDocumentError as error:
        # Retrying won't help -- the engine this document needs isn't
        # available at all (e.g. Tesseract not installed). Fail now
        # with a clear reason rather than burning 3 retries pointlessly.
        logger.error("document_id=%s cannot be processed: %s", document_id, error)
        raise

    except Exception as error:
        logger.exception("document_id=%s failed, will retry: %s", document_id, error)
        raise self.retry(exc=error)
