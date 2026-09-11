"""LangGraph node for storing conversation turns."""

from agents.consulta_normativa.langchain_rag.business_context.history import (
    append_conversation_turn,
)
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState


def save_conversation_turn_node(
    state: RagGraphState,
) -> RagGraphState:
    """Store the current user question and assistant answer."""

    business_context = state.get("business_context", {})

    updated_context = append_conversation_turn(
        business_context=business_context,
        user_message=state["question"],
        assistant_message=state["answer"],
    )

    return {
        "business_context": updated_context,
    }