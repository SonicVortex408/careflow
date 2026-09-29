"""
Regression test for the two import-time crashes documented in
CURRENT_STATE.md / WEEKS_1-3_STATUS_AND_PLAN.md:

  1. `init_chat_model` used to run at module import in app/agent/nodes.py,
     so importing app.main (and therefore every endpoint, including the
     health check) failed with `groq.GroqError` whenever GROQ_API_KEY
     was unset.
  2. `retriever.py` used to call `FAISS.load_local` at module import, so
     the app failed to import at all until `python -m app.retrieval.ingest`
     had been run once to create faiss_index/.

This test asserts the app imports and answers `/` and `/health` with
neither GROQ_API_KEY set nor faiss_index/ present -- the exact conditions
that broke both before.
"""

from starlette.testclient import TestClient


def test_app_imports_and_health_ok_without_groq_key_or_faiss_index(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    # Point the KB index at a directory that does not exist, to prove
    # the app doesn't need it to *import* -- only to actually retrieve.
    import app.retrieval.retriever as retriever_module

    retriever_module.INDEX_DIR = tmp_path / "does-not-exist"
    retriever_module.get_retriever.cache_clear()

    from app.main import app

    client = TestClient(app)

    root_response = client.get("/")
    assert root_response.status_code == 200

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"


def test_chat_model_construction_raises_a_clear_error_without_a_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    from app.agent.nodes import get_model_with_tools
    from app.core.config import get_settings

    get_settings.cache_clear()
    get_model_with_tools.cache_clear()

    try:
        import pytest

        with pytest.raises(RuntimeError, match="No API key configured"):
            get_model_with_tools()
    finally:
        get_settings.cache_clear()
        get_model_with_tools.cache_clear()
