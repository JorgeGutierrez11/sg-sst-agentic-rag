from typing import Any

from agents.consulta_normativa.langchain_rag.business_context.profile_extractor import (
    BusinessProfileExtractionSchema,
    extract_business_profile,
)


class FakeStructuredLLM:
    """Fake structured LLM response for deterministic tests."""

    def __init__(self, response: Any = None, error: Exception | None = None):
        self.response = response
        self.error = error

    def invoke(self, messages: list[Any]) -> Any:
        if self.error is not None:
            raise self.error

        return self.response


class FakeLLM:
    """Fake LLM supporting with_structured_output()."""

    def __init__(self, response: Any = None, error: Exception | None = None):
        self.response = response
        self.error = error

    def with_structured_output(self, schema: Any) -> FakeStructuredLLM:
        assert schema is BusinessProfileExtractionSchema

        return FakeStructuredLLM(
            response=self.response,
            error=self.error,
        )


def test_extracts_explicit_business_information() -> None:
    question = (
        "Somos una empresa de fabricación de calzado, "
        "tenemos 8 trabajadores y somos riesgo I."
    )

    llm = FakeLLM(
        response={
            "facts": [
                {
                    "field": "economic_activity",
                    "value": "fabricación de calzado",
                    "evidence": "empresa de fabricación de calzado",
                },
                {
                    "field": "worker_count",
                    "value": "8",
                    "evidence": "8 trabajadores",
                },
                {
                    "field": "risk_class",
                    "value": "I",
                    "evidence": "somos riesgo I",
                },
            ]
        }
    )

    result = extract_business_profile(llm, question)

    assert result["updates"] == {
        "economic_activity": "fabricación de calzado",
        "worker_count": 8,
        "risk_class": "I",
    }

    assert result["evidence"] == {
        "economic_activity": "empresa de fabricación de calzado",
        "worker_count": "8 trabajadores",
        "risk_class": "somos riesgo I",
    }


def test_extracts_ciiu_without_inferred_risk_class() -> None:
    question = "Mi CIIU es 1240, ¿qué riesgo soy?"

    llm = FakeLLM(
        response={
            "facts": [
                {
                    "field": "ciiu_code",
                    "value": "1240",
                    "evidence": "Mi CIIU es 1240",
                }
            ]
        }
    )

    result = extract_business_profile(llm, question)

    assert result == {
        "updates": {
            "ciiu_code": "1240",
        },
        "evidence": {
            "ciiu_code": "Mi CIIU es 1240",
        },
    }

    assert "risk_class" not in result["updates"]


def test_returns_empty_result_when_no_business_information_exists() -> None:
    question = "¿Qué estándares mínimos debo cumplir?"

    llm = FakeLLM(
        response={
            "facts": [],
        }
    )

    result = extract_business_profile(llm, question)

    assert result == {
        "updates": {},
        "evidence": {},
    }


def test_rejects_evidence_not_present_in_user_message() -> None:
    question = "Tengo una empresa de fabricación de calzado."

    llm = FakeLLM(
        response={
            "facts": [
                {
                    "field": "worker_count",
                    "value": "8",
                    "evidence": "Tengo 8 trabajadores",
                }
            ]
        }
    )

    result = extract_business_profile(llm, question)

    assert result == {
        "updates": {},
        "evidence": {},
    }


def test_rejects_invalid_worker_count() -> None:
    question = "Tenemos varios trabajadores."

    llm = FakeLLM(
        response={
            "facts": [
                {
                    "field": "worker_count",
                    "value": "varios",
                    "evidence": "varios trabajadores",
                }
            ]
        }
    )

    result = extract_business_profile(llm, question)

    assert "worker_count" not in result["updates"]


def test_rejects_negative_worker_count() -> None:
    question = "Tenemos -5 trabajadores."

    llm = FakeLLM(
        response={
            "facts": [
                {
                    "field": "worker_count",
                    "value": "-5",
                    "evidence": "-5 trabajadores",
                }
            ]
        }
    )

    result = extract_business_profile(llm, question)

    assert "worker_count" not in result["updates"]


def test_rejects_invalid_risk_class() -> None:
    question = "Somos riesgo bajo."

    llm = FakeLLM(
        response={
            "facts": [
                {
                    "field": "risk_class",
                    "value": "BAJO",
                    "evidence": "riesgo bajo",
                }
            ]
        }
    )

    result = extract_business_profile(llm, question)

    assert "risk_class" not in result["updates"]


def test_returns_empty_result_when_llm_fails() -> None:
    question = "Tenemos 8 trabajadores."

    llm = FakeLLM(
        error=RuntimeError("LLM unavailable"),
    )

    result = extract_business_profile(llm, question)

    assert result == {
        "updates": {},
        "evidence": {},
    }


def test_returns_empty_result_for_empty_question() -> None:
    llm = FakeLLM(
        response={
            "facts": [
                {
                    "field": "worker_count",
                    "value": "8",
                    "evidence": "8 trabajadores",
                }
            ]
        }
    )

    result = extract_business_profile(llm, "   ")

    assert result == {
        "updates": {},
        "evidence": {},
    }


def test_normalizes_risk_class_to_uppercase() -> None:
    question = "Nuestra empresa está clasificada como riesgo ii."

    llm = FakeLLM(
        response={
            "facts": [
                {
                    "field": "risk_class",
                    "value": "ii",
                    "evidence": "riesgo ii",
                }
            ]
        }
    )

    result = extract_business_profile(llm, question)

    assert result["updates"]["risk_class"] == "II"