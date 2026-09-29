"""
Manual smoke test: run a similarity search against the global knowledge-
base FAISS index and print the results.

Not a test -- requires a built faiss_index/ (see
`python -m app.retrieval.ingest`). The default query and metadata fields
below are e-commerce leftovers from before the medical retrofit; once the
knowledge base is replaced with the 9-biomarker docs (Phase 3), update
the query and metadata keys to match.

Run from the ai-service/ directory:
    uv run python scripts/manual_kb_retrieval.py ["your query"]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.retrieval.retriever import get_retriever

DEFAULT_QUERY = "What is the return policy?"


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY

    docs = get_retriever().invoke(query)

    print(f"Found {len(docs)} documents\n")

    for i, doc in enumerate(docs, 1):
        print(f"--- Document {i} ---")
        print("Source:", doc.metadata.get("source"))
        print("Status:", doc.metadata.get("status"))
        print("Authority:", doc.metadata.get("policy_authority"))
        print("Audience:", doc.metadata.get("audience"))
        print("\nContent:")
        print(doc.page_content)
        print()


if __name__ == "__main__":
    main()
