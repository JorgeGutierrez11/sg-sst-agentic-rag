
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.interpretation import (
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_collection import (
    DuplicateAnswerError,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_validation import (
    AnswerReferenceError,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_answer_processor import (
    process_requirement_answers,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)


def get_requirement():
    return load_catalog(PILOT_PATH).requirements[0]


def build_answer(requirement, question_id, raw_answer):
    return QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=raw_answer,
    )


def test_processes_partial_answers() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", "Sí"),
        build_answer(requirement, "q_pension_affiliation", "No sé"),
    ]

    result = process_requirement_answers(requirement, answers)

    assert result.requirement_id == requirement.id

    assert [
        interpretation.status
        for interpretation in result.interpretations
    ] == [
        InterpretationStatus.AFFIRMATIVE,
        InterpretationStatus.INSUFFICIENT_INFORMATION,
    ]

    assert result.unanswered_question_ids == [
        "q_occupational_risk_affiliation",
    ]

    assert result.unresolved_question_ids == [
        "q_pension_affiliation",
    ]


def test_identifies_all_questions_as_pending_when_no_answers() -> None:
    requirement = get_requirement()

    result = process_requirement_answers(requirement, [])

    assert result.interpretations == []
    assert result.unanswered_question_ids == [
        question.id for question in requirement.questions
    ]
    assert result.unresolved_question_ids == []


def test_processes_all_resolved_answers() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, question.id, True)
        for question in requirement.questions
    ]

    result = process_requirement_answers(requirement, answers)

    assert len(result.interpretations) == 3
    assert all(
        interpretation.status == InterpretationStatus.AFFIRMATIVE
        for interpretation in result.interpretations
    )
    assert result.unanswered_question_ids == []
    assert result.unresolved_question_ids == []


@pytest.mark.parametrize(
    "raw_answer",
    [
        "Creo que sí, pero no estoy seguro.",
        8,
    ],
)
def test_identifies_unresolved_answers(raw_answer) -> None:
    requirement = get_requirement()
    question_id = requirement.questions[0].id

    answer = build_answer(requirement, question_id, raw_answer)

    result = process_requirement_answers(requirement, [answer])

    assert result.unresolved_question_ids == [question_id]
    assert question_id not in result.unanswered_question_ids
    assert result.interpretations[0].interpreted_value is None


def test_rejects_duplicate_answers() -> None:
    requirement = get_requirement()
    question_id = requirement.questions[0].id

    answers = [
        build_answer(requirement, question_id, True),
        build_answer(requirement, question_id, False),
    ]

    with pytest.raises(DuplicateAnswerError):
        process_requirement_answers(requirement, answers)


def test_rejects_answer_for_another_requirement() -> None:
    requirement = get_requirement()

    answer = QuestionAnswer(
        requirement_id="another_requirement",
        question_id=requirement.questions[0].id,
        raw_answer=True,
    )

    with pytest.raises(AnswerReferenceError):
        process_requirement_answers(requirement, [answer])
