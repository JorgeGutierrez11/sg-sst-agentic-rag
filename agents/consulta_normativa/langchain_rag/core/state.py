"""State contract for the LangGraph RAG flow."""

from operator import add
from typing import Annotated, Any, TypedDict

from agents.consulta_normativa.langchain_rag.models import (
    LangChainRagResult,
    RetrievedDocument,
)

from agents.consulta_normativa.langchain_rag.business_context.models import (
    BusinessContext,
)


class RagGraphState(TypedDict, total=False):
    """State passed through the LangGraph RAG flow."""

    question: str
    raw_results: dict[str, Any]
    documents: list[RetrievedDocument]
    retrieval_traces: list[dict[str, Any]]
    reranking_trace: dict[str, Any]

    context: str
    references: list[str]
    messages: list[Any]
    prompt: str
    answer: str
    result: LangChainRagResult

    # Business Context
    business_context: BusinessContext

    # Rewrite Query
    retrieval_query: str
    query_rewrite_trace: dict[str, Any]
    query_expansion_trace: dict[str, Any]

    # Multi-Query
    query_variants: list[str]
    multi_query_trace: dict[str, Any]
    retrieved_lists: Annotated[list[list[RetrievedDocument]], add]

    # Retrieval Relevance Grading
    relevance_grading_trace: dict[str, Any]

    # Sufficient-Context Gate
    context_sufficiency: str
    sufficient_context_trace: dict[str, Any]

    # Self-Refine
    self_refine_trace: dict[str, Any]
