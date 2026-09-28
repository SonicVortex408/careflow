from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router

app = FastAPI(
    title="AI Service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://careflow-pearl-pi.vercel.app",
        "https://careflow-47vvv5nuc-acne-7a93.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(documents_router)

@app.get("/")
def root():
    return {
        "message": "AI service is running"
    }
