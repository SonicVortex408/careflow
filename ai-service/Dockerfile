# Build context: repository root (needs ../common and ../graph_service).
#   docker build -f ai-service/Dockerfile -t polymarker-ai .
#   --build-arg INSTALL_VECTOR=true  adds FAISS + sentence-transformers (CPU torch) for vector retrieval
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Tesseract is the default OCR engine (PaddleOCR / LayoutLMv3 are opt-in, see README).
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "uv==0.8.17"

WORKDIR /srv
COPY common ./common
COPY graph_service ./graph_service
COPY ai-service/pyproject.toml ai-service/uv.lock ./ai-service/

WORKDIR /srv/ai-service
ARG INSTALL_VECTOR=false
RUN uv sync --frozen --no-dev --no-install-project \
 && if [ "$INSTALL_VECTOR" = "true" ]; then \
      uv sync --frozen --no-dev --no-install-project --extra vector --no-install-package torch \
      && uv pip install --python /opt/venv/bin/python --index-url https://download.pytorch.org/whl/cpu torch; \
    fi

COPY ai-service/app ./app
COPY ai-service/knowledge_base ./knowledge_base
RUN if [ "$INSTALL_VECTOR" = "true" ]; then \
      uv sync --frozen --no-dev --extra vector --no-install-package torch \
      && /opt/venv/bin/python -m app.retrieval.kb build; \
    else \
      uv sync --frozen --no-dev; \
    fi

RUN useradd --create-home --uid 10001 app \
 && mkdir -p /srv/ai-service/patient_documents /srv/ai-service/patient_faiss \
 && chown -R app /srv/ai-service
USER app

ENV PATH="/opt/venv/bin:$PATH" \
    MODEL_ARTIFACT_DIR=/models \
    OMP_THREAD_LIMIT=1
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=4)" || exit 1
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
