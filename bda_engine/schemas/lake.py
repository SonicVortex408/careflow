"""Data-lake zone schemas (MELD-style multi-source lake).

raw/      as delivered by sources: per-lab CSV / JSONL exports, intake forms, PDFs
bronze/   raw rows unified to one column set, typed as strings, partitioned by lab
silver/   LOINC-coded SI biomarkers with quality flags; normalized PROMs
gold/     one row per patient (latest report) wide feature table + PROMs
extracted/ canonical JSON rows from batch OCR of PDFs
audit/    data-quality counts per source and check
"""

from __future__ import annotations

import pyarrow as pa

RAW_LAB_COLUMNS = [
    "report_id",
    "patient_id",
    "lab_provider",
    "collected_at",
    "raw_label",
    "raw_value",
    "raw_unit",
    "raw_reference",
    "flag",
]

PATIENTS = pa.schema(
    [
        ("patient_id", pa.string()),
        ("sex", pa.string()),
        ("birth_year", pa.int32()),
        ("site", pa.string()),
    ]
)

PDF_METADATA = pa.schema(
    [
        ("report_id", pa.string()),
        ("path", pa.string()),
        ("pages", pa.int32()),
        ("bytes", pa.int64()),
        ("sha256", pa.string()),
        ("ocr_method", pa.string()),
        ("mean_confidence", pa.float64()),
        ("completeness", pa.float64()),
        ("quality_issues", pa.int32()),
        ("seconds", pa.float64()),
    ]
)

EXTRACTED_ROWS = pa.schema(
    [
        ("report_id", pa.string()),
        ("marker", pa.string()),
        ("loinc", pa.string()),
        ("raw_label", pa.string()),
        ("raw_value", pa.string()),
        ("raw_unit", pa.string()),
        ("value_si", pa.float64()),
        ("unit_si", pa.string()),
        ("confidence", pa.float64()),
        ("ocr_method", pa.string()),
    ]
)

SILVER_BIOMARKERS = pa.schema(
    [
        ("report_id", pa.string()),
        ("patient_id", pa.string()),
        ("lab_provider", pa.string()),
        ("collected_at", pa.date32()),
        ("marker", pa.string()),
        ("loinc", pa.string()),
        ("panel", pa.string()),
        ("value_si", pa.float64()),
        ("unit_si", pa.string()),
        ("qualifier", pa.string()),
        ("label_confidence", pa.float64()),
        ("unit_inferred", pa.bool_()),
        ("implausible", pa.bool_()),
        ("decimal_misread_suspect", pa.bool_()),
        ("z_log", pa.float64()),
        ("iqr_outlier", pa.bool_()),
    ]
)

SILVER_PROMS = pa.schema(
    [
        ("report_id", pa.string()),
        ("patient_id", pa.string()),
        ("fatigue_severity", pa.int32()),
        ("brain_fog_frequency", pa.string()),
        ("hair_loss", pa.string()),
    ]
)

ALL = {
    "patients": PATIENTS,
    "pdf_metadata": PDF_METADATA,
    "extracted": EXTRACTED_ROWS,
    "silver_biomarkers": SILVER_BIOMARKERS,
    "silver_proms": SILVER_PROMS,
}
