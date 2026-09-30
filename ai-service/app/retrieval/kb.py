"""Medical knowledge base retrieval (vector fallback for GraphRAG).

Metadata filtering is enforced here, in code, not only in the prompt
(architecture decision 9): only chunks with ``status: active`` and a non-internal
audience can ever be returned, whichever backend (FAISS or BM25) ranks them.

    uv run python -m app.retrieval.kb build     # build the FAISS index (vector extra)
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.retrieval.lexical import BM25

logger = logging.getLogger(__name__)

ALLOWED_STATUS = {"active"}
BLOCKED_AUDIENCE = {"internal", "staff-only"}
CHUNK_CHARS = 700


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


def parse_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, parts[2].strip()


def is_allowed(meta: dict) -> bool:
    return (
        meta.get("status", "").lower() in ALLOWED_STATUS
        and meta.get("audience", "patient").lower() not in BLOCKED_AUDIENCE
    )


def load_chunks(kb_dir: Path | None = None) -> list[Chunk]:
    kb_dir = kb_dir or get_settings().knowledge_base_dir
    chunks = []
    for path in sorted(kb_dir.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        meta["source"] = path.name
        heading = meta.get("title", path.stem)
        current = ""
        for para in [p.strip() for p in body.split("\n\n") if p.strip()]:
            if para.startswith("#"):
                heading = para.lstrip("# ").strip() or heading
            if current and len(current) + len(para) > CHUNK_CHARS:
                chunks.append(Chunk(current, dict(meta, section=heading)))
                current = ""
            current = f"{current}\n\n{para}".strip()
        if current:
            chunks.append(Chunk(current, dict(meta, section=heading)))
    return chunks


@lru_cache(maxsize=1)
def _lexical_index() -> tuple[list[Chunk], BM25]:
    allowed = [c for c in load_chunks() if is_allowed(c.metadata)]
    return allowed, BM25(
        [f"{c.metadata.get('title', '')} {c.metadata.get('section', '')} {c.text}" for c in allowed]
    )


@lru_cache(maxsize=1)
def _vector_store():
    from app.retrieval.vector import load_faiss, vector_available

    path = get_settings().kb_index_dir
    if not vector_available() or not (path / "index.faiss").exists():
        return None
    try:
        return load_faiss(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("KB vector index unavailable (%s); using BM25", type(exc).__name__)
        return None


def search(query: str, k: int = 4) -> list[Chunk]:
    store = _vector_store()
    if store is not None:
        hits = store.similarity_search(query, k=k * 4)
        results = [Chunk(h.page_content, dict(h.metadata)) for h in hits if is_allowed(h.metadata)]
        return results[:k]
    chunks, bm25 = _lexical_index()
    scored = sorted(zip(bm25.scores(query), range(len(chunks)), strict=True), reverse=True)
    return [chunks[i] for s, i in scored[:k] if s > 0]


def format_results(chunks: list[Chunk]) -> str:
    if not chunks:
        return "No relevant reference material was found."
    return "\n\n---\n\n".join(
        f"[{c.metadata.get('title', c.metadata['source'])} | evidence: {c.metadata.get('evidence_level', 'unverified')}]\n{c.text}"
        for c in chunks
    )


def build_index() -> int:
    from langchain_core.documents import Document

    from app.retrieval.vector import build_faiss, vector_available

    if not vector_available():
        raise SystemExit("vector extra not installed: uv sync --extra vector")
    # Filtered at build time too, so blocked documents are never embedded.
    docs = [
        Document(page_content=c.text, metadata=c.metadata)
        for c in load_chunks()
        if is_allowed(c.metadata)
    ]
    store = build_faiss(docs)
    out = get_settings().kb_index_dir
    out.mkdir(parents=True, exist_ok=True)
    store.save_local(str(out))
    return len(docs)


if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        print(f"indexed {build_index()} chunks")
    else:
        print("usage: python -m app.retrieval.kb build")
