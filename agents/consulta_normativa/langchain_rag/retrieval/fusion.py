"""Multi-query retrieval fan-out and reciprocal-rank fusion helpers."""

import hashlib
from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.formatting import recovered_documents, reference_from_metadata
from agents.consulta_normativa.langchain_rag.models import RetrievedDocument

Retriever = Callable[[str, int], dict[str, Any]]


# Nodes for Multi-Query and RRF
def retrieve_variant_node(retriever: Retriever, top_k: int) -> Callable[[dict[str, Any]], RagGraphState]:
    """Retrieve and normalize documents for one query variant."""

    def run(state: dict[str, Any]) -> RagGraphState:
        raw_results = retriever(str(state["query"]), top_k)
        return {"retrieved_lists": [recovered_documents(raw_results)]}

    return run
    
def rrf_fuse_node(rrf_k: int, top_k: int) -> Callable[[RagGraphState], RagGraphState]:
    """Fuse retrieved lists and write final normalized documents."""

    def run(state: RagGraphState) -> RagGraphState:
        fused = reciprocal_rank_fusion(state.get("retrieved_lists", []), rrf_k)
        return {"documents": fused[:top_k]}

    return run


def fanout_retrieve_variants(state: RagGraphState) -> list[Any]:
    """Create one retrieval worker per query variant."""

    # pyrefly: ignore [missing-import]
    from langgraph.types import Send

    return [Send("retrieve_variant", {"query": query}) for query in state.get("query_variants", [])]

def reciprocal_rank_fusion(ranked_lists: list[list[RetrievedDocument]], k: int) -> list[RetrievedDocument]:
    """Fuse ranked lists using RRF score: 1 / (k + one_based_rank)."""

    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    documents_by_identity: dict[str, RetrievedDocument] = {}
    occurrence = 0

    for ranked_list in ranked_lists:
        for rank, document in enumerate(ranked_list, start=1):
            identity = document_identity(document)
            if identity not in first_seen:
                first_seen[identity] = occurrence
                documents_by_identity[identity] = document
                occurrence += 1
            scores[identity] = scores.get(identity, 0.0) + (1 / (k + rank))

    ranked_identities = sorted(scores, key=lambda identity: (-scores[identity], first_seen[identity]))
    return [documents_by_identity[identity] for identity in ranked_identities]


def document_identity(document: RetrievedDocument) -> str:
    """Return a stable identity for RRF deduplication."""

    metadata = document.metadata
    document_id = metadata.get("_document_id") or metadata.get("document_id")
    if has_value(document_id):
        return f"id:{document_id}"

    text_hash = hashlib.sha256(document.document.encode("utf-8")).hexdigest()[:12]
    return f"fallback:{reference_from_metadata(metadata)}:{text_hash}"

def has_value(value: Any) -> bool:
    """Return whether a metadata value can participate in document identity."""

    return value is not None and value != ""
