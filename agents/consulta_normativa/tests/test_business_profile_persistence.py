"""Integration tests for persisted business profile state."""

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from agents.consulta_normativa.langchain_rag.graph import (
    answer_with_langgraph,
    build_langgraph_rag,
)


class FakeStructuredLLM:
    """Fake structured output used by the business-profile extractor."""

    def invoke(self, messages: list[Any]) -> dict[str, Any]:
        user_message = messages[-1].content

        if "8 trabajadores" in user_message:
            return {
                "facts": [
                    {
                        "field": "worker_count",
                        "value": "8",
                        "evidence": "8 trabajadores",
                    }
                ]
            }

        return {
            "facts": [],
        }


class FakeLLM:
    """Minimal LLM compatible with business-profile extraction."""

    def with_structured_output(self, schema: Any, **kwargs,) -> FakeStructuredLLM:
        return FakeStructuredLLM()


def fake_retriever(
    question: str,
    top_k: int,
) -> dict[str, Any]:
    """Return no normative evidence; retrieval is irrelevant for this test."""

    return {
        "documents": [[]],
        "metadatas": [[]],
    }


def test_business_profile_survives_between_turns() -> None:
    checkpointer = InMemorySaver()

    graph = build_langgraph_rag(
        llm=FakeLLM(),
        retriever=fake_retriever,
        top_k=1,
        checkpointer=checkpointer,
    )

    thread_id = "company-001"

    # First turn: user explicitly provides the number of workers.
    answer_with_langgraph(
        question="Tenemos 8 trabajadores.",
        graph=graph,
        thread_id=thread_id,
    )

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    first_snapshot = graph.get_state(config)

    assert (
        first_snapshot.values["business_context"]["profile"]["worker_count"]
        == 8
    )

    # Second turn: no new worker count is provided.
    answer_with_langgraph(
        question="¿Qué estándares mínimos debemos cumplir?",
        graph=graph,
        thread_id=thread_id,
    )

    second_snapshot = graph.get_state(config)

    assert (
        second_snapshot.values["business_context"]["profile"]["worker_count"]
        == 8
    )

def test_business_profiles_are_isolated_between_threads() -> None:
    checkpointer = InMemorySaver()

    graph = build_langgraph_rag(
        llm=FakeLLM(),
        retriever=fake_retriever,
        top_k=1,
        checkpointer=checkpointer,
    )

    answer_with_langgraph(
        question="Tenemos 8 trabajadores.",
        graph=graph,
        thread_id="company-001",
    )

    company_1_state = graph.get_state(
        {
            "configurable": {
                "thread_id": "company-001",
            }
        }
    )

    company_2_state = graph.get_state(
        {
            "configurable": {
                "thread_id": "company-002",
            }
        }
    )

    assert (
        company_1_state.values["business_context"]["profile"]["worker_count"]
        == 8
    )

    assert not company_2_state.values

def test_conversation_history_survives_between_turns() -> None:
    checkpointer = InMemorySaver()

    graph = build_langgraph_rag(
        llm=FakeLLM(),
        retriever=fake_retriever,
        top_k=1,
        checkpointer=checkpointer,
    )

    thread_id = "company-history-001"

    answer_with_langgraph(
        question="Tenemos 8 trabajadores.",
        graph=graph,
        thread_id=thread_id,
    )

    answer_with_langgraph(
        question="¿Qué estándares mínimos debemos cumplir?",
        graph=graph,
        thread_id=thread_id,
    )

    snapshot = graph.get_state(
        {
            "configurable": {
                "thread_id": thread_id,
            }
        }
    )

    history = snapshot.values["business_context"]["history"]

    assert len(history) == 2

    assert history[0]["user"] == "Tenemos 8 trabajadores."
    assert history[1]["user"] == "¿Qué estándares mínimos debemos cumplir?"

    assert history[0]["assistant"]
    assert history[1]["assistant"]

def test_full_conversation_context_contains_previous_turn() -> None:
    checkpointer = InMemorySaver()

    graph = build_langgraph_rag(
        llm=FakeLLM(),
        retriever=fake_retriever,
        top_k=1,
        checkpointer=checkpointer,
    )

    thread_id = "company-context-001"

    # Primer turno
    answer_with_langgraph(
        question="Tenemos 8 trabajadores.",
        graph=graph,
        thread_id=thread_id,
    )

    # Segundo turno: al comenzar esta ejecución,
    # Full Conversation Memory debe recuperar el turno anterior.
    answer_with_langgraph(
        question="¿Qué estándares mínimos debemos cumplir?",
        graph=graph,
        thread_id=thread_id,
    )

    snapshot = graph.get_state(
        {
            "configurable": {
                "thread_id": thread_id,
            }
        }
    )

    business_context = snapshot.values["business_context"]
    current_context = business_context["current_context"]

    # El perfil actualizado debe estar disponible.
    assert "Número de trabajadores: 8" in current_context

    # El primer turno debe formar parte del contexto construido.
    assert "HISTORIAL DE CONVERSACIÓN" in current_context
    assert "Usuario: Tenemos 8 trabajadores." in current_context

    # Después de finalizar el segundo turno, el historial persistente
    # debe contener ambos turnos.
    assert len(business_context["history"]) == 2

    assert (
        business_context["history"][0]["user"]
        == "Tenemos 8 trabajadores."
    )

    assert (
        business_context["history"][1]["user"]
        == "¿Qué estándares mínimos debemos cumplir?"
    )