from agents.consulta_normativa.langchain_rag.business_context.techniques.full_conversation_memory import (
    build_full_conversation_context,
)


def test_builds_context_with_profile_and_history() -> None:
    business_context = {
        "profile": {
            "economic_activity": "Mantenimiento de motocicletas",
            "worker_count": 8,
            "risk_class": "I",
        },
        "history": [
            {
                "user": "Tenemos 8 trabajadores.",
                "assistant": "Respuesta 1",
            },
            {
                "user": "Un trabajador se fracturó el brazo.",
                "assistant": "Respuesta 2",
            },
        ],
    }

    result = build_full_conversation_context(business_context)

    current_context = result["current_context"]

    assert "PERFIL EMPRESARIAL" in current_context
    assert "Actividad económica: Mantenimiento de motocicletas" in current_context
    assert "Número de trabajadores: 8" in current_context
    assert "Clase de riesgo: I" in current_context

    assert "HISTORIAL DE CONVERSACIÓN" in current_context
    assert "Turno 1" in current_context
    assert "Usuario: Tenemos 8 trabajadores." in current_context
    assert "Agente: Respuesta 1" in current_context
    assert "Turno 2" in current_context
    assert "Usuario: Un trabajador se fracturó el brazo." in current_context
    assert "Agente: Respuesta 2" in current_context


def test_builds_context_with_only_history() -> None:
    business_context = {
        "history": [
            {
                "user": "¿Qué debo hacer con el accidente?",
                "assistant": "Respuesta del agente",
            }
        ]
    }

    result = build_full_conversation_context(business_context)

    current_context = result["current_context"]

    assert "PERFIL EMPRESARIAL" not in current_context
    assert "HISTORIAL DE CONVERSACIÓN" in current_context
    assert "Usuario: ¿Qué debo hacer con el accidente?" in current_context
    assert "Agente: Respuesta del agente" in current_context


def test_builds_empty_current_context_when_no_data_exists() -> None:
    business_context = {}

    result = build_full_conversation_context(business_context)

    assert result["current_context"] == ""


def test_does_not_mutate_original_business_context() -> None:
    business_context = {
        "profile": {
            "worker_count": 8,
        },
        "history": [
            {
                "user": "Mensaje",
                "assistant": "Respuesta",
            }
        ],
    }

    result = build_full_conversation_context(business_context)

    assert "current_context" not in business_context
    assert "current_context" in result

    assert result["profile"] == business_context["profile"]
    assert result["history"] == business_context["history"]

from agents.consulta_normativa.langchain_rag.business_context.techniques.full_conversation_memory import (
    build_full_conversation_context,
    full_conversation_memory_node,
)


def test_full_conversation_memory_node_builds_current_context() -> None:
    state = {
        "question": "¿Qué debo hacer ahora?",
        "business_context": {
            "profile": {
                "worker_count": 8,
                "risk_class": "I",
            },
            "history": [
                {
                    "user": "Un trabajador se fracturó el brazo.",
                    "assistant": "Respuesta anterior.",
                }
            ],
        },
    }

    result = full_conversation_memory_node(state)

    current_context = result["business_context"]["current_context"]

    assert "Número de trabajadores: 8" in current_context
    assert "Clase de riesgo: I" in current_context
    assert "Un trabajador se fracturó el brazo." in current_context
    assert "Respuesta anterior." in current_context