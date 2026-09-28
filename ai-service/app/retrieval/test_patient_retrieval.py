from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PATIENT_ID = "6a9d17d6b74cef0c8858926a"

INDEX_DIR = (
    PROJECT_ROOT
    / "patient_faiss"
    / PATIENT_ID
)


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


vector_store = FAISS.load_local(
    INDEX_DIR,
    embeddings,
    allow_dangerous_deserialization=True
)


query = "What could be causing the patient's fatigue and dizziness?"


results = vector_store.similarity_search(
    query,
    k=5
)


print("\n========== RETRIEVED DOCUMENTS ==========\n")


for i, document in enumerate(results, start=1):

    print(f"--- Result {i} ---")

    print("Content:")
    print(document.page_content)

    print("\nMetadata:")
    print(document.metadata)

    print()