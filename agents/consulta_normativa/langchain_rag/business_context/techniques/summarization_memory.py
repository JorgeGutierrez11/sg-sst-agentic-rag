"""Summarization-Based Conversational Memory technique."""

import logging
from typing import Any

from agents.consulta_normativa.langchain_rag.business_context.models import (
    BusinessContext,
    ConversationTurn,
)
from agents.consulta_normativa.langchain_rag.core.llm import invoke_llm_text


logger = logging.getLogger(__name__)

# Cantidad de turnos recientes que nunca se resumen.
RECENT_TURNS_TO_KEEP = 2


SUMMARY_SYSTEM_PROMPT = """
Eres un componente de memoria conversacional para un agente de consulta
normativa sobre SG-SST en Colombia.

Tu tarea es mantener un resumen acumulado de conversaciones anteriores.

REGLAS:

- Resume únicamente la información presente en el resumen anterior y en los
  nuevos turnos proporcionados.
- Conserva hechos empresariales relevantes.
- Conserva accidentes, incidentes y otros eventos mencionados por el usuario.
- Conserva conclusiones importantes dadas anteriormente por el agente.
- Conserva cantidades de trabajadores, actividades económicas, códigos CIIU,
  clases de riesgo y otros datos concretos cuando aparezcan.
- Conserva información necesaria para entender referencias posteriores como
  "ese accidente", "lo anterior", "en ese caso" o expresiones similares.
- No agregues información nueva.
- No uses conocimiento externo.
- No respondas preguntas pendientes.
- No interpretes normativa adicional.
- Elimina redundancias y detalles innecesarios.
- Produce un resumen compacto pero suficiente para mantener continuidad
  conversacional.
""".strip()


def get_turns_pending_summarization(
    business_context: BusinessContext,
) -> list[ConversationTurn]:
    """Return old turns not yet included in the accumulated summary."""

    history = business_context.get("history", [])

    summarized_turns = business_context.get(
        "summarized_turns",
        0,
    )

    # Siempre dejamos los últimos N turnos sin resumir.
    summary_limit = max(
        0,
        len(history) - RECENT_TURNS_TO_KEEP,
    )

    # No existe nada nuevo que resumir.
    if summarized_turns >= summary_limit:
        return []

    return list(
        history[summarized_turns:summary_limit]
    )


def get_recent_turns(
    business_context: BusinessContext,
) -> list[ConversationTurn]:
    """Return conversation turns that must remain uncompressed."""

    history = business_context.get("history", [])

    if len(history) <= RECENT_TURNS_TO_KEEP:
        return list(history)

    return list(
        history[-RECENT_TURNS_TO_KEEP:]
    )


def update_conversation_summary(
    llm: Any,
    business_context: BusinessContext,
) -> BusinessContext:
    """Incrementally summarize old conversation turns."""

    updated_context: BusinessContext = dict(
        business_context
    )

    pending_turns = get_turns_pending_summarization(
        business_context
    )

    # No hay nuevos turnos suficientemente antiguos para resumir.
    if not pending_turns:
        return updated_context

    previous_summary = business_context.get(
        "history_summary",
        "",
    )

    pending_text = _format_turns(
        pending_turns
    )

    try:
        messages = _build_summary_messages(
            previous_summary=previous_summary,
            pending_turns=pending_text,
        )

        summary = invoke_llm_text(
            llm,
            messages,
        ).strip()

    except Exception as error:
        logger.error(
            "Conversation summarization failed: %s",
            error,
        )

        # Fail-safe:
        # si falla el resumen, no marcamos turnos como resumidos.
        return updated_context

    if not summary:
        return updated_context

    updated_context["history_summary"] = summary

    # Todos los turnos excepto los dos recientes ya forman
    # parte del nuevo resumen acumulado.
    updated_context["summarized_turns"] = max(
        0,
        len(business_context.get("history", []))
        - RECENT_TURNS_TO_KEEP,
    )

    return updated_context


def _format_turns(
    turns: list[ConversationTurn],
) -> str:
    """Format conversation turns for summarization."""

    formatted_turns: list[str] = []

    for index, turn in enumerate(
        turns,
        start=1,
    ):
        formatted_turns.append(
            "\n".join(
                [
                    f"Turno {index}",
                    f"Usuario: {turn['user']}",
                    f"Agente: {turn['assistant']}",
                ]
            )
        )

    return "\n\n".join(
        formatted_turns
    )


def _build_summary_messages(
    previous_summary: str,
    pending_turns: str,
) -> list[Any]:
    """Build LangChain messages for incremental summarization."""

    try:
        # pyrefly: ignore [missing-import]
        from langchain_core.messages import (
            HumanMessage,
            SystemMessage,
        )
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            f"langchain is not installed: {error}"
        ) from error

    if previous_summary:
        human_content = (
            "RESUMEN ANTERIOR:\n"
            f"{previous_summary}\n\n"
            "NUEVOS TURNOS A INCORPORAR:\n"
            f"{pending_turns}\n\n"
            "Genera el nuevo resumen acumulado."
        )
    else:
        human_content = (
            "TURNOS A RESUMIR:\n"
            f"{pending_turns}\n\n"
            "Genera el resumen inicial."
        )

    return [
        SystemMessage(
            content=SUMMARY_SYSTEM_PROMPT,
        ),
        HumanMessage(
            content=human_content,
        ),
    ]


def build_summarization_context(
    business_context: BusinessContext,
) -> BusinessContext:
    """Build current context from profile, summary and unsummarized turns."""

    updated_context: BusinessContext = dict(
        business_context
    )

    profile = business_context.get(
        "profile",
        {},
    )

    history = business_context.get(
        "history",
        [],
    )

    history_summary = business_context.get(
        "history_summary",
        "",
    )

    summarized_turns = business_context.get(
        "summarized_turns",
        0,
    )

    sections: list[str] = []

    profile_text = _format_profile(
        profile
    )

    if profile_text:
        sections.append(
            "PERFIL EMPRESARIAL\n"
            f"{profile_text}"
        )

    if history_summary:
        sections.append(
            "RESUMEN DE CONVERSACIONES ANTERIORES\n"
            f"{history_summary}"
        )

    # Todo lo que todavía no esté incluido en el resumen
    # debe permanecer disponible literalmente.
    unsummarized_turns = history[
        summarized_turns:
    ]

    if unsummarized_turns:
        recent_text = _format_turns(
            unsummarized_turns
        )

        sections.append(
            "CONVERSACIÓN RECIENTE\n"
            f"{recent_text}"
        )

    updated_context["current_context"] = (
        "\n\n".join(sections)
    )

    return updated_context


def _format_profile(
    profile: dict[str, Any],
) -> str:
    """Format business profile for current context."""

    fields = [
        (
            "Actividad económica",
            profile.get("economic_activity"),
        ),
        (
            "Código CIIU",
            profile.get("ciiu_code"),
        ),
        (
            "Número de trabajadores",
            profile.get("worker_count"),
        ),
        (
            "Clase de riesgo",
            profile.get("risk_class"),
        ),
    ]

    return "\n".join(
        f"- {label}: {value}"
        for label, value in fields
        if value is not None
    )


from collections.abc import Callable

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState


def summarization_memory_node(
    llm: Any,
) -> Callable[[RagGraphState], RagGraphState]:
    """Build a node that updates the summary and prepares current context."""

    def run(
        state: RagGraphState,
    ) -> RagGraphState:
        business_context = state.get(
            "business_context",
            {},
        )

        # 1. Actualizar resumen incremental si existen
        #    turnos suficientemente antiguos.
        updated_context = update_conversation_summary(
            llm=llm,
            business_context=business_context,
        )

        # 2. Construir el contexto que consumirán
        #    las etapas posteriores.
        updated_context = build_summarization_context(
            business_context=updated_context,
        )

        return {
            "business_context": updated_context,
        }

    return run