"""PolyMarker Analytics AI service (FastAPI).

Importing this module never needs an API key, a model artifact, Redis or Neo4j:
every dependency is resolved lazily and degrades gracefully (see /ready).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.inference import router as inference_router
from app.api.ocr import router as ocr_router
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="PolyMarker Analytics AI Service",
        version="1.0.0",
        description="OCR ingestion, LOINC normalization, cohort inference and a GraphRAG assistant "
        "behind deterministic clinical guardrails. Population analytics are derived from synthetic data.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    for router in (health_router, ocr_router, inference_router, chat_router, documents_router):
        app.include_router(router)
    return app


app = create_app()
