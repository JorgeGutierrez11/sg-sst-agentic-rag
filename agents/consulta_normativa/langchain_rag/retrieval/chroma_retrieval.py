"""Canonical query-only ChromaDB helpers for runtime retrieval."""

import shutil
import stat
import tempfile
import weakref
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pipeline.chunking.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL_REVISION

DEFAULT_COLLECTION_NAME = "sg_sst_base_rag"
WORKING_COPY_PREFIX = "sg-sst-chroma-"
Retriever = Callable[[str, int], dict[str, Any]]


class ChromaWorkingCopy:
    """Disposable copy of the published Chroma index, removed on cleanup or at exit."""

    def __init__(self, directory: Path) -> None:
        # Se borra con rmtree: solo se aceptan directorios creados por create_working_copy.
        if not directory.name.startswith(WORKING_COPY_PREFIX):
            raise ValueError(f"Not a Chroma working copy directory: {directory}")
        self.path = directory / "chroma"
        self._finalizer = weakref.finalize(self, shutil.rmtree, directory, ignore_errors=True)

    def cleanup(self) -> None:
        """Remove the copy now instead of waiting for interpreter exit."""

        self._finalizer()


def create_working_copy(source_path: Path, working_root: Path | None = None) -> ChromaWorkingCopy:
    """Copy the published index to a fresh writable directory, never opening the source.

    Chroma rewrites its SQLite and HNSW files even when only querying, and it fails
    on read-only files, so the runtime must query a private copy.

    Args:
        source_path: Published Chroma persist directory.
        working_root: Parent directory for the copy; the system temp dir when None.
    """

    source = source_path.resolve()
    if not source.is_dir():
        raise ValueError(f"ChromaDB persist path does not exist: {source_path}")

    if working_root is not None:
        working_root = working_root.resolve()
        if working_root.is_relative_to(source):
            raise ValueError(
                "RAG_CHROMA_WORKING_DIR must be outside the published Chroma index: "
                f"{working_root}"
            )
        working_root.mkdir(parents=True, exist_ok=True)

    directory = Path(tempfile.mkdtemp(prefix=WORKING_COPY_PREFIX, dir=working_root))
    target = directory / "chroma"
    try:
        # copyfile no copia permisos: un origen de solo lectura daría una copia inservible.
        shutil.copytree(source, target, copy_function=shutil.copyfile)
        for item in (target, *target.rglob("*")):
            item.chmod(item.stat().st_mode | stat.S_IWUSR)
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise

    return ChromaWorkingCopy(directory)


def open_existing_collection(
    persist_path: Path,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    embedding_function: Any = None,
) -> Any:
    """Open an existing persistent ChromaDB collection for query without creating it."""

    if not persist_path.exists():
        raise ValueError(f"ChromaDB persist path does not exist: {persist_path}")

    client = persistent_client(persist_path)
    return client.get_collection(
        name=collection_name,
        embedding_function=embedding_function if embedding_function is not None else qwen_embedding_function(),
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

    # chromadb cachea modelos por nombre e ignora la revisión: crear una sola instancia
    return SentenceTransformerEmbeddingFunction(
        model_name=DEFAULT_EMBEDDING_MODEL,
        revision=DEFAULT_EMBEDDING_MODEL_REVISION,
    )


def query_top_k(collection: Any, question: str, top_k: int = 5) -> dict[str, Any]:
    """Run a top-k similarity query against ChromaDB."""

    return collection.query(
        query_texts=[question],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )


def chroma_retriever(collection: Any) -> Retriever:
    """Build a graph-compatible retriever callable from a ChromaDB collection."""

    def retrieve(question: str, top_k: int) -> dict[str, Any]:
        return query_top_k(collection, question, top_k)

    return retrieve
