"""Lazy, configurable chat-model factory (architecture decision 10).

Nothing is constructed at import time, so a missing API key never prevents the
service from starting. ``get_chat_model()`` returns None when no provider is
usable; callers then fall back to deterministic templated output.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_PROVIDERS = {
    "groq": ("groq", "groq_api_key"),
    "google": ("google_genai", "google_api_key"),
}


@lru_cache(maxsize=1)
def get_chat_model():
    s = get_settings()
    provider = s.llm_provider.lower().strip()
    if provider in ("", "none", "off"):
        return None
    if provider not in _PROVIDERS:
        logger.warning("Unknown LLM_PROVIDER=%s; LLM disabled", provider)
        return None
    lc_provider, key_field = _PROVIDERS[provider]
    api_key = getattr(s, key_field)
    if not api_key:
        logger.warning(
            "LLM_PROVIDER=%s but %s is not set; using templated output", provider, key_field.upper()
        )
        return None
    try:
        from langchain.chat_models import init_chat_model

        return init_chat_model(
            f"{lc_provider}:{s.llm_model}", api_key=api_key, temperature=s.llm_temperature
        )
    except Exception as exc:  # noqa: BLE001 - provider SDK errors must not crash the app
        logger.error("Could not initialise LLM (%s): %s", provider, type(exc).__name__)
        return None


def llm_status() -> dict:
    s = get_settings()
    return {
        "provider": s.llm_provider,
        "model": s.llm_model,
        "configured": get_chat_model() is not None,
    }
