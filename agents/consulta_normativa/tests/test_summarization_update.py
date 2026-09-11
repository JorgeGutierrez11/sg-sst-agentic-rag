from typing import Any

from agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory import (
    update_conversation_summary,
)


def make_turn(number: int) -> dict[str, str]:
    return {
        "user": f"Pregunta {number}",
        "assistant": f"Respuesta {number}",
    }


def test_creates_initial_summary(monkeypatch) -> None:
    context = {
        "history": [
            make_turn(1),
            make_turn(2),
            make_turn(3),
            make_turn(4),
            make_turn(5),
        ]
    }

    def fake_invoke_llm_text(
        llm: Any,
        messages: list[Any],
    ) -> str:
        return "Resumen de los turnos 1, 2 y 3."

    monkeypatch.setattr(
        "agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory.invoke_llm_text",
        fake_invoke_llm_text,
    )

    result = update_conversation_summary(
        llm=object(),
        business_context=context,
    )

    assert result["history_summary"] == (
        "Resumen de los turnos 1, 2 y 3."
    )

    assert result["summarized_turns"] == 3


def test_updates_summary_incrementally(monkeypatch) -> None:
    context = {
        "history": [
            make_turn(1),
            make_turn(2),
            make_turn(3),
            make_turn(4),
            make_turn(5),
            make_turn(6),
            make_turn(7),
        ],
        "history_summary": "Resumen anterior de los turnos 1, 2 y 3.",
        "summarized_turns": 3,
    }

    captured_messages = []

    def fake_invoke_llm_text(
        llm: Any,
        messages: list[Any],
    ) -> str:
        captured_messages.extend(messages)

        return (
            "Resumen acumulado de los turnos "
            "1, 2, 3, 4 y 5."
        )

    monkeypatch.setattr(
        "agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory.invoke_llm_text",
        fake_invoke_llm_text,
    )

    result = update_conversation_summary(
        llm=object(),
        business_context=context,
    )

    assert result["history_summary"] == (
        "Resumen acumulado de los turnos "
        "1, 2, 3, 4 y 5."
    )

    assert result["summarized_turns"] == 5

    human_message = captured_messages[-1].content

    assert "Resumen anterior de los turnos 1, 2 y 3." in human_message

    assert "Pregunta 4" in human_message
    assert "Respuesta 4" in human_message

    assert "Pregunta 5" in human_message
    assert "Respuesta 5" in human_message

    # Los turnos ya resumidos no deben volver a enviarse.
    assert "Pregunta 1" not in human_message
    assert "Pregunta 2" not in human_message
    assert "Pregunta 3" not in human_message

    # Los dos turnos recientes tampoco se resumen.
    assert "Pregunta 6" not in human_message
    assert "Pregunta 7" not in human_message


def test_does_nothing_when_no_turns_need_summarization(
    monkeypatch,
) -> None:
    context = {
        "history": [
            make_turn(1),
            make_turn(2),
        ]
    }

    called = False

    def fake_invoke_llm_text(
        llm: Any,
        messages: list[Any],
    ) -> str:
        nonlocal called
        called = True

        return "No debería ejecutarse."

    monkeypatch.setattr(
        "agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory.invoke_llm_text",
        fake_invoke_llm_text,
    )

    result = update_conversation_summary(
        llm=object(),
        business_context=context,
    )

    assert called is False
    assert "history_summary" not in result
    assert "summarized_turns" not in result


def test_keeps_previous_summary_when_llm_fails(
    monkeypatch,
) -> None:
    context = {
        "history": [
            make_turn(1),
            make_turn(2),
            make_turn(3),
            make_turn(4),
            make_turn(5),
        ],
        "history_summary": "Resumen anterior.",
        "summarized_turns": 1,
    }

    def fake_invoke_llm_text(
        llm: Any,
        messages: list[Any],
    ) -> str:
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(
        "agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory.invoke_llm_text",
        fake_invoke_llm_text,
    )

    result = update_conversation_summary(
        llm=object(),
        business_context=context,
    )

    assert result["history_summary"] == "Resumen anterior."
    assert result["summarized_turns"] == 1


def test_does_not_mark_turns_as_summarized_when_llm_returns_empty(
    monkeypatch,
) -> None:
    context = {
        "history": [
            make_turn(1),
            make_turn(2),
            make_turn(3),
        ]
    }

    def fake_invoke_llm_text(
        llm: Any,
        messages: list[Any],
    ) -> str:
        return "   "

    monkeypatch.setattr(
        "agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory.invoke_llm_text",
        fake_invoke_llm_text,
    )

    result = update_conversation_summary(
        llm=object(),
        business_context=context,
    )

    assert "history_summary" not in result
    assert "summarized_turns" not in result