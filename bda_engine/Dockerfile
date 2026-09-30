# Offline big-data engine (compose profile "ml"). Build context: repository root.
#   docker compose --profile ml run --rm bda all
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy
# Java for PySpark, Tesseract for batch OCR of scanned PDFs, fonts for PDF generation.
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless tesseract-ocr tesseract-ocr-eng fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "uv==0.8.17"
WORKDIR /srv
COPY common ./common
COPY bda_engine/pyproject.toml bda_engine/uv.lock ./bda_engine/
WORKDIR /srv/bda_engine
RUN uv sync --frozen --no-dev --extra spark --no-install-project
COPY bda_engine ./
RUN uv sync --frozen --no-dev --extra spark
ENV PATH="/opt/venv/bin:$PATH" MODEL_ARTIFACT_DIR=/models BDA_DATA_DIR=/data OMP_THREAD_LIMIT=1
ENTRYPOINT ["bda"]
CMD ["all"]
