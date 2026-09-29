"""Runtime configuration (environment variables, with local-dev defaults)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent


@dataclass(frozen=True)
class Settings:
    etl_engine: str  # spark | duckdb
    seed: int
    n_patients: int
    n_pdfs: int
    data_dir: Path
    artifact_dir: Path
    model_semver: str
    spark_master: str

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def holdout_dir(self) -> Path:
        """Generator parameters + OCR ground truth. Never read by ETL or models (risk R2)."""
        return self.data_dir / "holdout"

    @property
    def lake_dir(self) -> Path:
        return self.data_dir / "lake"


def get_settings(**overrides) -> Settings:
    values = dict(
        etl_engine=os.getenv("ETL_ENGINE", "duckdb").lower(),
        seed=int(os.getenv("SYNTHETIC_SEED", "42")),
        n_patients=int(os.getenv("N_PATIENTS", "50000")),
        n_pdfs=int(os.getenv("N_PDFS", "500")),
        data_dir=Path(os.getenv("BDA_DATA_DIR", PACKAGE_DIR / "data")),
        artifact_dir=Path(os.getenv("MODEL_ARTIFACT_DIR", REPO_ROOT / "models")),
        model_semver=os.getenv("MODEL_SEMVER", "1.0.0"),
        spark_master=os.getenv("SPARK_MASTER", "local[*]"),
    )
    values.update(overrides)
    if values["etl_engine"] not in ("spark", "duckdb"):
        raise ValueError("ETL_ENGINE must be 'spark' or 'duckdb'")
    return Settings(**values)
