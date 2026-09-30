"""Service configuration. Every environment variable goes through ``Settings``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SERVICE_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SERVICE_ROOT / ".env", extra="ignore")

    # --- HTTP
    port: int = 8080
    cors_origins: str = "http://localhost:5173"
    # Shared secret the backend sends as X-Internal-Key. Empty = not enforced (dev only).
    internal_api_key: str = ""

    # --- LLM (constructed lazily; missing key => deterministic templated output)
    llm_provider: str = Field("groq", description="groq | google | none")
    llm_model: str = "openai/gpt-oss-20b"
    groq_api_key: str = ""
    google_api_key: str = ""
    llm_temperature: float = 0.2
    max_regenerations: int = 2

    # --- Jobs
    job_backend: str = Field(
        "celery",
        description="celery | modal (Modal functions) | local (in-process, dev/tests)",
    )
    # JOB_BACKEND=modal: deployed app name (deploy/modal_app.py) + job-state Dict.
    modal_app_name: str = "polymarker"
    modal_job_dict: str = "polymarker-jobs"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    job_result_ttl_seconds: int = 7 * 24 * 3600

    # --- Conversation memory
    checkpointer: str = Field("auto", description="auto | redis | memory")

    # --- Knowledge graph
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # --- OCR
    ocr_engine: str = "tesseract"
    enable_layoutlmv3: bool = False

    # --- Storage & artifacts
    model_artifact_dir: Path = REPO_ROOT / "models"
    patient_documents_dir: Path = SERVICE_ROOT / "patient_documents"
    patient_index_dir: Path = SERVICE_ROOT / "patient_faiss"
    knowledge_base_dir: Path = SERVICE_ROOT / "knowledge_base"
    kb_index_dir: Path = SERVICE_ROOT / "faiss_index"
    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
