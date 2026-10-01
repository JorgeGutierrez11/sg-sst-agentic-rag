
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import (
    load_catalog,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_validation import (
    AnswerReferenceError,
    validate_answer_reference,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "valid_catalog.json"
)


def test_accepts_answer_for_existing_question() -> None:
    requirement = load_catalog(FIXTURE_PATH).requirements[0]

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id=requirement.questions[0].id,
        raw_answer="Creo que sí, pero no estoy seguro.",
    )

    validate_answer_reference(answer, requirement)

    assert answer.raw_answer == (
        "Creo que sí, pero no estoy seguro."
    )


def test_rejects_answer_for_another_requirement() -> None:
    requirement = load_catalog(FIXTURE_PATH).requirements[0]

    answer = QuestionAnswer(
        requirement_id="another_requirement",
        question_id=requirement.questions[0].id,
        raw_answer=True,
    )

    with pytest.raises(AnswerReferenceError):
        validate_answer_reference(answer, requirement)


def test_rejects_unknown_question() -> None:
    requirement = load_catalog(FIXTURE_PATH).requirements[0]

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id="question_that_does_not_exist",
        raw_answer=True,
    )

    with pytest.raises(AnswerReferenceError):
        validate_answer_reference(answer, requirement)
