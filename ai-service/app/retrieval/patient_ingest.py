from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from app.retrieval.embeddings import embeddings

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PATIENT_DOCUMENTS_DIR = PROJECT_ROOT / "patient_documents"
PATIENT_INDEX_DIR = PROJECT_ROOT / "patient_faiss"

PATIENT_INDEX_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# Same local embedding model already used by the
# global medical knowledge base.



text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)


def load_document(file_path: Path):
    """
    Load a patient document based on its file type.
    """

    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        loader = PyPDFLoader(str(file_path))

    elif suffix == ".txt":
        loader = TextLoader(
            str(file_path),
            encoding="utf-8"
        )

    else:
        raise ValueError(
            f"Unsupported document type: {suffix}"
        )

    return loader.load()


def ingest_patient_document(
    patient_id: str,
    document_id: str,
    file_path: Path
):
    """
    Add one patient document to that patient's FAISS index.
    """

    documents = load_document(file_path)

    chunks = text_splitter.split_documents(
        documents
    )

    # Add patient/document metadata to every chunk.
    for chunk in chunks:
        chunk.metadata.update({
            "patient_id": patient_id,
            "document_id": document_id,
            "source": "patient_upload",
            "filename": file_path.name,
        })

    patient_index_dir = (
        PATIENT_INDEX_DIR / patient_id
    )

    # If this patient already has an index,
    # load it and add the new document.
    if patient_index_dir.exists():

        vector_store = FAISS.load_local(
            patient_index_dir,
            embeddings,
            allow_dangerous_deserialization=True
        )

        vector_store.add_documents(
            chunks
        )

    else:

        vector_store = FAISS.from_documents(
            chunks,
            embeddings
        )

    vector_store.save_local(
        patient_index_dir
    )

    return {
        "patient_id": patient_id,
        "document_id": document_id,
        "filename": file_path.name,
        "chunks": len(chunks),
        "index_path": str(
            patient_index_dir
        )
    }