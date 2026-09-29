"""Centralized settings for ai-service.

Every environment variable the service reads goes through this module.
Nothing here is imported eagerly by application code at *module import*
time in a way that requires a value to be present -- settings are read
lazily via ``get_settings()`` so the app can start (and ``GET /`` can
answer) even when optional integrations (Groq, Redis, Neo4j) are not
configured yet. Endpoints that need a given setting validate it at
request time and return a clear error instead of crashing the process.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider -----------------------------------------------
    # LLM_PROVIDER selects which client nodes.py builds; LLM_MODEL is the
    # provider-qualified model id (e.g. "groq:openai/gpt-oss-20b",
    # "google_genai:gemini-2.5-flash"). Both were previously hardcoded.
    llm_provider: str = Field(default="groq")
    llm_model: str = Field(default="groq:openai/gpt-oss-20b")
    groq_api_key: str | None = Field(default=None)
    google_api_key: str | None = Field(default=None)

    # --- CORS ---------------------------------------------------------
    cors_allow_origins: str = Field(
        default="http://localhost:5173"
    )

    # --- Celery / Redis (Week 2) --------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str | None = Field(default=None)
    celery_result_backend: str | None = Field(default=None)

    # --- OCR feature flags (Week 2) ------------------------------------
    ocr_engine: str = Field(default="tesseract")  # tesseract | paddle
    enable_layoutlmv3: bool = Field(default=False)
    tesseract_cmd: str | None = Field(default=None)

    # --- Neo4j (future GraphRAG phase) ---------------------------------
    neo4j_uri: str | None = Field(default=None)
    neo4j_user: str | None = Field(default=None)
    neo4j_password: str | None = Field(default=None)

    # --- Data lake / bda_engine handoff --------------------------------
    model_artifact_dir: str | None = Field(default=None)

    @property
    def celery_broker_url_resolved(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def celery_result_backend_resolved(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Safe to call from any module at any time."""
    return Settings()
