"""Conditional routes for the LangGraph RAG flow."""

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState


def evidence_route(state: RagGraphState) -> str:
    """Return the next graph route based on retrieved document availability."""

    return "with_evidence" if state.get("documents") else "without_evidence"

# validation route for sufficient_context_gate.py

def sufficient_context_route(state: RagGraphState) -> str:
    """Route according to the sufficient-context assessment."""

    if state.get("context_sufficiency") == "insufficient":
        return "insufficient"

    if state.get("context_sufficiency") == "partial":
        return "partial"

    return "answerable"
