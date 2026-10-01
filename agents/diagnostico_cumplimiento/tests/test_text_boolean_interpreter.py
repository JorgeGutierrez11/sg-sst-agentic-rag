
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.interpretation import (
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.text_boolean_interpreter import (
    interpret_text_boolean_answer,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)


def get_pilot_question():
    requirement = load_catalog(PILOT_PATH).requirements[0]
    return requirement, requirement.questions[0]


@pytest.mark.parametrize(
    ("raw_text", "expected_status", "expected_value"),
    [
        ("Sí", InterpretationStatus.AFFIRMATIVE, True),
        ("si.", InterpretationStatus.AFFIRMATIVE, True),
        (" No ", InterpretationStatus.NEGATIVE, False),
        ("No sé", InterpretationStatus.INSUFFICIENT_INFORMATION, None),
        ("no se.", InterpretationStatus.INSUFFICIENT_INFORMATION, None),
        (
            "Creo que sí, pero no estoy seguro",
            InterpretationStatus.NEEDS_CLARIFICATION,
            None,
        ),
        (
            "Sí, pero algunos trabajadores no están afiliados",
            InterpretationStatus.NEEDS_CLARIFICATION,
            None,
        ),
        ("", InterpretationStatus.NEEDS_CLARIFICATION, None),
    ],
)
def test_interprets_text_answers(
    raw_text: str,
    expected_status: InterpretationStatus,
    expected_value: bool | None,
) -> None:
    requirement, question = get_pilot_question()

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question.id,
        raw_answer=raw_text,
    )

    result = interpret_text_boolean_answer(question, answer)

    assert result.requirement_id == requirement.id
    assert result.question_id == question.id
    assert result.status == expected_status
    assert result.interpreted_value is expected_value

    # La interpretación no modifica el texto escrito por el usuario.
    assert answer.raw_answer == raw_text


def test_rejects_structured_boolean_answer() -> None:
    requirement, question = get_pilot_question()

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question.id,
        raw_answer=True,
    )

    with pytest.raises(ValueError):
        interpret_text_boolean_answer(question, answer)


def test_rejects_answer_for_another_question() -> None:
    requirement, question = get_pilot_question()

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id="another_question",
        raw_answer="Sí",
    )

    with pytest.raises(ValueError):
        interpret_text_boolean_answer(question, answer)
