"""Conversation history utilities for business context."""

from agents.consulta_normativa.langchain_rag.business_context.models import (
    BusinessContext,
    ConversationTurn,
)


def append_conversation_turn(
    business_context: BusinessContext,
    user_message: str,
    assistant_message: str,
) -> BusinessContext:
    """Append one complete conversation turn without mutating the input."""

    updated_context: BusinessContext = dict(business_context)

    history = list(
        business_context.get("history", [])
    )

    turn: ConversationTurn = {
        "user": user_message,
        "assistant": assistant_message,
    }

    history.append(turn)

    updated_context["history"] = history

    return updated_context