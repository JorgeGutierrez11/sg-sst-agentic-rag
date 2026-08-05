"""Small ChromaDB boundary used by the base RAG vectorization flow."""

from pathlib import Path
from typing import Any

from pipeline.vectorization.documents import ChromaRecord

DEFAULT_COLLECTION_NAME = "sg_sst_base_rag"


def open_collection(
    persist_path: Path,  # Path to the directory where the ChromaDB collection will be stored
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Any:
    """Open or create a persistent local ChromaDB collection."""

    # pyrefly: ignore [missing-import]
    import chromadb

    persist_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_path))
    return client.get_or_create_collection(collection_name)


def upsert_records(collection: Any, records: list[ChromaRecord]) -> int:
    """Insert or update records in a ChromaDB collection and return the count."""

    if not records:
        return 0

    ids = [record.id for record in records]
    documents = [record.document for record in records]
    metadatas = [record.metadata for record in records]

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(records)


def query_top_k(collection: Any, question: str, top_k: int = 5) -> dict[str, Any]:
    """Run a top-k similarity query against ChromaDB."""

    return collection.query(
        query_texts=[question],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
