from pathlib import Path

from langchain_community.vectorstores import FAISS
from app.retrieval.embeddings import embeddings

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INDEX_DIR = PROJECT_ROOT / "faiss_index"





vector_store = FAISS.load_local(
    INDEX_DIR,
    embeddings,
    allow_dangerous_deserialization=True
)


retriever = vector_store.as_retriever(
    search_kwargs={
        "k": 5
    }
)