from pathlib import Path

from langchain_community.vectorstores import FAISS

from app.core.validation import InvalidPatientId, validate_patient_id
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

    # patient_id arrives here straight from the POST /api/chat/ request
    # body (app/api/chat.py), unauthenticated at this layer -- the JWT
    # check happens one hop up in the Express backend, but ai-service
    # itself trusts the string it is given. Without validation, a
    # patient_id like "../other_patient" would join outside
    # patient_faiss/ (path traversal) or read a *different* patient's
    # index (cross-patient data leak, ARCHITECTURE.md risk R5). Treat an
    # invalid id the same as "no documents yet" rather than raising, so
    # normal callers see no behavior change.
    try:
        patient_id = validate_patient_id(patient_id)
    except InvalidPatientId:
        return None

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
