"""Query-only Hybrid Retrieval helpers for dense Chroma and sparse BM25."""

from agents.consulta_normativa.langchain_rag.formatting import first_result_list
from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.formatting import recovered_documents
from agents.consulta_normativa.langchain_rag.models import RetrievedDocument
from agents.consulta_normativa.langchain_rag.retrieval.fusion import document_identity, reciprocal_rank_fusion
from agents.shared import bm25_retrieval, chroma_retrieval
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMPTY_HYBRID_RESULT = {"ids": [[]], "documents": [[]], "metadatas": [[]]}



def hybrid_retriever(
    dense_collection: Any,
    sparse_index: Any,
    *,
    candidate_top_k: int,
    rrf_k: int,
) -> Callable[[str, int], dict[str, Any]]:
    """Build a graph-compatible retriever that fuses Chroma and BM25 rankings with RRF."""

    def retrieve(query: str, top_k: int) -> dict[str, Any]:
        if top_k <= 0:
            return empty_hybrid_result()

        dense_raw = chroma_retrieval.query_top_k(dense_collection, query, candidate_top_k)
        sparse_raw = bm25_retrieval.query_top_k(sparse_index, query, candidate_top_k)

        dense_documents = recovered_documents(dense_raw)
        sparse_documents = recovered_documents(sparse_raw)

        # log_raw_retrieval_results("chroma", dense_raw, query)
        # log_raw_retrieval_results("bm25", sparse_raw, query)

        fused_documents = reciprocal_rank_fusion([dense_documents, sparse_documents], k=rrf_k)
        enriched_documents = add_retrieval_source_metadata(fused_documents[:top_k], dense_documents, sparse_documents)
        return documents_to_raw_results(enriched_documents)

    return retrieve


def add_retrieval_source_metadata(
    documents: list[RetrievedDocument],
    dense_documents: list[RetrievedDocument],
    sparse_documents: list[RetrievedDocument],
) -> list[RetrievedDocument]:
    """Add internal retrieval-source metadata without changing document order."""

    sources_by_identity: dict[str, set[str]] = {}
    for source_name, source_documents in (("chroma", dense_documents), ("bm25", sparse_documents)):
        for source_document in source_documents:
            sources_by_identity.setdefault(document_identity(source_document), set()).add(source_name)

    enriched_documents = []
    for document in documents:
        sources = sources_by_identity.get(document_identity(document), set())
        ordered_sources = [source for source in ("chroma", "bm25") if source in sources]
        metadata = dict(document.metadata)
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


def log_raw_retrieval_results(source: str, raw_results: dict[str, Any], query: str) -> None:
    """Log compact raw retrieval candidates before fusion."""

    ids = first_result_list(raw_results, "ids")
    documents = first_result_list(raw_results, "documents")
    metadatas = first_result_list(raw_results, "metadatas")
    distances = first_result_list(raw_results, "distances")
    scores = first_result_list(raw_results, "scores")

    logger.info("%s retrieval candidates for query: %s", source, query)

    for index, document_id in enumerate(ids, start=1):
        document = str(documents[index - 1]) if index - 1 < len(documents) else ""
        metadata = metadatas[index - 1] if index - 1 < len(metadatas) else {}
        score = scores[index - 1] if index - 1 < len(scores) else None
        distance = distances[index - 1] if index - 1 < len(distances) else None

        logger.info(
            "%s rank=%s id=%s score=%s distance=%s source=%s contains_4711=%s preview=%s",
            source,
            index,
            document_id,
            score,
            distance,
            metadata.get("source_stem") if isinstance(metadata, dict) else None,
            "4711" in document,
            document[:180].replace("\n", " "),
        )