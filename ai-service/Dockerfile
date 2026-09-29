FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# System dependencies for the Week 2 OCR pipeline:
#   tesseract-ocr        the binary pytesseract wraps -- there is no
#                         PyPI wheel for this, it must be installed at
#                         the OS level (OCR_ENGINE=tesseract, default).
#   libglib2.0-0 / libsm6 / libxext6
#                         runtime libs opencv-python-headless needs even
#                         in its "headless" build.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY sample_docs ./sample_docs

RUN uv venv /opt/venv

# NOTE: uv.lock is not committed right now -- the Week 1-3 changes added
# a large batch of new dependencies (celery, OCR libs, rapidfuzz, ...)
# and there is no `uv` binary in the environment that built this repo to
# regenerate the lock. This build resolves versions at build time
# instead of from a lock. Before a production deploy, run `uv lock`
# once from a machine with uv installed, commit uv.lock, and switch the
# line below back to `uv sync --frozen ...` for reproducible builds.
RUN uv sync --no-install-project --no-install-package torch

# Install CPU-only PyTorch after uv sync so uv cannot replace it with the
# CUDA-enabled build from PyPI.
RUN uv pip install \
    --python /opt/venv/bin/python \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.14.0

# Build the general FAISS knowledge base.
RUN uv run --no-sync python -m app.retrieval.ingest

EXPOSE 8080

CMD ["sh", "-c", "uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
