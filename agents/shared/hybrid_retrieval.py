"""Query-only Hybrid Retrieval helpers for dense Chroma and sparse BM25."""

from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.formatting import recovered_documents
from agents.consulta_normativa.langchain_rag.models import RetrievedDocument
from agents.consulta_normativa.langchain_rag.retrieval.fusion import document_identity, reciprocal_rank_fusion
from agents.shared import bm25_retrieval, chroma_retrieval

EMPTY_HYBRID_RESULT = {"ids": [[]], "documents": [[]], "metadatas": [[]]}


def hybrid_retriever(
    dense_collection: Any,
    sparse_index: Any,
    *,
    candidate_top_k: int,
    final_top_k: int,
    rrf_k: int,
) -> Callable[[str, int], dict[str, Any]]:
    """Build a graph-compatible retriever that fuses Chroma and BM25 rankings with RRF."""

    def retrieve(query: str, top_k: int) -> dict[str, Any]:
        effective_top_k = effective_final_top_k(top_k, final_top_k)
        if effective_top_k <= 0:
            return empty_hybrid_result()

        dense_raw = chroma_retrieval.query_top_k(dense_collection, query, candidate_top_k)
        sparse_raw = bm25_retrieval.query_top_k(sparse_index, query, candidate_top_k)

        dense_documents = recovered_documents(dense_raw)
        sparse_documents = recovered_documents(sparse_raw)
        
        retrieval_sources = retrieval_sources_by_identity(dense_documents, sparse_documents)
        fused_documents = reciprocal_rank_fusion([dense_documents, sparse_documents], k=rrf_k)
        enriched_documents = add_retrieval_source_metadata(fused_documents[:effective_top_k], retrieval_sources)
        return documents_to_raw_results(enriched_documents)

    return retrieve


def effective_final_top_k(requested_top_k: int, configured_final_top_k: int) -> int:
    """Return the final result count allowed by caller and configuration."""

    if requested_top_k <= 0 or configured_final_top_k <= 0:
        return 0
    return min(requested_top_k, configured_final_top_k)


def retrieval_sources_by_identity(
    dense_documents: list[RetrievedDocument],
    sparse_documents: list[RetrievedDocument],
) -> dict[str, set[str]]:
    """Return retrieval source names grouped by document identity."""

    sources_by_identity: dict[str, set[str]] = {}
    for source_name, documents in (("chroma", dense_documents), ("bm25", sparse_documents)):
        for document in documents:
            sources_by_identity.setdefault(document_identity(document), set()).add(source_name)
    return sources_by_identity


def add_retrieval_source_metadata(
    documents: list[RetrievedDocument],
    sources_by_identity: dict[str, set[str]],
) -> list[RetrievedDocument]:
    """Add internal retrieval-source metadata without changing document order."""

    enriched_documents = []
    for document in documents:
        sources = sources_by_identity.get(document_identity(document), set())
        ordered_sources = [source for source in ("chroma", "bm25") if source in sources]
        metadata = dict(document.metadata)
        metadata["_retrieved_by_chroma"] = "chroma" in sources
        metadata["_retrieved_by_bm25"] = "bm25" in sources
        metadata["_retrieval_sources"] = ordered_sources
        enriched_documents.append(RetrievedDocument(document=document.document, metadata=metadata))
    return enriched_documents


def documents_to_raw_results(documents: list[RetrievedDocument]) -> dict[str, Any]:
    """Convert normalized retrieved documents back to the graph raw-results shape."""

    if not documents:
        return empty_hybrid_result()

    return {
        "ids": [[document_identity(document) for document in documents]],
        "documents": [[document.document for document in documents]],
        "metadatas": [[dict(document.metadata) for document in documents]],
    }


def empty_hybrid_result() -> dict[str, Any]:
    """Return a fresh empty Chroma-like result shape."""

    return {key: [list(values[0])] for key, values in EMPTY_HYBRID_RESULT.items()}
