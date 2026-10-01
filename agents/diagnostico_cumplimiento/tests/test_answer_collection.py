
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import (
    load_catalog,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_collection import (
    DuplicateAnswerError,
    collect_requirement_answers,
    get_unanswered_questions,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_validation import (
    AnswerReferenceError,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "valid_catalog.json"
)


def test_collects_answer_without_changing_original_text() -> None:
    requirement = load_catalog(FIXTURE_PATH).requirements[0]
    question_id = requirement.questions[0].id

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer="No sé si todos están afiliados.",
    )

    collected = collect_requirement_answers(
        requirement,
        [answer],
    )

    assert collected[question_id].raw_answer == (
        "No sé si todos están afiliados."
    )


def test_allows_unanswered_questions() -> None:
    requirement = load_catalog(FIXTURE_PATH).requirements[0]

    collected = collect_requirement_answers(
        requirement,
        [],
    )

    assert collected == {}


def test_rejects_duplicate_answers() -> None:
    requirement = load_catalog(FIXTURE_PATH).requirements[0]
    question_id = requirement.questions[0].id

    first = QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=True,
    )

    second = QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=False,
    )

    with pytest.raises(DuplicateAnswerError):
        collect_requirement_answers(
            requirement,
            [first, second],
        )


def test_rejects_unknown_question() -> None:
    requirement = load_catalog(FIXTURE_PATH).requirements[0]

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id="unknown_question",
        raw_answer=True,
    )

    with pytest.raises(AnswerReferenceError):
        collect_requirement_answers(
            requirement,
            [answer],
        )


@pytest.mark.parametrize(
    ("answered_count", "expected_pending_count"),
    [
        (0, 3),
        (1, 2),
        (3, 0),
    ],
)
def test_identifies_unanswered_questions(
    answered_count: int,
    expected_pending_count: int,
) -> None:
    pilot_path = (
        Path(__file__).resolve().parents[1]
        / "catalog"
        / "data"
        / "res0312_piloto_v1.json"
    )

    requirement = load_catalog(pilot_path).requirements[0]

    answers = [
        QuestionAnswer(
            requirement_id=requirement.id,
            question_id=question.id,
            raw_answer="No sé",
        )
        for question in requirement.questions[:answered_count]
    ]

    pending = get_unanswered_questions(requirement, answers)

    assert len(pending) == expected_pending_count

    assert [question.id for question in pending] == [
        question.id
        for question in requirement.questions[answered_count:]
    ]
