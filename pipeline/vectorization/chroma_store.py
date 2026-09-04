"""Small ChromaDB boundary used by the base RAG vectorization flow."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pipeline.chunking.config import DEFAULT_EMBEDDING_MODEL
from pipeline.vectorization.documents import ChromaRecord

DEFAULT_COLLECTION_NAME = "sg_sst_base_rag"
DEFAULT_UPSERT_BATCH_SIZE = 8

ProgressCallback = Callable[[int, int, int], None]


def open_or_create_collection(
    persist_path: Path,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Any:
    """Open or create a persistent ChromaDB collection for ingestion."""

    client = persistent_client(persist_path, create_path=True)
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=qwen_embedding_function(),
    )


def persistent_client(persist_path: Path, create_path: bool = False) -> Any:
    """Build a ChromaDB persistent client, optionally creating the ingest directory first."""

    if create_path:
        persist_path.mkdir(parents=True, exist_ok=True)

    # pyrefly: ignore [missing-import]
    import chromadb

    return chromadb.PersistentClient(path=str(persist_path))


def qwen_embedding_function() -> Any:
    """Return the explicit Qwen embedding function used for SG-SST vectorization."""

    # pyrefly: ignore [missing-import]
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    return SentenceTransformerEmbeddingFunction(model_name=DEFAULT_EMBEDDING_MODEL)


def upsert_records(
    collection: Any,
    records: list[ChromaRecord],
    batch_size: int = DEFAULT_UPSERT_BATCH_SIZE,
    on_batch_complete: ProgressCallback | None = None,
) -> int:
    """Insert or update Chroma records in bounded batches and return the inserted count."""

    if not records:
        return 0
    if batch_size <= 0:
        raise ValueError("--batch-size must be greater than 0")

    total_batches = (len(records) + batch_size - 1) // batch_size
    inserted_count = 0
    for batch_index, batch in enumerate(record_batches(records, batch_size), start=1):
        ids = [record.id for record in batch]
        documents = [record.document for record in batch]
        metadatas = [record.metadata for record in batch]

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        inserted_count += len(batch)
        if on_batch_complete:
            on_batch_complete(batch_index, total_batches, inserted_count)
    return inserted_count


def record_batches(records: list[ChromaRecord], batch_size: int) -> list[list[ChromaRecord]]:
    """Split Chroma records into sequential batches with a fixed maximum size."""

    return [records[index : index + batch_size] for index in range(0, len(records), batch_size)]
