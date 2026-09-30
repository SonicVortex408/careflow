"""Optional vector backend (``ai-service[vector]``): FAISS + MiniLM embeddings, lazy."""

from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def vector_available() -> bool:
    try:
        import faiss  # noqa: F401
        import langchain_community  # noqa: F401
        import langchain_huggingface  # noqa: F401
    except ImportError:
        return False
    return True


@lru_cache(maxsize=1)
def get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def load_faiss(path):
    from langchain_community.vectorstores import FAISS

    # Only indexes this service wrote itself are loaded, from validated paths.
    return FAISS.load_local(str(path), get_embeddings(), allow_dangerous_deserialization=True)


def build_faiss(documents):
    from langchain_community.vectorstores import FAISS

    return FAISS.from_documents(documents, get_embeddings())
