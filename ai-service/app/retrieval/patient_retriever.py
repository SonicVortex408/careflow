from pathlib import Path

from langchain_community.vectorstores import FAISS
from app.retrieval.embeddings import embeddings

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PATIENT_INDEX_DIR = (
    PROJECT_ROOT / "patient_faiss"
)



def get_patient_retriever(
    patient_id: str,
    k: int = 5
):
    """
    Return a retriever for one patient's
    medical documents.

    Each patient has a completely separate
    FAISS index.
    """

    patient_index_dir = (
        PATIENT_INDEX_DIR / patient_id
    )

    # Patient has no uploaded documents yet.
    if not patient_index_dir.exists():
        return None

    vector_store = FAISS.load_local(
        patient_index_dir,
        embeddings,
        allow_dangerous_deserialization=True
    )

    return vector_store.as_retriever(
        search_kwargs={
            "k": k
        }
    )
