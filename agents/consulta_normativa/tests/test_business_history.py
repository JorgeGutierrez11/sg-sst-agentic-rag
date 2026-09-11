from agents.consulta_normativa.langchain_rag.business_context.history import (
    append_conversation_turn,
)


def test_adds_first_conversation_turn() -> None:
    business_context = {
        "profile": {
            "worker_count": 8,
        }
    }

    result = append_conversation_turn(
        business_context=business_context,
        user_message="Tengo 8 trabajadores.",
        assistant_message="Respuesta 1",
    )

    assert result["history"] == [
        {
            "user": "Tengo 8 trabajadores.",
            "assistant": "Respuesta 1",
        }
    ]

    assert result["profile"]["worker_count"] == 8


def test_accumulates_multiple_conversation_turns() -> None:
    business_context = {}

    first_result = append_conversation_turn(
        business_context=business_context,
        user_message="Tengo 8 trabajadores.",
        assistant_message="Respuesta 1",
    )

    second_result = append_conversation_turn(
        business_context=first_result,
        user_message="Somos riesgo I.",
        assistant_message="Respuesta 2",
    )

    assert second_result["history"] == [
        {
            "user": "Tengo 8 trabajadores.",
            "assistant": "Respuesta 1",
        },
        {
            "user": "Somos riesgo I.",
            "assistant": "Respuesta 2",
        },
    ]


def test_does_not_mutate_original_business_context() -> None:
    business_context = {
        "history": [
            {
                "user": "Mensaje anterior",
                "assistant": "Respuesta anterior",
            }
        ]
    }

    result = append_conversation_turn(
        business_context=business_context,
        user_message="Nuevo mensaje",
        assistant_message="Nueva respuesta",
    )

    assert len(business_context["history"]) == 1
    assert len(result["history"]) == 2