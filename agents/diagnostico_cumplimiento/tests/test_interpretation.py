
import pytest
from pydantic import ValidationError

from agents.diagnostico_cumplimiento.domain.interpretation import (
    AnswerInterpretation,
    InterpretationStatus,
)


REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"
QUESTION_ID = "q_occupational_risk_affiliation"


def build_interpretation(
    status: InterpretationStatus,
    interpreted_value: bool | None,
) -> AnswerInterpretation:
    return AnswerInterpretation(
        requirement_id=REQUIREMENT_ID,
        question_id=QUESTION_ID,
        status=status,
        interpreted_value=interpreted_value,
        explanation="Resultado de interpretación de prueba.",
    )


@pytest.mark.parametrize(
    ("status", "interpreted_value"),
    [
        (InterpretationStatus.AFFIRMATIVE, True),
        (InterpretationStatus.NEGATIVE, False),
        (InterpretationStatus.NEEDS_CLARIFICATION, None),
        (InterpretationStatus.INSUFFICIENT_INFORMATION, None),
        (InterpretationStatus.INVALID_FORMAT, None),
    ],
)
def test_accepts_consistent_interpretations(
    status: InterpretationStatus,
    interpreted_value: bool | None,
) -> None:
    result = build_interpretation(status, interpreted_value)

    assert result.status == status
    assert result.interpreted_value is interpreted_value


@pytest.mark.parametrize(
    ("status", "interpreted_value"),
    [
        (InterpretationStatus.AFFIRMATIVE, False),
        (InterpretationStatus.NEGATIVE, True),
        (InterpretationStatus.NEEDS_CLARIFICATION, True),
        (InterpretationStatus.INSUFFICIENT_INFORMATION, False),
        (InterpretationStatus.INVALID_FORMAT, True),
    ],
)
def test_rejects_contradictory_interpretations(
    status: InterpretationStatus,
    interpreted_value: bool | None,
) -> None:
    with pytest.raises(ValidationError):
        build_interpretation(status, interpreted_value)


def test_requires_explanation() -> None:
    with pytest.raises(ValidationError):
        AnswerInterpretation(
            requirement_id=REQUIREMENT_ID,
            question_id=QUESTION_ID,
            status=InterpretationStatus.AFFIRMATIVE,
            interpreted_value=True,
            explanation="",
        )


def test_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        AnswerInterpretation(
            requirement_id=REQUIREMENT_ID,
            question_id=QUESTION_ID,
            status=InterpretationStatus.AFFIRMATIVE,
            interpreted_value=True,
            explanation="El usuario respondió afirmativamente.",
            compliance_status="compliant",
        )
