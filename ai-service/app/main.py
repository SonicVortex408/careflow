from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.ocr import router as ocr_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AI Service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    # Previously three origins were hardcoded here. CORS_ALLOW_ORIGINS
    # (comma-separated) now drives this, defaulting to the local Vite
    # dev server. Set it explicitly per environment (see .env.example).
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(ocr_router)


@app.get("/")
def root():
    return {
        "message": "AI service is running"
    }


@app.get("/health")
def health():
    """
    Liveness/readiness probe that never touches the lazily-constructed
    LLM client or FAISS indexes, so it answers even when GROQ_API_KEY is
    unset or the knowledge-base index hasn't been built yet. Use this
    for container health checks, not `/`.
    """
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
    }
