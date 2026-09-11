from agents.consulta_normativa.langchain_rag.business_context.history_node import (
    save_conversation_turn_node,
)


def test_saves_current_conversation_turn() -> None:
    state = {
        "question": "Tengo 8 trabajadores.",
        "answer": "Respuesta del agente.",
        "business_context": {
            "profile": {
                "worker_count": 8,
            }
        },
    }

    result = save_conversation_turn_node(state)

    assert result["business_context"]["profile"]["worker_count"] == 8

    assert result["business_context"]["history"] == [
        {
            "user": "Tengo 8 trabajadores.",
            "assistant": "Respuesta del agente.",
        }
    ]


def test_appends_to_existing_history() -> None:
    state = {
        "question": "Somos riesgo I.",
        "answer": "Respuesta 2",
        "business_context": {
            "history": [
                {
                    "user": "Tengo 8 trabajadores.",
                    "assistant": "Respuesta 1",
                }
            ]
        },
    }

    result = save_conversation_turn_node(state)

    assert result["business_context"]["history"] == [
        {
            "user": "Tengo 8 trabajadores.",
            "assistant": "Respuesta 1",
        },
        {
            "user": "Somos riesgo I.",
            "assistant": "Respuesta 2",
        },
    ]