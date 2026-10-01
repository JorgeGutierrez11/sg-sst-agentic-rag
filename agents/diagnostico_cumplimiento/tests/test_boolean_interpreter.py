
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.interpretation import (
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.boolean_interpreter import (
    interpret_structured_boolean_answer,
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
    ("raw_answer", "expected_status"),
    [
        (True, InterpretationStatus.AFFIRMATIVE),
        (False, InterpretationStatus.NEGATIVE),
    ],
)
def test_interprets_structured_boolean_answers(
    raw_answer: bool,
    expected_status: InterpretationStatus,
) -> None:
    requirement, question = get_pilot_question()

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question.id,
        raw_answer=raw_answer,
    )

    result = interpret_structured_boolean_answer(question, answer)

    assert result.requirement_id == requirement.id
    assert result.question_id == question.id
    assert result.status == expected_status
    assert result.interpreted_value is raw_answer

    # La interpretación no modifica la respuesta original.
    assert answer.raw_answer is raw_answer


@pytest.mark.parametrize(
    "raw_answer",
    [
        "Sí",
        "No",
        "No sé",
        "Creo que sí, pero no estoy seguro.",
        1,
        ["Sí"],
    ],
)
def test_rejects_answers_that_are_not_direct_booleans(
    raw_answer,
) -> None:
    requirement, question = get_pilot_question()

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question.id,
        raw_answer=raw_answer,
    )

    with pytest.raises(ValueError):
        interpret_structured_boolean_answer(question, answer)


def test_rejects_answer_for_another_question() -> None:
    requirement, question = get_pilot_question()

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id="another_question",
        raw_answer=True,
    )

    with pytest.raises(ValueError):
        interpret_structured_boolean_answer(question, answer)
