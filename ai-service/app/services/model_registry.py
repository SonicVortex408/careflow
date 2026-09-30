"""Loads bda_engine artifacts through manifest.json (sha256-verified, cached).

The service starts without artifacts; inference endpoints then report
``models_available: false`` instead of failing.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from polymarker_common.catalog import catalog_version

logger = logging.getLogger(__name__)


class ArtifactError(RuntimeError):
    pass


class ModelRegistry:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self._lock = threading.Lock()
        self._cache: dict[str, Any] = {}
        self._manifest: dict | None = None
        self._error: str | None = None

    @property
    def manifest(self) -> dict | None:
        if self._manifest is None and self._error is None:
            path = self.dir / "manifest.json"
            if not path.exists():
                self._error = f"no manifest.json in {self.dir}"
            else:
                manifest = json.loads(path.read_text(encoding="utf-8"))
                if manifest.get("catalog_version") != catalog_version():
                    self._error = f"artifact catalog_version {manifest.get('catalog_version')} != service {catalog_version()}"
                else:
                    self._manifest = manifest
            if self._error:
                logger.warning("Model artifacts unavailable: %s", self._error)
        return self._manifest

    @property
    def available(self) -> bool:
        return self.manifest is not None

    def _path(self, name: str) -> Path:
        if not self.available:
            raise ArtifactError(self._error or "artifacts unavailable")
        entry = self.manifest["artifacts"].get(name)
        if entry is None:
            raise ArtifactError(f"artifact '{name}' not in manifest")
        path = self.dir / entry["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            raise ArtifactError(f"sha256 mismatch for {entry['path']}")
        return path

    def json(self, name: str) -> dict:
        with self._lock:
            if name not in self._cache:
                self._cache[name] = json.loads(self._path(name).read_text(encoding="utf-8"))
            return self._cache[name]

    def booster(self, name: str):
        with self._lock:
            if name not in self._cache:
                import xgboost as xgb

                booster = xgb.Booster()
                booster.load_model(str(self._path(name)))
                self._cache[name] = booster
            return self._cache[name]

    def status(self) -> dict:
        m = self.manifest
        if m is None:
            return {"available": False, "error": self._error, "dir": str(self.dir)}
        return {
            "available": True,
            "semver": m["semver"],
            "seed": m["seed"],
            "created_at": m["created_at"],
            "catalog_version": m["catalog_version"],
            "artifacts": sorted(m["artifacts"]),
            "summary": m.get("summary", {}),
            "label": m["label"],
        }


@lru_cache(maxsize=1)
def get_registry() -> ModelRegistry:
    return ModelRegistry(get_settings().model_artifact_dir)
