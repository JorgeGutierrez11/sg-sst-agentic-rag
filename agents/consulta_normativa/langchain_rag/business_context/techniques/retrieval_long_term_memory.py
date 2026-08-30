"""Retrieval-Based Long-Term Memory technique."""

from typing import Any

from agents.consulta_normativa.langchain_rag.business_context.models import (
    ConversationTurn,
    RetrievedBusinessMemory,
)
from agents.consulta_normativa.langchain_rag.business_context.models import (
    BusinessContext,
    ConversationTurn,
    RetrievedBusinessMemory,
)
from langchain_core.runnables import RunnableConfig

from collections.abc import Callable

from langgraph.runtime import Runtime

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState


DEFAULT_MEMORY_TOP_K = 3


def build_memory_text(
    turn: ConversationTurn,
) -> str:
    """Build text used for semantic retrieval."""

    return turn["user"]


def store_conversation_memory(
    store: Any,
    namespace: tuple[str, ...],
    memory_id: str,
    turn: ConversationTurn,
) -> None:
    """Store one conversation turn as a searchable long-term memory."""

    memory_text = build_memory_text(turn)

    store.put(
        namespace,
        memory_id,
        {
            "text": memory_text,
            "user": turn["user"],
            "assistant": turn["assistant"],
        },
        index=["text"],
    )


def search_relevant_memories(
    store: Any,
    namespace: tuple[str, ...],
    query: str,
    limit: int = DEFAULT_MEMORY_TOP_K,
) -> list[RetrievedBusinessMemory]:
    """Retrieve conversation memories semantically related to the query."""

    normalized_query = query.strip()

    if not normalized_query:
        return []

    if limit <= 0:
        return []

    items = store.search(
        namespace,
        query=normalized_query,
        limit=limit,
    )

    memories: list[RetrievedBusinessMemory] = []

    for item in items:
        value = getattr(
            item,
            "value",
            {},
        )

        if not isinstance(value, dict):
            continue

        user = value.get("user")
        assistant = value.get("assistant")

        if not isinstance(user, str):
            continue

        if not isinstance(assistant, str):
            continue

        memory_id = str(
            getattr(item, "key", "")
        )

        raw_score = getattr(
            item,
            "score",
            None,
        )

        score: float | None = None

        if isinstance(raw_score, (int, float)) and not isinstance(
            raw_score,
            bool,
        ):
            score = float(raw_score)

        memories.append(
            {
                "memory_id": memory_id,
                "user": user,
                "assistant": assistant,
                "score": score,
            }
        )

    return memories


def build_memory_namespace(
    thread_id: str,
) -> tuple[str, ...]:
    """Build an isolated memory namespace for one conversation."""

    normalized_thread_id = thread_id.strip()

    if not normalized_thread_id:
        raise ValueError("thread_id cannot be empty.")

    return (
        "business-context",
        normalized_thread_id,
    )



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


def _format_retrieved_memories(
    memories: list[RetrievedBusinessMemory],
) -> str:
    """Format retrieved memories for current context."""

    formatted: list[str] = []

    for index, memory in enumerate(
        memories,
        start=1,
    ):
        formatted.append(
            "\n".join(
                [
                    f"Memoria {index}",
                    f"Usuario: {memory['user']}",
                    f"Agente: {memory['assistant']}",
                ]
            )
        )

    return "\n\n".join(formatted)


def _get_thread_id(
    config: RunnableConfig,
) -> str | None:
    """Extract the current conversation thread identifier."""

    configurable = config.get(
        "configurable",
        {},
    )

    thread_id = configurable.get(
        "thread_id"
    )

    if not isinstance(thread_id, str):
        return None

    normalized_thread_id = thread_id.strip()

    if not normalized_thread_id:
        return None

    return normalized_thread_id


def build_retrieval_memory_context(
    business_context: BusinessContext,
) -> BusinessContext:
    """Build current context from profile and retrieved memories."""

    updated_context: BusinessContext = dict(
        business_context
    )

    profile = business_context.get(
        "profile",
        {},
    )

    retrieved_memories = business_context.get(
        "retrieved_memories",
        [],
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

    memories_text = _format_retrieved_memories(
        retrieved_memories
    )

    if memories_text:
        sections.append(
            "MEMORIA CONVERSACIONAL RECUPERADA\n"
            f"{memories_text}"
        )

    updated_context["current_context"] = (
        "\n\n".join(sections)
    )

    return updated_context


def retrieval_long_term_memory_node(
    limit: int = DEFAULT_MEMORY_TOP_K,
) -> Callable[..., RagGraphState]:
    """Build a node that retrieves relevant memories for the current question."""

    def run(
        state: RagGraphState,
        config: RunnableConfig,
        runtime: Runtime,
    ) -> RagGraphState:
        business_context = state.get(
            "business_context",
            {},
        )

        store = runtime.store

        thread_id = _get_thread_id(
            config
        )

        # Fail-safe: sin Store o thread_id no se recupera memoria.
        if store is None or thread_id is None:
            updated_context: BusinessContext = dict(
                business_context
            )

            updated_context["retrieved_memories"] = []

            updated_context = build_retrieval_memory_context(
                updated_context
            )

            return {
                "business_context": updated_context,
            }

        namespace = build_memory_namespace(
            thread_id
        )

        memories = search_relevant_memories(
            store=store,
            namespace=namespace,
            query=state["question"],
            limit=limit,
        )

        updated_context: BusinessContext = dict(
            business_context
        )

        updated_context["retrieved_memories"] = memories

        updated_context = build_retrieval_memory_context(
            updated_context
        )

        return {
            "business_context": updated_context,
        }

    return run


def store_latest_conversation_memory_node(
    state: RagGraphState,
    config: RunnableConfig,
    runtime: Runtime,
) -> RagGraphState:
    """Store the latest completed conversation turn in long-term memory."""

    store = runtime.store

    thread_id = _get_thread_id(
        config
    )

    if store is None or thread_id is None:
        return {}

    business_context = state.get(
        "business_context",
        {},
    )

    history = business_context.get(
        "history",
        [],
    )

    if not history:
        return {}

    latest_turn = history[-1]

    namespace = build_memory_namespace(
        thread_id
    )

    memory_id = f"turn-{len(history)}"

    store_conversation_memory(
        store=store,
        namespace=namespace,
        memory_id=memory_id,
        turn=latest_turn,
    )

    return {}