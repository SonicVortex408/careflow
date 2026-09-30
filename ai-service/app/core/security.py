"""Input validation shared by every endpoint that touches the filesystem or a patient."""

from __future__ import annotations

import hmac
import re
from pathlib import Path

from fastapi import Header, HTTPException, status

from app.core.config import get_settings

_OBJECT_ID = re.compile(r"^[0-9a-f]{24}$")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def validate_object_id(value: str, field: str = "patient_id") -> str:
    """Patient/report ids are Mongo ObjectIds (24 hex). Anything else is rejected
    before it can reach a path join (closes the path-traversal surface)."""
    value = (value or "").strip().lower()
    if not _OBJECT_ID.match(value):
        raise HTTPException(status_code=422, detail=f"Invalid {field}")
    return value


def safe_child(base: Path, *parts: str) -> Path:
    """Join and assert the result stays inside ``base``."""
    base = base.resolve()
    target = base.joinpath(*parts).resolve()
    if base != target and base not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid path")
    return target


def safe_suffix(filename: str | None, allowed: tuple[str, ...]) -> str:
    suffix = Path(_SAFE_NAME.sub("_", filename or "")).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=415, detail=f"Unsupported file type. Allowed: {', '.join(allowed)}"
        )
    return suffix


async def require_internal_key(x_internal_key: str = Header(default="")) -> None:
    expected = get_settings().internal_api_key
    if expected and not hmac.compare_digest(x_internal_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal key")
