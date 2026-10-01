
import pytest
from pydantic import ValidationError

from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer


REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"
QUESTION_ID = "q_occupational_risk_affiliation"


@pytest.mark.parametrize(
    "raw_answer",
    [
        True,
        False,
        8,
        "Sí, todos están afiliados.",
        ["Salud", "Pensión", "Riesgos laborales"],
    ],
)
def test_accepts_supported_answer_types(raw_answer) -> None:
    answer = QuestionAnswer(
        requirement_id=REQUIREMENT_ID,
        question_id=QUESTION_ID,
        raw_answer=raw_answer,
    )

    assert answer.raw_answer == raw_answer
    assert type(answer.raw_answer) is type(raw_answer)


def test_preserves_uncertain_answer() -> None:
    original_text = (
        "Creo que sí, pero no estoy seguro "
        "de que todos estén afiliados."
    )

    answer = QuestionAnswer(
        requirement_id=REQUIREMENT_ID,
        question_id=QUESTION_ID,
        raw_answer=original_text,
    )

    assert answer.raw_answer == original_text
    assert answer.model_dump()["raw_answer"] == original_text


def test_requires_original_answer() -> None:
    with pytest.raises(ValidationError):
        QuestionAnswer(
            requirement_id=REQUIREMENT_ID,
            question_id=QUESTION_ID,
        )


def test_rejects_empty_identifiers() -> None:
    with pytest.raises(ValidationError):
        QuestionAnswer(
            requirement_id="",
            question_id=QUESTION_ID,
            raw_answer=True,
        )


def test_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        QuestionAnswer(
            requirement_id=REQUIREMENT_ID,
            question_id=QUESTION_ID,
            raw_answer=True,
            compliance_status="compliant",
        )


def test_rejects_unsupported_answer_type() -> None:
    with pytest.raises(ValidationError):
        QuestionAnswer(
            requirement_id=REQUIREMENT_ID,
            question_id=QUESTION_ID,
            raw_answer={"affiliated": True},
        )
