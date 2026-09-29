"""
Manual smoke test: run a similarity search against one patient's FAISS
index and print the results.

Not a test -- requires a real index already built by
scripts/manual_patient_ingest.py (or via the /api/documents/process
endpoint) for the given patient_id.

Run from the ai-service/ directory:
    uv run python scripts/manual_patient_retrieval.py [patient_id] [query]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PATIENT_ID = "6a9d17d6b74cef0c8858926a"
DEFAULT_QUERY = "What could be causing the patient's fatigue and dizziness?"


def main():
    patient_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATIENT_ID
    query = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_QUERY

    index_dir = PROJECT_ROOT / "patient_faiss" / patient_id

    if not index_dir.exists():
        print(f"No index found at {index_dir}")
        print("Run scripts/manual_patient_ingest.py first.")
        sys.exit(1)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = FAISS.load_local(
        index_dir,
        embeddings,
        allow_dangerous_deserialization=True
    )

    results = vector_store.similarity_search(query, k=5)

    print("\n========== RETRIEVED DOCUMENTS ==========\n")

    for i, document in enumerate(results, start=1):
        print(f"--- Result {i} ---")
        print("Content:")
        print(document.page_content)
        print("\nMetadata:")
        print(document.metadata)
        print()


if __name__ == "__main__":
    main()
