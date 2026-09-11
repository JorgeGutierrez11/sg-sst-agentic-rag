"""Full Conversation Memory technique for business context."""

from agents.consulta_normativa.langchain_rag.business_context.models import (
    BusinessContext,
    BusinessProfile,
    ConversationTurn,
)
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState



def build_full_conversation_context(
    business_context: BusinessContext,
) -> BusinessContext:
    """Build current context using the complete business profile and history."""

    updated_context: BusinessContext = dict(business_context)

    profile = business_context.get("profile", {})
    history = business_context.get("history", [])

    sections: list[str] = []

    profile_context = _format_profile(profile)

    if profile_context:
        sections.append(
            "PERFIL EMPRESARIAL\n"
            f"{profile_context}"
        )

    history_context = _format_history(history)

    if history_context:
        sections.append(
            "HISTORIAL DE CONVERSACIÓN\n"
            f"{history_context}"
        )

    updated_context["current_context"] = "\n\n".join(sections)

    return updated_context


def full_conversation_memory_node(
    state: RagGraphState,
) -> RagGraphState:
    """Build current business context using the complete profile and history."""

    business_context = state.get("business_context", {})

    updated_context = build_full_conversation_context(
        business_context=business_context,
    )

    return {
        "business_context": updated_context,
    }


def _format_profile(
    profile: BusinessProfile,
) -> str:
    """Format the business profile for downstream consumption."""

    fields = [
        ("Actividad económica", profile.get("economic_activity")),
        ("Código CIIU", profile.get("ciiu_code")),
        ("Número de trabajadores", profile.get("worker_count")),
        ("Clase de riesgo", profile.get("risk_class")),
    ]

    lines = [
        f"- {label}: {value}"
        for label, value in fields
        if value is not None
    ]

    return "\n".join(lines)


def _format_history(
    history: list[ConversationTurn],
) -> str:
    """Format the complete conversation history."""

    turns: list[str] = []

    for index, turn in enumerate(history, start=1):
        turns.append(
            "\n".join(
                [
                    f"Turno {index}",
                    f"Usuario: {turn['user']}",
                    f"Agente: {turn['assistant']}",
                ]
            )
        )

    return "\n\n".join(turns)