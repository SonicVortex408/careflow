import glob
import os
from pathlib import Path

from dotenv import load_dotenv

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

DOCS_DIR = PROJECT_ROOT / "sample_docs"
INDEX_DIR = PROJECT_ROOT / "faiss_index"


def extract_metadata(text):

    metadata = {}

    if not text.startswith("---"):
        return metadata

    parts = text.split("---", 2)

    if len(parts) < 3:
        return metadata

    front_matter = parts[1].strip()

    for line in front_matter.splitlines():

        if ":" in line:

            key, value = line.split(":", 1)

            metadata[key.strip()] = value.strip()

    return metadata


def load_and_split(docs_dir):

    chunks = []

    # =========================
    # LOAD MARKDOWN FILES
    # =========================

    md_files = glob.glob(
        os.path.join(
            docs_dir,
            "**",
            "*.md"
        ),
        recursive=True
    )

    for path in md_files:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            text = f.read()

        source = os.path.basename(path)

        doc_metadata = extract_metadata(text)
        doc_metadata["source"] = source

        paragraphs = [
            p.strip()
            for p in text.split("\n\n")
            if p.strip()
        ]

        current = ""

        for para in paragraphs:

            if len(current) + len(para) + 2 <= 500:

                current = (
                    current
                    + "\n\n"
                    + para
                ).strip()

            else:

                if current:

                    chunks.append(
                        Document(
                            page_content=current,
                            metadata=doc_metadata.copy()
                        )
                    )

                current = para

        if current:

            chunks.append(
                Document(
                    page_content=current,
                    metadata=doc_metadata.copy()
                )
            )

    # =========================
    # LOAD PDF FILES
    # =========================

    pdf_files = glob.glob(
        os.path.join(
            docs_dir,
            "**",
            "*.pdf"
        ),
        recursive=True
    )

    for path in pdf_files:

        loader = PyPDFLoader(path)

        pages = loader.load()

        for page in pages:

            text = page.page_content.strip()

            if not text:
                continue

            metadata = page.metadata.copy()

            metadata["source"] = os.path.basename(path)

            # Split PDF page text into ~500 character chunks
            for i in range(0, len(text), 500):

                chunk_text = text[i:i + 500].strip()

                if chunk_text:

                    chunks.append(
                        Document(
                            page_content=chunk_text,
                            metadata=metadata.copy()
                        )
                    )

    return chunks


def build_index():

    chunks = load_and_split(DOCS_DIR)

    print(f"{len(chunks)} chunks created.")

    if not chunks:

        print("ERROR: No documents were found.")
        return


    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = FAISS.from_documents(
        chunks,
        embeddings
    )

    INDEX_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    vector_store.save_local(
        INDEX_DIR
    )

    print(
        "FAISS index rebuilt successfully."
    )


if __name__ == "__main__":
    build_index()