"""Retrieval-Based Long-Term Memory technique."""

from collections.abc import Callable
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from agents.consulta_normativa.langchain_rag.business_context.models import (
    BusinessContext,
    ConversationTurn,
    RetrievedBusinessMemory,
)
from agents.consulta_normativa.langchain_rag.core.state import (
    RagGraphState,
)


DEFAULT_MEMORY_TOP_K = 3


# ============================================================
# Memory storage
# ============================================================


def build_memory_text(
    turn: ConversationTurn,
) -> str:
    """
    Build the text indexed for semantic retrieval.

    Only the user's message is embedded because retrieval
    should match the current user query against previous
    user intents/questions.

    The assistant response is still stored as payload and
    becomes available once the memory is retrieved.
    """

    return turn["user"]


def store_conversation_memory(
    store: Any,
    namespace: tuple[str, ...],
    memory_id: str,
    turn: ConversationTurn,
) -> None:
    """Store one conversation turn as searchable long-term memory."""

    memory_text = build_memory_text(
        turn
    )

    store.put(
        namespace,
        memory_id,
        {
            "text": memory_text,
            "user": turn["user"],
            "assistant": turn["assistant"],
        },
        index=[
            "text",
        ],
    )


# ============================================================
# Semantic retrieval
# ============================================================


def search_relevant_memories(
    store: Any,
    namespace: tuple[str, ...],
    query: str,
    limit: int = DEFAULT_MEMORY_TOP_K,
) -> list[RetrievedBusinessMemory]:
    """
    Retrieve previous conversation memories semantically
    related to the current user query.
    """

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

    memories: list[
        RetrievedBusinessMemory
    ] = []

    for item in items:
        value = getattr(
            item,
            "value",
            {},
        )

        if not isinstance(
            value,
            dict,
        ):
            continue

        user = value.get(
            "user"
        )

        assistant = value.get(
            "assistant"
        )

        if not isinstance(
            user,
            str,
        ):
            continue

        if not isinstance(
            assistant,
            str,
        ):
            continue

        memory_id = str(
            getattr(
                item,
                "key",
                "",
            )
        )

        raw_score = getattr(
            item,
            "score",
            None,
        )

        score: float | None = None

        if (
            isinstance(
                raw_score,
                (int, float),
            )
            and not isinstance(
                raw_score,
                bool,
            )
        ):
            score = float(
                raw_score
            )

        memories.append(
            {
                "memory_id": memory_id,
                "user": user,
                "assistant": assistant,
                "score": score,
            }
        )

    return memories


# ============================================================
# Memory namespace
# ============================================================


def build_memory_namespace(
    thread_id: str,
) -> tuple[str, ...]:
    """
    Build an isolated semantic-memory namespace.

    Each B2 thread gets a different namespace, preventing
    one company's memories from leaking into another.
    """

    normalized_thread_id = (
        thread_id.strip()
    )

    if not normalized_thread_id:
        raise ValueError(
            "thread_id cannot be empty."
        )

    return (
        "business-context",
        normalized_thread_id,
    )


def _get_thread_id(
    config: RunnableConfig,
) -> str | None:
    """
    Extract thread_id from LangGraph RunnableConfig.

    Important:
    thread_id must come from:

        config["configurable"]["thread_id"]

    and not from runtime.execution_info, because that
    attribute is not available in the current LangGraph
    Runtime used by the project.
    """

    configurable = config.get(
        "configurable",
        {},
    )

    if not isinstance(
        configurable,
        dict,
    ):
        return None

    thread_id = configurable.get(
        "thread_id"
    )

    if not isinstance(
        thread_id,
        str,
    ):
        return None

    normalized_thread_id = (
        thread_id.strip()
    )

    if not normalized_thread_id:
        return None

    return normalized_thread_id


# ============================================================
# Formatting
# ============================================================


def _format_profile(
    profile: dict[str, Any],
) -> str:
    """Format the structured business profile."""

    fields = [
        (
            "Actividad económica",
            profile.get(
                "economic_activity"
            ),
        ),
        (
            "Código CIIU",
            profile.get(
                "ciiu_code"
            ),
        ),
        (
            "Número de trabajadores",
            profile.get(
                "worker_count"
            ),
        ),
        (
            "Clase de riesgo",
            profile.get(
                "risk_class"
            ),
        ),
    ]

    return "\n".join(
        f"- {label}: {value}"
        for label, value in fields
        if value is not None
    )


def _format_retrieved_memories(
    memories: list[
        RetrievedBusinessMemory
    ],
) -> str:
    """Format semantically retrieved memories for generation."""

    formatted: list[str] = []

    for index, memory in enumerate(
        memories,
        start=1,
    ):
        formatted.append(
            "\n".join(
                [
                    f"Memoria {index}",
                    (
                        "Usuario: "
                        f"{memory['user']}"
                    ),
                    (
                        "Agente: "
                        f"{memory['assistant']}"
                    ),
                ]
            )
        )

    return "\n\n".join(
        formatted
    )


def build_retrieval_memory_context(
    business_context: BusinessContext,
) -> BusinessContext:
    """
    Build current_context from:

        business profile
        +
        semantically retrieved memories

    It intentionally does NOT include the full conversation
    history because that would turn the experiment into
    Full Conversation Memory.
    """

    updated_context: BusinessContext = dict(
        business_context
    )

    raw_profile = business_context.get(
        "profile",
        {},
    )

    profile: dict[str, Any]

    if isinstance(
        raw_profile,
        dict,
    ):
        profile = raw_profile
    else:
        profile = {}

    raw_memories = business_context.get(
        "retrieved_memories",
        [],
    )

    retrieved_memories: list[
        RetrievedBusinessMemory
    ]

    if isinstance(
        raw_memories,
        list,
    ):
        retrieved_memories = raw_memories
    else:
        retrieved_memories = []

    sections: list[str] = []

    profile_text = _format_profile(
        profile
    )

    if profile_text:
        sections.append(
            "PERFIL EMPRESARIAL\n"
            f"{profile_text}"
        )

    memories_text = (
        _format_retrieved_memories(
            retrieved_memories
        )
    )

    if memories_text:
        sections.append(
            "MEMORIA CONVERSACIONAL RECUPERADA\n"
            f"{memories_text}"
        )

    updated_context[
        "current_context"
    ] = "\n\n".join(
        sections
    )

    return updated_context


# ============================================================
# Retrieval node
# ============================================================


def retrieval_long_term_memory_node(
    limit: int = DEFAULT_MEMORY_TOP_K,
) -> Callable[..., RagGraphState]:
    """
    Build the Retrieval-Based Long-Term Memory node.

    For every question:

        current question
              ↓
        semantic Store search
              ↓
        top-k relevant previous turns
              ↓
        profile + retrieved memories
              ↓
        business_context.current_context

    The technique does not modify the normative retrieval query.
    """

    def run(
        state: RagGraphState,
        config: RunnableConfig,
        runtime: Runtime,
    ) -> RagGraphState:

        raw_business_context = (
            state.get(
                "business_context",
                {},
            )
        )

        business_context: BusinessContext

        if isinstance(
            raw_business_context,
            dict,
        ):
            business_context = (
                raw_business_context
            )
        else:
            business_context = {}

        store = runtime.store

        thread_id = _get_thread_id(
            config
        )

        # ----------------------------------------------------
        # Fail-safe
        # ----------------------------------------------------
        # If semantic Store or thread_id is unavailable,
        # preserve the business profile but retrieve no
        # conversational memories.
        # ----------------------------------------------------

        if (
            store is None
            or thread_id is None
        ):
            updated_context: BusinessContext = dict(
                business_context
            )

            updated_context[
                "retrieved_memories"
            ] = []

            updated_context = (
                build_retrieval_memory_context(
                    updated_context
                )
            )

            return {
                "business_context": (
                    updated_context
                ),
            }

        # ----------------------------------------------------
        # Thread-isolated semantic namespace
        # ----------------------------------------------------

        namespace = (
            build_memory_namespace(
                thread_id
            )
        )

        # ----------------------------------------------------
        # Semantic search
        # ----------------------------------------------------

        memories = (
            search_relevant_memories(
                store=store,
                namespace=namespace,
                query=state.get(
                    "question",
                    "",
                ),
                limit=limit,
            )
        )

        # ----------------------------------------------------
        # Build current business context
        # ----------------------------------------------------

        updated_context: BusinessContext = dict(
            business_context
        )

        updated_context[
            "retrieved_memories"
        ] = memories

        updated_context = (
            build_retrieval_memory_context(
                updated_context
            )
        )

        return {
            "business_context": (
                updated_context
            ),
        }

    return run


# ============================================================
# Store current completed turn
# ============================================================


def store_latest_conversation_memory_node(
    state: RagGraphState,
    config: RunnableConfig,
    runtime: Runtime,
) -> RagGraphState:
    """
    Store the latest completed conversation turn.

    This node must execute AFTER save_conversation_turn_node.

    Therefore the current question cannot retrieve itself;
    it only becomes searchable for future turns.
    """

    store = runtime.store

    thread_id = _get_thread_id(
        config
    )

    # Fail-safe.
    if (
        store is None
        or thread_id is None
    ):
        return {}

    raw_business_context = (
        state.get(
            "business_context",
            {},
        )
    )

    if not isinstance(
        raw_business_context,
        dict,
    ):
        return {}

    business_context: BusinessContext = (
        raw_business_context
    )

    history = business_context.get(
        "history",
        [],
    )

    if not isinstance(
        history,
        list,
    ):
        return {}

    if not history:
        return {}

    latest_turn = history[-1]

    if not isinstance(
        latest_turn,
        dict,
    ):
        return {}

    user = latest_turn.get(
        "user"
    )

    assistant = latest_turn.get(
        "assistant"
    )

    if not isinstance(
        user,
        str,
    ):
        return {}

    if not isinstance(
        assistant,
        str,
    ):
        return {}

    turn: ConversationTurn = {
        "user": user,
        "assistant": assistant,
    }

    namespace = (
        build_memory_namespace(
            thread_id
        )
    )

    # One deterministic memory identifier per completed turn.
    memory_id = (
        f"turn-{len(history)}"
    )

    store_conversation_memory(
        store=store,
        namespace=namespace,
        memory_id=memory_id,
        turn=turn,
    )

    return {}