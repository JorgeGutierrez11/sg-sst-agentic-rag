"""Integration tests for CLI conversation memory."""

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from agents.consulta_normativa.langchain_rag.graph import build_langgraph_rag
from agents.consulta_normativa.langchain_rag.main import (
    RagRuntime,
    run_once,
)
from agents.consulta_normativa.langchain_rag.graph import (
    answer_with_langgraph,
    build_langgraph_rag,
)


class FakeStructuredLLM:
    """Fake structured output for business-profile extraction."""

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
    """Minimal LLM required by the graph for this test."""

    def with_structured_output(self, schema: Any) -> FakeStructuredLLM:
        return FakeStructuredLLM()


def fake_retriever(
    question: str,
    top_k: int,
) -> dict[str, Any]:
    """Return no evidence so the graph uses deterministic fallback."""

    return {
        "documents": [[]],
        "metadatas": [[]],
    }


def test_cli_runtime_preserves_profile_and_history() -> None:
    checkpointer = InMemorySaver()

    graph = build_langgraph_rag(
        llm=FakeLLM(),
        retriever=fake_retriever,
        top_k=1,
        checkpointer=checkpointer,
    )

    runtime = RagRuntime(
    answer_with_langgraph=answer_with_langgraph,
    graph=graph,
    thread_id="cli-test-session",
)

    # Turno 1
    result_1 = run_once(
        runtime,
        "Tenemos 8 trabajadores.",
    )

    assert result_1 == 0

    # Turno 2
    result_2 = run_once(
        runtime,
        "¿Qué estándares mínimos debemos cumplir?",
    )

    assert result_2 == 0

    snapshot = graph.get_state(
        {
            "configurable": {
                "thread_id": runtime.thread_id,
            }
        }
    )

    business_context = snapshot.values["business_context"]

    # El perfil debe sobrevivir.
    assert business_context["profile"]["worker_count"] == 8

    # La CLI debe haber acumulado ambos turnos.
    assert len(business_context["history"]) == 2

    assert (
        business_context["history"][0]["user"]
        == "Tenemos 8 trabajadores."
    )

    assert (
        business_context["history"][1]["user"]
        == "¿Qué estándares mínimos debemos cumplir?"
    )

    # Full Conversation Memory del segundo turno debe haber visto
    # información persistida del primero.
    current_context = business_context["current_context"]

    assert "Número de trabajadores: 8" in current_context
    assert "Usuario: Tenemos 8 trabajadores." in current_context