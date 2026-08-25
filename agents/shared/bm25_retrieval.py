"""Canonical query-only BM25S helpers for runtime sparse retrieval."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

DEFAULT_BM25_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "bm25"
EMPTY_QUERY_RESULT = {"ids": [[]], "documents": [[]], "metadatas": [[]], "scores": [[]]}
Retriever = Callable[[str, int], dict[str, Any]]


def open_existing_index(persist_path: Path = DEFAULT_BM25_PATH) -> Any:
    """Open an existing BM25S index for query without creating or writing it."""

    if not persist_path.exists():
        raise ValueError(f"BM25 persist path does not exist: {persist_path}")

    return bm25s_module().BM25.load(str(persist_path), load_corpus=True)


def query_top_k(index: Any, question: str, top_k: int = 5) -> dict[str, Any]:
    """Run a top-k sparse query against a loaded BM25S index."""

    document_count = len(getattr(index, "corpus", []) or [])
    if document_count == 0 or top_k <= 0:
        return empty_query_result()

    effective_top_k = min(top_k, document_count)
    query_tokens = bm25s_module().tokenize([question], stopwords="es")
    try:
        retrieval_output = index.retrieve(query_tokens, k=effective_top_k, return_as="tuple")
    except TypeError:
        retrieval_output = index.retrieve(query_tokens, k=effective_top_k)

    return normalize_retrieval_results(retrieval_output)


def bm25_retriever(index: Any) -> Retriever:
    """Build a graph-compatible retriever callable from a loaded BM25S index."""

    def retrieve(question: str, top_k: int) -> dict[str, Any]:
        return query_top_k(index, question, top_k)

    return retrieve


def empty_query_result() -> dict[str, Any]:
    """Return a fresh empty Chroma-like result shape."""

    return {key: [list(values[0])] for key, values in EMPTY_QUERY_RESULT.items()}


def normalize_retrieval_results(retrieval_output: Any) -> dict[str, Any]:
    """Convert BM25S result arrays into the runtime retrieval shape."""

    results, scores = retrieval_documents_and_scores(retrieval_output)
    records = first_row(results)
    score_values = first_row(scores)
    return {
        "ids": [[str(record["id"]) for record in records]],
        "documents": [[str(record["document"]) for record in records]],
        "metadatas": [[dict(record.get("metadata", {})) for record in records]],
        "scores": [[float(score) for score in score_values]],
    }


def retrieval_documents_and_scores(retrieval_output: Any) -> tuple[Any, Any]:
    """Return documents and scores from BM25S Results objects or tuple outputs."""

    if hasattr(retrieval_output, "documents") and hasattr(retrieval_output, "scores"):
        return retrieval_output.documents, retrieval_output.scores

    documents, scores = retrieval_output
    return documents, scores


def first_row(values: Any) -> list[Any]:
    """Return the first row from BM25S list or array outputs."""

    if hasattr(values, "tolist"):
        values = values.tolist()
    if not values:
        return []
    return list(values[0])


def bm25s_module() -> Any:
    """Import BM25S lazily so runtime import stays lightweight and testable."""

    # pyrefly: ignore [missing-import]
    import bm25s

    return bm25s
