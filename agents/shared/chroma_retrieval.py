"""Canonical query-only ChromaDB helpers for runtime retrieval.

The vectorization pipeline re-exports these helpers for backward-compatible imports,
but collection creation and upsert remain in ``pipeline.vectorization``.
"""

from pathlib import Path
from typing import Any

from pipeline.chunking.core.config import DEFAULT_EMBEDDING_MODEL

DEFAULT_COLLECTION_NAME = "sg_sst_base_rag"


def open_existing_collection(
    persist_path: Path,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Any:
    """Open an existing persistent ChromaDB collection for query without creating it."""

    if not persist_path.exists():
        raise ValueError(f"ChromaDB persist path does not exist: {persist_path}")

    client = persistent_client(persist_path)
    return client.get_collection(
        name=collection_name,
        embedding_function=qwen_embedding_function(),
    )


def persistent_client(persist_path: Path) -> Any:
    """Build a ChromaDB persistent client while keeping Chroma optional at import time."""

    # pyrefly: ignore [missing-import]
    import chromadb

    client = chromadb.PersistentClient(path=str(persist_path))
    return client


def qwen_embedding_function() -> Any:
    """Return the explicit Qwen embedding function used for SG-SST retrieval."""

    # pyrefly: ignore [missing-import]
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    return SentenceTransformerEmbeddingFunction(model_name=DEFAULT_EMBEDDING_MODEL)


def query_top_k(collection: Any, question: str, top_k: int = 5) -> dict[str, Any]:
    """Run a top-k similarity query against ChromaDB."""

    return collection.query(
        query_texts=[question],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
