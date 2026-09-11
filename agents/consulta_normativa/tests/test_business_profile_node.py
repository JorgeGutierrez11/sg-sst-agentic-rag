from typing import Any

from agents.consulta_normativa.langchain_rag.business_context.profile_node import (
    business_profile_node,
)


def test_creates_profile_when_business_context_is_empty(monkeypatch) -> None:
    def fake_extract_business_profile(
        llm: Any,
        question: str,
    ) -> dict[str, Any]:
        return {
            "updates": {
                "worker_count": 8,
            },
            "evidence": {
                "worker_count": "8 trabajadores",
            },
        }

    monkeypatch.setattr(
        "agents.consulta_normativa.langchain_rag.business_context.profile_node.extract_business_profile",
        fake_extract_business_profile,
    )

    node = business_profile_node(llm=object())

    result = node(
        {
            "question": "Tenemos 8 trabajadores.",
        }
    )

    assert result["business_context"]["profile"] == {
        "worker_count": 8,
    }


def test_updates_existing_profile_without_losing_other_fields(monkeypatch) -> None:
    def fake_extract_business_profile(
        llm: Any,
        question: str,
    ) -> dict[str, Any]:
        return {
            "updates": {
                "worker_count": 10,
            },
            "evidence": {
                "worker_count": "10 trabajadores",
            },
        }

    monkeypatch.setattr(
        "agents.consulta_normativa.langchain_rag.business_context.profile_node.extract_business_profile",
        fake_extract_business_profile,
    )

    node = business_profile_node(llm=object())

    result = node(
        {
            "question": "Ahora tenemos 10 trabajadores.",
            "business_context": {
                "profile": {
                    "worker_count": 8,
                    "risk_class": "I",
                }
            },
        }
    )

    assert result["business_context"]["profile"] == {
        "worker_count": 10,
        "risk_class": "I",
    }


def test_keeps_profile_unchanged_when_nothing_is_extracted(monkeypatch) -> None:
    def fake_extract_business_profile(
        llm: Any,
        question: str,
    ) -> dict[str, Any]:
        return {
            "updates": {},
            "evidence": {},
        }

    monkeypatch.setattr(
        "agents.consulta_normativa.langchain_rag.business_context.profile_node.extract_business_profile",
        fake_extract_business_profile,
    )

    node = business_profile_node(llm=object())

    result = node(
        {
            "question": "¿Qué estándares mínimos debo cumplir?",
            "business_context": {
                "profile": {
                    "worker_count": 8,
                    "risk_class": "I",
                }
            },
        }
    )

    assert result["business_context"]["profile"] == {
        "worker_count": 8,
        "risk_class": "I",
    }


def test_preserves_existing_business_context_fields(monkeypatch) -> None:
    def fake_extract_business_profile(
        llm: Any,
        question: str,
    ) -> dict[str, Any]:
        return {
            "updates": {
                "risk_class": "II",
            },
            "evidence": {
                "risk_class": "riesgo II",
            },
        }

    monkeypatch.setattr(
        "agents.consulta_normativa.langchain_rag.business_context.profile_node.extract_business_profile",
        fake_extract_business_profile,
    )

    node = business_profile_node(llm=object())

    result = node(
        {
            "question": "Somos riesgo II.",
            "business_context": {
                "profile": {
                    "worker_count": 8,
                    "risk_class": "I",
                },
                "history": [
                    {
                        "user": "Tenemos 8 trabajadores.",
                        "assistant": "Entendido.",
                    }
                ],
                "current_context": "Contexto previo",
            },
        }
    )

    assert result["business_context"]["profile"]["risk_class"] == "II"

    assert result["business_context"]["history"] == [
        {
            "user": "Tenemos 8 trabajadores.",
            "assistant": "Entendido.",
        }
    ]

    assert result["business_context"]["current_context"] == "Contexto previo"