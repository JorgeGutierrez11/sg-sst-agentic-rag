
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.interpretation import (
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_interpreter import (
    interpret_boolean_answer,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_validation import (
    AnswerReferenceError,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)


def get_pilot_requirement():
    return load_catalog(PILOT_PATH).requirements[0]


@pytest.mark.parametrize(
    ("raw_answer", "expected_status", "expected_value"),
    [
        (True, InterpretationStatus.AFFIRMATIVE, True),
        (False, InterpretationStatus.NEGATIVE, False),
        ("Sí", InterpretationStatus.AFFIRMATIVE, True),
        ("No", InterpretationStatus.NEGATIVE, False),
        (
            "No sé",
            InterpretationStatus.INSUFFICIENT_INFORMATION,
            None,
        ),
        (
            "Creo que sí, pero no estoy seguro.",
            InterpretationStatus.NEEDS_CLARIFICATION,
            None,
        ),
        (8, InterpretationStatus.INVALID_FORMAT, None),
        (["Sí"], InterpretationStatus.INVALID_FORMAT, None),
    ],
)
def test_interprets_answer_according_to_its_format(
    raw_answer,
    expected_status: InterpretationStatus,
    expected_value: bool | None,
) -> None:
    requirement = get_pilot_requirement()
    question = requirement.questions[0]

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question.id,
        raw_answer=raw_answer,
    )

    result = interpret_boolean_answer(requirement, answer)

    assert result.requirement_id == requirement.id
    assert result.question_id == question.id
    assert result.status == expected_status
    assert result.interpreted_value is expected_value

    # La interpretación no altera el dato original.
    assert type(answer.raw_answer) is type(raw_answer)
    assert answer.raw_answer == raw_answer


def test_rejects_answer_for_another_requirement() -> None:
    requirement = get_pilot_requirement()

    answer = QuestionAnswer(
        requirement_id="another_requirement",
        question_id=requirement.questions[0].id,
        raw_answer=True,
    )

    with pytest.raises(AnswerReferenceError):
        interpret_boolean_answer(requirement, answer)


def test_rejects_unknown_question() -> None:
    requirement = get_pilot_requirement()

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id="unknown_question",
        raw_answer="Sí",
    )

    with pytest.raises(AnswerReferenceError):
        interpret_boolean_answer(requirement, answer)
