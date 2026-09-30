"""PolyMarker on Modal: ai-service, job runner and Express backend in one app.

Deploy (see docs/DEPLOYMENT.md for the secrets):

    pip install modal && modal setup
    modal deploy deploy/modal_app.py
    modal run deploy/modal_app.py::migrate      # schema + Storage bucket (also runs on start)
    modal run deploy/modal_app.py::seed         # admin / clinician / patient accounts
    modal run deploy/modal_app.py::load_graph   # only with Neo4j Aura (NEO4J_URI)

Endpoints (https://<workspace>--<label>.modal.run):

    polymarker-api   Express API gateway -> VITE_API_BASE_URL = <url>/api
    polymarker-ai    FastAPI ai-service; public URL, but every /api route needs
                     the X-Internal-Key that only the backend holds

Every function scales to zero when idle, so a demo deployment stays inside
Modal's monthly free credits. The first request after an idle period waits for
a cold start (a few seconds for the API, ~10-20 s for the ai-service).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "polymarker"  # must match MODAL_APP_NAME in the ai-service settings

app = modal.App(APP_NAME)

IGNORE = ["**/.venv", "**/__pycache__", "**/.pytest_cache", "**/.ruff_cache", "**/node_modules", "**/.env"]

# --- ai-service ---------------------------------------------------------------

ai_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("tesseract-ocr", "tesseract-ocr-eng", "fonts-dejavu-core")
    .pip_install("uv==0.8.17")
    .add_local_dir(ROOT / "common", "/srv/common", copy=True, ignore=IGNORE)
    .add_local_dir(ROOT / "graph_service", "/srv/graph_service", copy=True, ignore=IGNORE)
    .add_local_file(ROOT / "ai-service/pyproject.toml", "/srv/ai-service/pyproject.toml", copy=True)
    .add_local_file(ROOT / "ai-service/uv.lock", "/srv/ai-service/uv.lock", copy=True)
    .add_local_file(ROOT / "ai-service/README.md", "/srv/ai-service/README.md", copy=True)
    # Locked dependencies (incl. common + graph_service) into the image's Python.
    .run_commands(
        "cd /srv/ai-service && UV_PROJECT_ENVIRONMENT=/usr/local "
        "uv sync --frozen --no-dev --no-install-project --inexact"
    )
    .env(
        {
            "PYTHONPATH": "/srv/ai-service",
            "JOB_BACKEND": "modal",
            "MODAL_APP_NAME": APP_NAME,
            # No Redis on Modal: conversation memory lives in the serving container.
            "CHECKPOINTER": "memory",
            "MODEL_ARTIFACT_DIR": "/models",
            "OCR_ENGINE": "tesseract",
            "ENABLE_LAYOUTLMV3": "false",
            # Tesseract's OpenMP threads oversubscribe small containers.
            "OMP_THREAD_LIMIT": "1",
        }
    )
    .add_local_dir(ROOT / "ai-service/app", "/srv/ai-service/app", ignore=IGNORE)
    .add_local_dir(ROOT / "ai-service/knowledge_base", "/srv/ai-service/knowledge_base", ignore=IGNORE)
    .add_local_dir(ROOT / "models", "/models", ignore=IGNORE)
)

# INTERNAL_API_KEY (shared with the backend) + optional GROQ_API_KEY / NEO4J_*.
ai_secrets = [
    modal.Secret.from_name("polymarker-shared", required_keys=["INTERNAL_API_KEY"]),
    modal.Secret.from_name("polymarker-ai"),
]


@app.function(image=ai_image, secrets=ai_secrets, cpu=1.0, memory=2048, scaledown_window=300, timeout=300)
@modal.concurrent(max_inputs=16)
@modal.asgi_app(label="polymarker-ai")
def ai():
    from app.main import create_app

    return create_app()


@app.function(image=ai_image, secrets=ai_secrets, cpu=2.0, memory=2048, timeout=600)
def run_job(job_id: str, kind: str, payload: dict, data: bytes | None) -> None:
    """One OCR / interpretation job (replaces the Celery worker)."""
    from app.services.jobs import run_modal_job

    from app.core.config import get_settings

    store = modal.Dict.from_name(get_settings().modal_job_dict, create_if_missing=True)
    run_modal_job(store, job_id, kind, payload, data)


@app.function(image=ai_image, secrets=ai_secrets, timeout=600)
def load_graph() -> None:
    """Load schema, seed and synthetic-derived bands into Neo4j (idempotent)."""
    if not os.environ.get("NEO4J_URI"):
        raise SystemExit("NEO4J_URI is not set in the polymarker-ai secret; nothing to load.")
    subprocess.run(["python", "-m", "graph_service.loader", "--artifacts", "/models"], check=True)


# --- backend (Express) ----------------------------------------------------------

backend_image = (
    modal.Image.from_registry("node:22-slim", add_python="3.11")
    .add_local_file(ROOT / "backend/package.json", "/app/package.json", copy=True)
    .add_local_file(ROOT / "backend/package-lock.json", "/app/package-lock.json", copy=True)
    .run_commands("cd /app && npm ci --omit=dev && npm cache clean --force")
    .env({"NODE_ENV": "production", "PORT": "5000"})
    .add_local_dir(ROOT / "backend/src", "/app/src", ignore=IGNORE)
)

# DATABASE_URL, JWT_SECRET, FRONTEND_URL, SUPABASE_URL, SUPABASE_SERVICE_KEY, SEED_*.
backend_secrets = [
    modal.Secret.from_name("polymarker-shared", required_keys=["INTERNAL_API_KEY"]),
    modal.Secret.from_name("polymarker-backend", required_keys=["DATABASE_URL", "JWT_SECRET", "FRONTEND_URL"]),
]


def _node(script: str) -> None:
    subprocess.run(["node", script], cwd="/app", check=True)


@app.function(image=backend_image, secrets=backend_secrets, cpu=0.5, memory=512, scaledown_window=300)
@modal.concurrent(max_inputs=50)
@modal.web_server(5000, startup_timeout=60, label="polymarker-api")
def api():
    env = dict(os.environ)
    if not env.get("AI_SERVICE_URL"):
        env["AI_SERVICE_URL"] = ai.get_web_url()
    subprocess.Popen(["node", "src/server.js"], cwd="/app", env=env)


@app.function(image=backend_image, secrets=backend_secrets, timeout=300)
def migrate() -> None:
    """Apply the Postgres schema and create the private Storage bucket."""
    _node("src/scripts/migrate.js")


@app.function(image=backend_image, secrets=backend_secrets, timeout=300)
def seed() -> None:
    """Create the SEED_* admin / clinician / patient accounts (idempotent)."""
    _node("src/scripts/seed.js")
