"""Instrumentation nodes for the LangGraph RAG flow."""

from typing import Any

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState


def record_retrieval_trace_node(state: RagGraphState) -> RagGraphState:
    """Record retrieval metadata without changing selected documents."""

    documents = state.get("documents", [])
    traces: list[dict[str, Any]] = list(state.get("retrieval_traces", []))
    traces.append({"document_count": len(documents)})
    return {"retrieval_traces": traces}
