"""Per-patient document indexes (one directory per patient).

Isolation (risk R5): the directory is derived only from a validated ObjectId,
and every chunk returned is re-checked against the requesting patient id; a
mismatch is dropped and logged as a security event.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.security import safe_child, validate_object_id
from app.retrieval.lexical import BM25

logger = logging.getLogger(__name__)
CHUNK = 600
OVERLAP = 100


def _dir(patient_id: str) -> Path:
    pid = validate_object_id(patient_id)
    return safe_child(get_settings().patient_index_dir, pid)


def _chunks(text: str) -> list[str]:
    text = text.strip()
    out, i = [], 0
    while i < len(text):
        out.append(text[i : i + CHUNK])
        i += CHUNK - OVERLAP
    return [c for c in out if c.strip()]


def index_patient_text(
    patient_id: str, document_id: str, text: str, source: str = "patient_upload"
) -> int:
    pid = validate_object_id(patient_id)
    directory = _dir(pid)
    directory.mkdir(parents=True, exist_ok=True)
    pieces = _chunks(text)
    records = [
        {"text": c, "patient_id": pid, "document_id": document_id, "source": source} for c in pieces
    ]
    with open(directory / "chunks.jsonl", "a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")

    from app.retrieval.vector import vector_available

    if vector_available() and records:
        try:
            from langchain_core.documents import Document

            from app.retrieval.vector import build_faiss, load_faiss

            docs = [
                Document(
                    page_content=r["text"], metadata={k: v for k, v in r.items() if k != "text"}
                )
                for r in records
            ]
            faiss_dir = directory / "faiss"
            if (faiss_dir / "index.faiss").exists():
                store = load_faiss(faiss_dir)
                store.add_documents(docs)
            else:
                store = build_faiss(docs)
            store.save_local(str(faiss_dir))
        except Exception as exc:  # noqa: BLE001 - lexical index is still written
            logger.warning("patient vector index update failed: %s", type(exc).__name__)
    return len(records)


def index_patient_file(patient_id: str, document_id: str, path: Path) -> int:
    from polymarker_common.ocr import extract_text

    text = extract_text(path).text
    return index_patient_text(patient_id, document_id, text)


def _assert_owned(records: list[dict], patient_id: str) -> list[dict]:
    owned = [r for r in records if r.get("patient_id") == patient_id]
    if len(owned) != len(records):
        logger.error(
            "SECURITY: dropped %d chunk(s) not owned by the requesting patient",
            len(records) - len(owned),
        )
    return owned


def search_patient(patient_id: str, query: str, k: int = 4) -> list[dict]:
    pid = validate_object_id(patient_id)
    directory = _dir(pid)
    from app.retrieval.vector import vector_available

    if vector_available() and (directory / "faiss" / "index.faiss").exists():
        from app.retrieval.vector import load_faiss

        store = load_faiss(directory / "faiss")
        hits = [{"text": h.page_content, **h.metadata} for h in store.similarity_search(query, k=k)]
        return _assert_owned(hits, pid)
    path = directory / "chunks.jsonl"
    if not path.exists():
        return []
    records = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    records = _assert_owned(records, pid)
    if not records:
        return []
    scores = BM25([r["text"] for r in records]).scores(query)
    ranked = sorted(zip(scores, range(len(records)), strict=True), reverse=True)
    return [records[i] for s, i in ranked[:k] if s > 0]
