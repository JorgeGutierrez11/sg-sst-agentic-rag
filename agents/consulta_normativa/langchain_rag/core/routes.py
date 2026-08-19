"""Conditional routes for the LangGraph RAG flow."""

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState


def evidence_route(state: RagGraphState) -> str:
    """Return the next graph route based on retrieved document availability."""

    return "with_evidence" if state.get("documents") else "without_evidence"
