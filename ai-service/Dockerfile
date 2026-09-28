FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY app ./app
COPY sample_docs ./sample_docs

RUN uv venv /opt/venv

# Install all locked dependencies except torch. The lockfile's PyPI torch
# package pulls CUDA dependencies on Linux, which is not needed here.
RUN uv sync --frozen --no-install-project --no-install-package torch

# Install CPU-only PyTorch after uv sync so uv cannot replace it with the
# CUDA-enabled build from the lockfile.
RUN uv pip install \
    --python /opt/venv/bin/python \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.14.0

# Build the general FAISS knowledge base.
RUN uv run --no-sync python -m app.retrieval.ingest

EXPOSE 8080

CMD ["sh", "-c", "uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]