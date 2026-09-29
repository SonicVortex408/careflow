"""
Week 1, Step 1.3: the synthetic data generator CLI.

Produces two related but distinct outputs -- keeping them separate is
deliberate, see the module-level note in each section below:

1. data_lake/gold/biomarker_observations/, prom_responses/, patients/,
   raw_documents/ -- Parquet, for ALL `--patients` patients. This is
   the analytics-lake corpus (Phase 4 clustering work): every patient's
   biomarkers are known directly (is_synthetic=True,
   mapping_method="exact"), with no OCR or text normalization involved.

2. data_lake/bronze/lab_reports/<document_id>.pdf +
   data_lake/bronze/ground_truth/<document_id>.json -- for a much
   smaller `--pdf-count` subset. These are actual rendered documents
   (some scan-simulated, i.e. no text layer) whose ground_truth.json is
   what the Week 2 OCR pipeline and Week 3 normalizer are scored
   against. Running OCR+normalization on these and writing THEIR
   output back into biomarker_observations would double-count those
   patients against their already-known direct values, so that wiring
   is deliberately NOT done here -- evaluation/ (Phase 4) is where OCR
   output gets compared to ground_truth.json, not merged into gold/.

Usage:
    uv run generate-synthetic-data --patients 50000 --pdf-count 2000 --seed 42
"""

import hashlib
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import typer
from faker import Faker

from bda_engine.generate.distributions import (
    sample_demographics,
    sample_markers,
    sample_phenotype,
    sample_proms,
)
from bda_engine.generate.render_pdf import LAYOUTS, build_printed_rows, render_report_pdf
from bda_engine.generate.scan_simulate import simulate_scan
from bda_engine.reference_data import load_biomarkers, load_lab_providers
from bda_engine.schemas.prom_response import PromDerived

app = typer.Typer(add_completion=False)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _prom_derived(values: dict) -> PromDerived:
    from bda_engine.schemas.common import PromItemCode

    fatigue = values[PromItemCode.FATIGUE_SEVERITY.value] / 10.0
    fog = values[PromItemCode.BRAIN_FOG_FREQUENCY.value] / 4.0
    hair = values[PromItemCode.HAIR_LOSS.value] / 4.0
    return PromDerived(
        fatigue_score=fatigue,
        brain_fog_score=fog,
        hair_loss_score=hair,
        composite_burden=(fatigue + fog + hair) / 3.0,
    )


def _generate_one_patient(
    index: int,
    np_rng: np.random.Generator,
    py_rng: random.Random,
    faker: Faker,
    base_date: date,
    lab_provider_names: list[str],
):
    patient_id = f"SYN{index:08d}"
    phenotype = sample_phenotype(np_rng)
    age, sex = sample_demographics(np_rng)
    markers_canonical = {k.value: v for k, v in sample_markers(phenotype, sex, np_rng).items()}
    proms = {k.value: v for k, v in sample_proms(phenotype, np_rng).items()}

    panel_date = base_date - timedelta(days=int(np_rng.integers(0, 730)))

    patient_row = {
        "patient_id": patient_id,
        "age_years": age,
        "sex": sex,
        "region": faker.state(),
        # NEVER feed this to a model -- see distributions.py's R2 note.
        "phenotype_internal": phenotype.key,
        "is_synthetic": True,
    }

    biomarkers = load_biomarkers()
    observation_rows = []
    for biomarker_key, value in markers_canonical.items():
        ref = biomarkers[biomarker_key]
        observation_rows.append({
            "observation_id": f"{patient_id}-{biomarker_key}-direct",
            "document_id": f"synthetic:{patient_id}",
            "row_id": f"synthetic:{patient_id}:{biomarker_key}",
            "patient_id": patient_id,
            "biomarker_key": biomarker_key,
            "loinc_code": ref.loinc_code,
            "mapping_confidence": 1.0,
            "mapping_method": "exact",
            "value_canonical": value,
            "unit_canonical": ref.canonical_unit,
            "value_source": value,
            "unit_source": ref.canonical_unit,
            "conversion_factor": 1.0,
            "conversion_source": "direct synthetic value, no conversion",
            "lab_provider_id": None,
            "patient_age_years": age,
            "patient_sex": sex,
            "collected_at": datetime.combine(panel_date, datetime.min.time()),
            "observed_month": panel_date.replace(day=1),
            "quality_status": "ok",
            "is_synthetic": True,
        })

    prom_row = {
        "response_id": f"{patient_id}-prom",
        "patient_id": patient_id,
        "instrument": "CAREFLOW_PROM_V1",
        "submitted_at": datetime.combine(panel_date, datetime.min.time()),
        "survey_date": panel_date,
        **{f"item_{k.lower()}": v for k, v in proms.items()},
        **{f"derived_{k}": v for k, v in _prom_derived(proms).model_dump().items()},
        "is_synthetic": True,
    }

    return patient_row, observation_rows, prom_row, phenotype, markers_canonical


def _render_documents_for_patient(
    patient_id: str,
    markers_canonical: dict,
    py_rng: random.Random,
    lab_provider_names: list[str],
    age: float,
    sex: str,
    out_dir: Path,
    doc_index: int,
    scan_fraction: float,
    base_date: date,
):
    """Renders one clean PDF and, with probability scan_fraction, one
    additional scan-simulated PDF for the same underlying data. Returns
    (raw_document_rows, ground_truth_written_paths)."""

    lab_report_dir = out_dir / "bronze" / "lab_reports"
    ground_truth_dir = out_dir / "bronze" / "ground_truth"

    n_rows = py_rng.randint(3, 9)
    rows = build_printed_rows(markers_canonical, py_rng, max_rows=n_rows)
    layout = py_rng.choice(LAYOUTS)
    lab_name = py_rng.choice(lab_provider_names)
    accession = f"ACC-{doc_index:08d}"
    ingest_date = base_date

    raw_document_rows = []

    def _write_ground_truth(document_id: str, has_text_layer: bool, pdf_path: Path):
        payload = {
            "document_id": document_id,
            "patient_id": patient_id,
            "has_text_layer": has_text_layer,
            "layout": layout,
            "lab_provider_name": lab_name,
            "patient_age_years": age,
            "patient_sex": sex,
            "rows": [
                {
                    "row_id": f"{document_id}:row{r.row_index}",
                    "analyte_name_raw": r.analyte_name_raw,
                    "value_raw": r.value_raw,
                    "value_printed_numeric": r.value_printed_numeric,
                    "unit_raw": r.unit_raw,
                    "reference_range_raw": r.reference_range_raw,
                    "true_biomarker_key": r.biomarker_key,
                    "true_loinc_code": r.loinc_code,
                    "true_value_canonical": r.value_canonical,
                    "true_unit_canonical": r.unit_canonical,
                }
                for r in rows
            ],
        }
        ground_truth_dir.mkdir(parents=True, exist_ok=True)
        gt_path = ground_truth_dir / f"{document_id}.json"
        gt_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return gt_path

    # --- Clean (text-layer) document ---
    clean_id = f"DOC{doc_index:08d}"
    clean_path = lab_report_dir / f"{clean_id}.pdf"
    page_count = render_report_pdf(
        out_path=clean_path, document_id=clean_id, patient_id=patient_id,
        lab_provider_name=lab_name, patient_age_years=age, patient_sex=sex,
        rows=rows, layout=layout, accession_no=accession,
    )
    _write_ground_truth(clean_id, has_text_layer=True, pdf_path=clean_path)
    raw_document_rows.append({
        "document_id": clean_id,
        "patient_id": patient_id,
        "sha256": _sha256_file(clean_path),
        "original_name": clean_path.name,
        "stored_uri": str(clean_path),
        "mime_type": "application/pdf",
        "size_bytes": clean_path.stat().st_size,
        "page_count": page_count,
        "has_text_layer": True,
        "source_channel": "synthetic",
        "is_synthetic": True,
        "ingest_status": "extracted",
        "ingest_date": ingest_date,
    })

    # --- Scan-simulated (no text layer) document, some fraction of the time ---
    if py_rng.random() < scan_fraction:
        scanned_id = f"DOC{doc_index:08d}S"
        scanned_path = lab_report_dir / f"{scanned_id}.pdf"
        simulate_scan(clean_path, scanned_path, py_rng, dpi=py_rng.choice([200, 250, 300]))
        _write_ground_truth(scanned_id, has_text_layer=False, pdf_path=scanned_path)
        raw_document_rows.append({
            "document_id": scanned_id,
            "patient_id": patient_id,
            "sha256": _sha256_file(scanned_path),
            "original_name": scanned_path.name,
            "stored_uri": str(scanned_path),
            "mime_type": "application/pdf",
            "size_bytes": scanned_path.stat().st_size,
            "page_count": page_count,
            "has_text_layer": False,
            "source_channel": "synthetic",
            "is_synthetic": True,
            "ingest_status": "extracted",
            "ingest_date": ingest_date,
        })

    return raw_document_rows


def generate(
    patients: int,
    pdf_count: int,
    seed: int,
    out_dir: Path,
    scan_fraction: float = 0.4,
) -> dict:
    """Programmatic entry point (the `uv run generate-synthetic-data` CLI
    below is a thin wrapper). Returns a summary dict; writes Parquet
    under out_dir/gold and out_dir/silver, and documents under
    out_dir/bronze."""

    np_rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    faker = Faker()
    Faker.seed(seed)

    lab_provider_names = sorted({r.canonical_name for r in load_lab_providers()})
    base_date = date.today()

    patient_rows, observation_rows, prom_rows, raw_document_rows = [], [], [], []
    doc_index = 0

    pdf_count = min(pdf_count, patients)

    for i in range(patients):
        patient_row, obs_rows, prom_row, phenotype, markers_canonical = _generate_one_patient(
            i, np_rng, py_rng, faker, base_date, lab_provider_names
        )
        patient_rows.append(patient_row)
        observation_rows.extend(obs_rows)
        prom_rows.append(prom_row)

        if i < pdf_count:
            doc_index += 1
            raw_document_rows.extend(
                _render_documents_for_patient(
                    patient_id=patient_row["patient_id"],
                    markers_canonical=markers_canonical,
                    py_rng=py_rng,
                    lab_provider_names=lab_provider_names,
                    age=patient_row["age_years"],
                    sex=patient_row["sex"],
                    out_dir=out_dir,
                    doc_index=doc_index,
                    scan_fraction=scan_fraction,
                    base_date=base_date,
                )
            )

    _write_parquet(out_dir, patient_rows, observation_rows, prom_rows, raw_document_rows)

    return {
        "patients": len(patient_rows),
        "biomarker_observations": len(observation_rows),
        "prom_responses": len(prom_rows),
        "documents_rendered": len(raw_document_rows),
        "out_dir": str(out_dir),
    }


def _write_parquet(out_dir, patient_rows, observation_rows, prom_rows, raw_document_rows):
    gold_dir = out_dir / "gold"
    silver_dir = out_dir / "silver"
    bronze_dir = out_dir / "bronze"
    for d in (gold_dir, silver_dir, bronze_dir):
        d.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(patient_rows).to_parquet(
        gold_dir / "patients.parquet", index=False
    )

    obs_df = pd.DataFrame(observation_rows)
    if not obs_df.empty:
        obs_df["observed_month"] = pd.to_datetime(obs_df["observed_month"])
        (gold_dir / "biomarker_observations").mkdir(parents=True, exist_ok=True)
        obs_df.to_parquet(
            gold_dir / "biomarker_observations", index=False,
            partition_cols=["biomarker_key"],
        )

    prom_df = pd.DataFrame(prom_rows)
    if not prom_df.empty:
        prom_df["survey_date"] = pd.to_datetime(prom_df["survey_date"])
        prom_df.to_parquet(silver_dir / "prom_responses.parquet", index=False)

    raw_df = pd.DataFrame(raw_document_rows)
    if not raw_df.empty:
        # Partitioned by ingest_date, matching the schema design (see
        # WEEKS_1-3_STATUS_AND_PLAN.md section 3.1) -- NOT by
        # has_text_layer: a boolean Hive partition value round-trips as
        # the *string* "true"/"false" on read-back (DuckDB and Spark
        # both do this), silently changing its type. Keeping
        # has_text_layer as a plain column avoids that footgun.
        raw_df["ingest_date"] = pd.to_datetime(raw_df["ingest_date"])
        (bronze_dir / "raw_documents").mkdir(parents=True, exist_ok=True)
        raw_df.to_parquet(
            bronze_dir / "raw_documents", index=False,
            partition_cols=["ingest_date"],
        )


@app.command()
def main(
    patients: int = typer.Option(50000, help="Number of synthetic patients to generate."),
    pdf_count: int = typer.Option(2000, help="Number of patients to also render as PDF documents."),
    seed: int = typer.Option(42, help="Random seed -- same seed reproduces the same corpus."),
    out: Path = typer.Option(Path("data_lake"), help="Output directory."),
    scan_fraction: float = typer.Option(
        0.4, help="Fraction of rendered documents to also scan-simulate (no text layer)."
    ),
):
    """Generate the Week 1 synthetic biomarker + PROM + lab-report corpus."""

    summary = generate(
        patients=patients, pdf_count=pdf_count, seed=seed,
        out_dir=out, scan_fraction=scan_fraction,
    )
    typer.echo(json.dumps(summary, indent=2))


if __name__ == "__main__":
    app()
