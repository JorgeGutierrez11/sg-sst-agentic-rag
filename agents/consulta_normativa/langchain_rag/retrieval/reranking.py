"""Post-retrieval document reranking helpers."""

from collections.abc import Callable
from functools import lru_cache
from typing import Any

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.models import RetrievedDocument


@lru_cache(maxsize=4)
def get_reranker(model_name: str, max_length: int) -> Any:
    """Load and cache a CrossEncoder reranker lazily."""

    # pyrefly: ignore [missing-import]
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, max_length=max_length)

# Por que no limito el numero de candidatos, no es mas eficiente analizar todo los recuperados? 
def rerank_node(
    reranker: Any,
    candidate_pool_size: int,
    final_top_k: int,
) -> Callable[[RagGraphState], RagGraphState]:
    """Rerank state documents and write the selected documents back to state documents."""

    def run(state: RagGraphState) -> RagGraphState:
        documents = state.get("documents", [])
        candidate_documents = documents[:candidate_pool_size]
        query = state["question"]

        if not candidate_documents:
            return {
                "documents": [],
                "reranking_trace": {
                    "fallback": False,
                    "candidate_count": 0,
                    "selected_count": 0,
                },
            }

        try:
            selected_documents = rerank_documents(query, candidate_documents, resolve_reranker(reranker), final_top_k)
            return {
                "documents": selected_documents,
                "reranking_trace": {
                    "fallback": False,
                    "candidate_count": len(candidate_documents),
                    "selected_count": len(selected_documents),
                },
            }
        except Exception as error:  # pragma: no cover - exact dependency failures vary by environment.
            return fallback_reranking_update(candidate_documents, final_top_k, error)

    return run


def rerank_documents(
    query: str,
    documents: list[RetrievedDocument],
    reranker: Any,
    final_top_k: int,
) -> list[RetrievedDocument]:
    """Score query/document pairs and return the top documents by descending score."""

    candidate_pairs = [(query, document_text_for_reranking(document)) for document in documents]
    scores = reranker.predict(candidate_pairs)
    ranked_documents = sorted(
        zip(documents, scores, strict=False), 
        key=lambda item: item[1], 
        reverse=True
    )
    return [document for document, _score in ranked_documents[:final_top_k]]


# Podemos hacer una mejora para que el Ranker vea la metadata.
def document_text_for_reranking(document: RetrievedDocument) -> str:
    """Return the text sent to the reranker for one candidate."""

    return document.document


def resolve_reranker(reranker: Any) -> Any:
    """Resolve a reranker instance or lazy loader."""

    if callable(reranker) and not hasattr(reranker, "predict"):
        return reranker()
    return reranker


def fallback_reranking_update(
    documents: list[RetrievedDocument],
    final_top_k: int,
    error: Exception,
) -> RagGraphState:
    """Return conservative reranking fallback state update."""

    selected_documents = documents[:final_top_k]
    return {
        "documents": selected_documents,
        "reranking_trace": {
            "fallback": True,
            "error": type(error).__name__,
            "candidate_count": len(documents),
            "selected_count": len(selected_documents),
        },
    }
