from functools import lru_cache
from pathlib import Path

from langchain_community.vectorstores import FAISS

from app.retrieval.embeddings import embeddings

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INDEX_DIR = PROJECT_ROOT / "faiss_index"


@lru_cache
def get_retriever():
    """
    Load the global knowledge-base FAISS index and build a retriever,
    lazily and cached.

    Previously this ran at *module import*: the whole service failed to
    import (and every endpoint 500'd) unless `python -m app.retrieval.ingest`
    had already been run to build faiss_index/. Loading lazily lets the
    app start; only `search_docs` calls that actually need retrieval fail,
    with a clear error, until the index exists.
    """

    if not INDEX_DIR.exists():
        raise RuntimeError(
            f"Knowledge-base index not found at {INDEX_DIR}. "
            "Run `python -m app.retrieval.ingest` first."
        )

    vector_store = FAISS.load_local(
        INDEX_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )

    return vector_store.as_retriever(
        search_kwargs={
            "k": 5
        }
    )
