import json
from pathlib import Path

import pytest

from bda_engine.config import get_settings
from bda_engine.scripts.generate_synthetic_data import generate


@pytest.fixture(scope="session")
def small_settings(tmp_path_factory) -> object:
    root = tmp_path_factory.mktemp("bda")
    s = get_settings(
        etl_engine="duckdb",
        n_patients=3000,
        n_pdfs=8,
        seed=7,
        data_dir=Path(root) / "data",
        artifact_dir=Path(root) / "artifacts",
    )
    generate(s.n_patients, s.n_pdfs, s.seed, s.data_dir)
    return s


@pytest.fixture(scope="session")
def etl_summary(small_settings):
    from bda_engine.etl.engine import get_engine
    from bda_engine.etl.lake import run_etl

    engine = get_engine("duckdb")
    try:
        return run_etl(engine, small_settings)
    finally:
        engine.close()


@pytest.fixture(scope="session")
def trained(small_settings, etl_summary):
    import bda_engine.models.functional_ranges as fr
    from bda_engine.pipeline import train

    fr.BOOTSTRAP = 3
    report = train(small_settings)
    manifest = json.loads((small_settings.artifact_dir / "manifest.json").read_text())
    return report, manifest
