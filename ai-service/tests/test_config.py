"""
Settings must be constructible with zero environment variables set
(every field has a default) -- this is what lets the service start
without a .env file present, e.g. in CI or a fresh clone.
"""

from app.core.config import Settings, get_settings


def test_settings_construct_with_no_env(monkeypatch):
    for var in (
        "GROQ_API_KEY", "GOOGLE_API_KEY", "LLM_PROVIDER", "LLM_MODEL",
        "REDIS_URL", "CELERY_BROKER_URL", "OCR_ENGINE",
        "ENABLE_LAYOUTLMV3", "CORS_ALLOW_ORIGINS",
    ):
        monkeypatch.delenv(var, raising=False)

    # Avoid picking up a real .env file from the repo during this test.
    settings = Settings(_env_file=None)

    assert settings.llm_provider == "groq"
    assert settings.groq_api_key is None
    assert settings.ocr_engine == "tesseract"
    assert settings.enable_layoutlmv3 is False


def test_get_settings_is_cached():
    assert get_settings() is get_settings()


def test_cors_origins_list_splits_and_strips():
    settings = Settings(
        _env_file=None,
        cors_allow_origins="http://a.test, http://b.test ,,http://c.test",
    )
    assert settings.cors_origins_list == [
        "http://a.test", "http://b.test", "http://c.test",
    ]


def test_celery_broker_falls_back_to_redis_url():
    settings = Settings(_env_file=None, redis_url="redis://x:6379/2")
    assert settings.celery_broker_url_resolved == "redis://x:6379/2"
    assert settings.celery_result_backend_resolved == "redis://x:6379/2"

    settings = Settings(
        _env_file=None,
        redis_url="redis://x:6379/2",
        celery_broker_url="redis://y:6379/0",
    )
    assert settings.celery_broker_url_resolved == "redis://y:6379/0"
