"""Load schema + seed (+ optional bda_engine artifacts) into Neo4j.

python -m graph_service.loader                      # schema + seed
python -m graph_service.loader --artifacts ../models  # also functional bands / correlations
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from graph_service.connector import Neo4jConnector, get_connector
from graph_service.cypher import SCHEMA_PATH, SEED_PATH, split_statements

logger = logging.getLogger("graph_service.loader")


def latest_manifest(artifact_dir: Path) -> dict | None:
    path = artifact_dir / "manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load(artifact_dir: Path | None = None) -> dict:
    connector = get_connector(require_neo4j=True)
    assert isinstance(connector, Neo4jConnector)
    counts = {"schema": 0, "seed": 0, "bands": 0, "correlations": 0}
    for stmt in split_statements(SCHEMA_PATH.read_text(encoding="utf-8")):
        connector._run(stmt)
        counts["schema"] += 1
    for stmt in split_statements(SEED_PATH.read_text(encoding="utf-8")):
        connector._run(stmt)
        counts["seed"] += 1
    if artifact_dir is not None:
        manifest = latest_manifest(artifact_dir)
        if manifest:
            bands_file = artifact_dir / manifest["artifacts"]["functional_bands"]["path"]
            bands = json.loads(bands_file.read_text(encoding="utf-8"))["bands"]
            functional = {k: v["functional"] for k, v in bands.items() if v.get("functional")}
            connector.upsert_functional_bands(functional)
            counts["bands"] = len(functional)
            corr_file = manifest["artifacts"].get("correlations")
            if corr_file:
                correlations = json.loads(
                    (artifact_dir / corr_file["path"]).read_text(encoding="utf-8")
                )
                connector.upsert_correlations(correlations["edges"])
                counts["correlations"] = len(correlations["edges"])
    connector.close()
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=None)
    args = parser.parse_args()
    print(json.dumps(load(args.artifacts), indent=2))


if __name__ == "__main__":
    main()
