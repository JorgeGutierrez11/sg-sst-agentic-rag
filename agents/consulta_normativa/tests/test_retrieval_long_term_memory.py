from collections.abc import Sequence

from langgraph.store.memory import InMemoryStore

from agents.consulta_normativa.langchain_rag.business_context.techniques.retrieval_long_term_memory import (
    build_memory_text,
    search_relevant_memories,
    store_conversation_memory,
)
from agents.consulta_normativa.langchain_rag.business_context.techniques.retrieval_long_term_memory import (
    build_memory_namespace,
)

from agents.consulta_normativa.langchain_rag.business_context.techniques.retrieval_long_term_memory import (
    build_retrieval_memory_context,
)


from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState

from agents.consulta_normativa.langchain_rag.business_context.techniques.retrieval_long_term_memory import (
    retrieval_long_term_memory_node,
    store_latest_conversation_memory_node,
)

def fake_embeddings(
    texts: Sequence[str],
) -> list[list[float]]:
    """Deterministic embeddings for semantic-memory tests."""

    vectors: list[list[float]] = []

    for text in texts:
        normalized = text.lower()

        if "accidente" in normalized:
            vectors.append([1.0, 0.0, 0.0])

        elif "panadería" in normalized or "panaderia" in normalized:
            vectors.append([0.0, 1.0, 0.0])

        elif "copasst" in normalized:
            vectors.append([0.0, 0.0, 1.0])

        else:
            vectors.append([0.1, 0.1, 0.1])

    return vectors


def build_test_store() -> InMemoryStore:
    return InMemoryStore(
        index={
            "embed": fake_embeddings,
            "dims": 3,
            "fields": ["text"],
        }
    )


def test_build_memory_text() -> None:
    turn = {
        "user": "Tengo 8 trabajadores.",
        "assistant": "Información registrada.",
    }

    result = build_memory_text(turn)

    assert result == "Tengo 8 trabajadores."
    assert "Información registrada." not in result
    assert "Agente:" not in result


def test_stores_conversation_memory() -> None:
    store = build_test_store()

    namespace = (
        "business-context",
        "company-1",
    )

    turn = {
        "user": "Somos una panadería.",
        "assistant": "La actividad económica indicada es panadería.",
    }

    store_conversation_memory(
        store=store,
        namespace=namespace,
        memory_id="turn-1",
        turn=turn,
    )

    item = store.get(
        namespace,
        "turn-1",
    )

    assert item is not None

    assert item.value["user"] == (
        "Somos una panadería."
    )

    assert item.value["assistant"] == (
        "La actividad económica indicada es panadería."
    )

    assert "panadería" in item.value["text"]


def test_retrieves_semantically_related_memory() -> None:
    store = build_test_store()

    namespace = (
        "business-context",
        "company-1",
    )

    store_conversation_memory(
        store,
        namespace,
        "turn-1",
        {
            "user": "Tuve un accidente con un trabajador.",
            "assistant": "Se explicó cómo investigar el accidente.",
        },
    )

    store_conversation_memory(
        store,
        namespace,
        "turn-2",
        {
            "user": "Somos una panadería.",
            "assistant": "Se explicó la actividad económica.",
        },
    )

    store_conversation_memory(
        store,
        namespace,
        "turn-3",
        {
            "user": "¿Debo tener COPASST?",
            "assistant": "Se explicó el requisito del COPASST.",
        },
    )

    memories = search_relevant_memories(
        store=store,
        namespace=namespace,
        query="¿Qué habíamos hablado del accidente?",
        limit=1,
    )

    assert len(memories) == 1

    assert memories[0]["memory_id"] == "turn-1"

    assert memories[0]["user"] == (
        "Tuve un accidente con un trabajador."
    )

    assert memories[0]["score"] is not None


def test_respects_top_k() -> None:
    store = build_test_store()

    namespace = (
        "business-context",
        "company-1",
    )

    for number in range(5):
        store_conversation_memory(
            store,
            namespace,
            f"turn-{number}",
            {
                "user": f"Accidente número {number}",
                "assistant": f"Respuesta número {number}",
            },
        )

    memories = search_relevant_memories(
        store=store,
        namespace=namespace,
        query="accidente",
        limit=2,
    )

    assert len(memories) == 2


def test_empty_query_returns_no_memories() -> None:
    store = build_test_store()

    memories = search_relevant_memories(
        store=store,
        namespace=("business-context", "company-1"),
        query="   ",
    )

    assert memories == []


def test_memory_namespaces_isolate_conversations() -> None:
    store = build_test_store()

    namespace_a = build_memory_namespace(
        "thread-a"
    )

    namespace_b = build_memory_namespace(
        "thread-b"
    )

    store_conversation_memory(
        store,
        namespace_a,
        "turn-1",
        {
            "user": "Tuve un accidente con un trabajador.",
            "assistant": "Se explicó cómo investigar el accidente.",
        },
    )

    store_conversation_memory(
        store,
        namespace_b,
        "turn-1",
        {
            "user": "Somos una panadería.",
            "assistant": "Se explicó la actividad económica.",
        },
    )

    memories_a = search_relevant_memories(
        store=store,
        namespace=namespace_a,
        query="accidente",
        limit=3,
    )

    memories_b = search_relevant_memories(
        store=store,
        namespace=namespace_b,
        query="accidente",
        limit=3,
    )

    assert len(memories_a) == 1
    assert memories_a[0]["user"] == (
        "Tuve un accidente con un trabajador."
    )

    # El chat B jamás debe recuperar memorias del chat A.
    assert all(
        memory["user"]
        != "Tuve un accidente con un trabajador."
        for memory in memories_b
    )

def test_builds_context_with_profile_and_retrieved_memories() -> None:
    context = {
        "profile": {
            "economic_activity": "Panadería",
            "worker_count": 8,
        },
        "retrieved_memories": [
            {
                "memory_id": "turn-1",
                "user": "Tuve un accidente con un trabajador.",
                "assistant": "Se explicó cómo investigar el accidente.",
                "score": 0.95,
            },
            {
                "memory_id": "turn-4",
                "user": "El accidente ocurrió ayer.",
                "assistant": "Se explicó el procedimiento aplicable.",
                "score": 0.88,
            },
        ],
    }

    result = build_retrieval_memory_context(
        context
    )

    current_context = result["current_context"]

    assert "PERFIL EMPRESARIAL" in current_context
    assert "Actividad económica: Panadería" in current_context
    assert "Número de trabajadores: 8" in current_context

    assert "MEMORIA CONVERSACIONAL RECUPERADA" in current_context

    assert "Tuve un accidente con un trabajador." in current_context
    assert "Se explicó cómo investigar el accidente." in current_context

    assert "El accidente ocurrió ayer." in current_context


def test_builds_context_without_memories() -> None:
    context = {
        "profile": {
            "worker_count": 5,
        },
        "retrieved_memories": [],
    }

    result = build_retrieval_memory_context(
        context
    )

    current_context = result["current_context"]

    assert "PERFIL EMPRESARIAL" in current_context
    assert "Número de trabajadores: 5" in current_context

    assert "MEMORIA CONVERSACIONAL RECUPERADA" not in current_context


def test_builds_context_without_profile() -> None:
    context = {
        "retrieved_memories": [
            {
                "memory_id": "turn-2",
                "user": "¿Qué pasa con ese accidente?",
                "assistant": "Se explicó el procedimiento.",
                "score": 0.91,
            },
        ],
    }

    result = build_retrieval_memory_context(
        context
    )

    current_context = result["current_context"]

    assert "PERFIL EMPRESARIAL" not in current_context

    assert "MEMORIA CONVERSACIONAL RECUPERADA" in current_context

    assert "¿Qué pasa con ese accidente?" in current_context


def test_builds_empty_context_when_no_data_exists() -> None:
    result = build_retrieval_memory_context(
        {}
    )

    assert result["current_context"] == ""


def test_build_retrieval_context_does_not_mutate_original() -> None:
    context = {
        "profile": {
            "worker_count": 5,
        },
        "retrieved_memories": [],
    }

    result = build_retrieval_memory_context(
        context
    )

    assert "current_context" not in context
    assert "current_context" in result


def test_retrieval_memory_node_uses_thread_memory() -> None:
    store = build_test_store()

    namespace = build_memory_namespace(
        "thread-a"
    )

    store_conversation_memory(
        store,
        namespace,
        "turn-1",
        {
            "user": "Tuve un accidente con un trabajador.",
            "assistant": "Se explicó cómo investigar el accidente.",
        },
    )

    workflow = StateGraph(RagGraphState)

    workflow.add_node(
        "retrieval_memory",
        retrieval_long_term_memory_node(limit=1),
    )

    workflow.set_entry_point(
        "retrieval_memory"
    )

    workflow.add_edge(
        "retrieval_memory",
        END,
    )

    graph = workflow.compile(
        checkpointer=InMemorySaver(),
        store=store,
    )

    result = graph.invoke(
        {
            "question": "¿Qué hablamos del accidente?",
            "business_context": {
                "profile": {
                    "worker_count": 8,
                },
            },
        },
        {
            "configurable": {
                "thread_id": "thread-a",
            }
        },
    )

    business_context = result["business_context"]

    memories = business_context[
        "retrieved_memories"
    ]

    assert len(memories) == 1

    assert memories[0]["memory_id"] == (
        "turn-1"
    )

    current_context = business_context[
        "current_context"
    ]

    assert "Número de trabajadores: 8" in current_context

    assert (
        "Tuve un accidente con un trabajador."
        in current_context
    )


def test_store_memory_node_saves_latest_turn() -> None:
    store = build_test_store()

    workflow = StateGraph(RagGraphState)

    workflow.add_node(
        "store_memory",
        store_latest_conversation_memory_node,
    )

    workflow.set_entry_point(
        "store_memory"
    )

    workflow.add_edge(
        "store_memory",
        END,
    )

    graph = workflow.compile(
        checkpointer=InMemorySaver(),
        store=store,
    )

    graph.invoke(
        {
            "question": "Pregunta actual",
            "business_context": {
                "history": [
                    {
                        "user": "Tuve un accidente laboral.",
                        "assistant": "Se explicó qué procedimiento seguir.",
                    }
                ],
            },
        },
        {
            "configurable": {
                "thread_id": "thread-a",
            }
        },
    )

    namespace = build_memory_namespace(
        "thread-a"
    )

    item = store.get(
        namespace,
        "turn-1",
    )

    assert item is not None

    assert item.value["user"] == (
        "Tuve un accidente laboral."
    )

    assert item.value["assistant"] == (
        "Se explicó qué procedimiento seguir."
    )