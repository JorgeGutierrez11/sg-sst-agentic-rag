from agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory import (
    get_recent_turns,
    get_turns_pending_summarization,
)
from typing import Any

def make_turn(number: int) -> dict[str, str]:
    return {
        "user": f"Pregunta {number}",
        "assistant": f"Respuesta {number}",
    }


def test_keeps_two_turns_without_summarizing() -> None:
    context = {
        "history": [
            make_turn(1),
            make_turn(2),
        ]
    }

    assert get_turns_pending_summarization(context) == []

    assert get_recent_turns(context) == [
        make_turn(1),
        make_turn(2),
    ]


def test_summarizes_first_turn_when_third_turn_exists() -> None:
    context = {
        "history": [
            make_turn(1),
            make_turn(2),
            make_turn(3),
        ]
    }

    assert get_turns_pending_summarization(context) == [
        make_turn(1),
    ]

    assert get_recent_turns(context) == [
        make_turn(2),
        make_turn(3),
    ]


def test_summarizes_first_three_of_five_turns() -> None:
    context = {
        "history": [
            make_turn(1),
            make_turn(2),
            make_turn(3),
            make_turn(4),
            make_turn(5),
        ]
    }

    assert get_turns_pending_summarization(context) == [
        make_turn(1),
        make_turn(2),
        make_turn(3),
    ]

    assert get_recent_turns(context) == [
        make_turn(4),
        make_turn(5),
    ]


def test_only_returns_new_turns_for_incremental_summary() -> None:
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
        "summarized_turns": 3,
    }

    assert get_turns_pending_summarization(context) == [
        make_turn(4),
        make_turn(5),
    ]

    assert get_recent_turns(context) == [
        make_turn(6),
        make_turn(7),
    ]


from agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory import (
    build_summarization_context,
)


def make_turn(number: int) -> dict[str, str]:
    return {
        "user": f"Pregunta {number}",
        "assistant": f"Respuesta {number}",
    }


def test_builds_context_with_summary_and_recent_turns() -> None:
    context = {
        "profile": {
            "economic_activity": "Panadería",
            "worker_count": 5,
        },
        "history": [
            make_turn(1),
            make_turn(2),
            make_turn(3),
            make_turn(4),
            make_turn(5),
        ],
        "history_summary": (
            "La empresa informó anteriormente datos relevantes "
            "durante los primeros tres turnos."
        ),
        "summarized_turns": 3,
    }

    result = build_summarization_context(context)

    current_context = result["current_context"]

    assert "PERFIL EMPRESARIAL" in current_context
    assert "Actividad económica: Panadería" in current_context
    assert "Número de trabajadores: 5" in current_context

    assert "RESUMEN DE CONVERSACIONES ANTERIORES" in current_context
    assert "primeros tres turnos" in current_context

    assert "CONVERSACIÓN RECIENTE" in current_context

    # Los turnos no resumidos deben estar completos.
    assert "Pregunta 4" in current_context
    assert "Respuesta 4" in current_context

    assert "Pregunta 5" in current_context
    assert "Respuesta 5" in current_context

    # Los turnos resumidos no deben aparecer literalmente.
    assert "Pregunta 1" not in current_context
    assert "Pregunta 2" not in current_context
    assert "Pregunta 3" not in current_context


def test_builds_context_without_summary_when_history_is_short() -> None:
    context = {
        "profile": {
            "worker_count": 8,
        },
        "history": [
            make_turn(1),
            make_turn(2),
        ],
    }

    result = build_summarization_context(context)

    current_context = result["current_context"]

    assert "PERFIL EMPRESARIAL" in current_context
    assert "Número de trabajadores: 8" in current_context

    assert "RESUMEN DE CONVERSACIONES ANTERIORES" not in current_context

    assert "CONVERSACIÓN RECIENTE" in current_context

    assert "Pregunta 1" in current_context
    assert "Respuesta 1" in current_context

    assert "Pregunta 2" in current_context
    assert "Respuesta 2" in current_context


def test_builds_context_without_profile() -> None:
    context = {
        "history": [
            make_turn(1),
            make_turn(2),
            make_turn(3),
        ],
        "history_summary": "Resumen del primer turno.",
        "summarized_turns": 1,
    }

    result = build_summarization_context(context)

    current_context = result["current_context"]

    assert "PERFIL EMPRESARIAL" not in current_context

    assert "RESUMEN DE CONVERSACIONES ANTERIORES" in current_context
    assert "Resumen del primer turno." in current_context

    assert "Pregunta 2" in current_context
    assert "Pregunta 3" in current_context


def test_keeps_unsummarized_turns_after_previous_summary_failure() -> None:
    context = {
        "history": [
            make_turn(1),
            make_turn(2),
            make_turn(3),
            make_turn(4),
            make_turn(5),
        ],
        "history_summary": "Solo el turno 1 fue resumido.",
        "summarized_turns": 1,
    }

    result = build_summarization_context(context)

    current_context = result["current_context"]

    assert "Solo el turno 1 fue resumido." in current_context

    # Como summarized_turns sigue siendo 1,
    # todos los turnos 2-5 deben conservarse literalmente.
    assert "Pregunta 2" in current_context
    assert "Respuesta 2" in current_context

    assert "Pregunta 3" in current_context
    assert "Respuesta 3" in current_context

    assert "Pregunta 4" in current_context
    assert "Respuesta 4" in current_context

    assert "Pregunta 5" in current_context
    assert "Respuesta 5" in current_context

    # El turno 1 ya está representado por el resumen.
    assert "Pregunta 1" not in current_context


def test_builds_empty_context_when_no_data_exists() -> None:
    context = {}

    result = build_summarization_context(context)

    assert result["current_context"] == ""


def test_does_not_mutate_original_context() -> None:
    context = {
        "profile": {
            "worker_count": 5,
        },
        "history": [
            make_turn(1),
        ],
    }

    result = build_summarization_context(context)

    assert "current_context" not in context
    assert "current_context" in result

    assert result["profile"] == context["profile"]
    assert result["history"] == context["history"]


def test_summarization_memory_node_updates_summary_and_context(
    monkeypatch,
) -> None:
    from agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory import (
        summarization_memory_node,
    )

    state = {
        "question": "Pregunta actual",
        "business_context": {
            "profile": {
                "worker_count": 5,
            },
            "history": [
                make_turn(1),
                make_turn(2),
                make_turn(3),
            ],
        },
    }

    def fake_invoke_llm_text(
        llm: Any,
        messages: list[Any],
    ) -> str:
        return "Resumen del turno 1."

    monkeypatch.setattr(
        "agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory.invoke_llm_text",
        fake_invoke_llm_text,
    )

    node = summarization_memory_node(
        llm=object(),
    )

    result = node(state)

    business_context = result["business_context"]

    assert business_context["history_summary"] == (
        "Resumen del turno 1."
    )

    assert business_context["summarized_turns"] == 1

    current_context = business_context["current_context"]

    assert "Número de trabajadores: 5" in current_context
    assert "Resumen del turno 1." in current_context

    # Turnos 2 y 3 deben quedar completos.
    assert "Pregunta 2" in current_context
    assert "Pregunta 3" in current_context

    # El turno 1 ya está representado por el resumen.
    assert "Pregunta 1" not in current_context