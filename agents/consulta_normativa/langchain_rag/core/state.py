"""State contract for the LangGraph RAG flow."""

from typing import Any, TypedDict

from agents.consulta_normativa.langchain_rag.models import LangChainRagResult, RetrievedDocument

# Business context
from agents.consulta_normativa.langchain_rag.business_context.models import (BusinessContext,)


class RagGraphState(TypedDict, total=False):
    """State passed through the minimal LangGraph RAG flow."""

    question: str
    raw_results: dict[str, Any]
    documents: list[RetrievedDocument]
    retrieval_traces: list[dict[str, Any]]
    context: str
    references: list[str]
    messages: list[Any]
    prompt: str
    answer: str
    result: LangChainRagResult

    # Business Context
    business_context: BusinessContext


    """# Rewrite Query
    retrieval_query: str
    query_rewrite_trace: dict[str, Any]

    # Retrieval Relevance Grading
    relevance_grading_trace: dict[str, Any]

    # Sufficient-Context Gate
    context_sufficiency: str
    sufficient_context_trace: dict[str, Any]

    # Self-Refine
    self_refine_trace: dict[str, Any]"""
