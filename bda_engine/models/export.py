"""Versioned model artifacts + manifest (architecture decision 7: no MLflow).

Files are named ``{model}_{semver}_s{seed}.{ext}`` inside MODEL_ARTIFACT_DIR and
indexed by ``manifest.json``. The ai-service loads only through the manifest,
checks sha256, and refuses artifacts whose ``catalog_version`` differs from its
own biomarker catalog.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from polymarker_common.catalog import SYNTHETIC_DATA_LABEL, catalog_version


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ArtifactWriter:
    def __init__(self, directory: Path, semver: str, seed: int):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.semver = semver
        self.seed = seed
        self.entries: dict[str, dict] = {}

    def _name(self, model: str, ext: str) -> str:
        return f"{model}_{self.semver}_s{self.seed}.{ext}"

    def _register(self, logical: str, path: Path, kind: str) -> None:
        self.entries[logical] = {
            "path": path.name,
            "kind": kind,
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }

    def write_json(self, logical: str, payload: dict | list) -> Path:
        path = self.dir / self._name(logical, "json")
        if isinstance(payload, dict):
            payload = (
                {"label": SYNTHETIC_DATA_LABEL, **payload} if "label" not in payload else payload
            )
        path.write_text(json.dumps(payload, indent=1, sort_keys=False), encoding="utf-8")
        self._register(logical, path, "json")
        return path

    def write_booster(self, logical: str, booster) -> Path:
        path = self.dir / self._name(logical, "ubj")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "model.ubj"
            booster.save_model(str(tmp_path))
            path.write_bytes(tmp_path.read_bytes())
        self._register(logical, path, "xgboost_ubj")
        return path

    def write_manifest(self, extra: dict) -> Path:
        manifest = {
            "manifest_version": 1,
            "semver": self.semver,
            "seed": self.seed,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "catalog_version": catalog_version(),
            "label": SYNTHETIC_DATA_LABEL,
            "artifacts": self.entries,
            **extra,
        }
        path = self.dir / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return path
