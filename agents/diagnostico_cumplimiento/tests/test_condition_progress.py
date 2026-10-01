
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.questionnaire.condition_answer_summary import (
    ConditionAnswerSummary,
    summarize_condition_answers,
)
from agents.diagnostico_cumplimiento.questionnaire.condition_progress import (
    ConditionCollectionStatus,
    determine_condition_collection_status,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)


def get_requirement() -> RequirementDefinition:
    return load_catalog(PILOT_PATH).requirements[0]


def requirement_with_two_health_questions() -> RequirementDefinition:
    """Crea una variante de prueba sin modificar el catálogo piloto."""
    requirement = get_requirement()
    data = requirement.model_dump()

    additional_question = {
        **data["questions"][0],
        "id": "q_health_support",
        "text": "¿Cuenta con los soportes de afiliación en salud?",
    }

    data["questions"].append(additional_question)

    return RequirementDefinition.model_validate(data)


def build_answer(
    requirement: RequirementDefinition,
    question_id: str,
    raw_answer: bool | str | int,
) -> QuestionAnswer:
    return QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=raw_answer,
    )


def get_health_summary(
    requirement: RequirementDefinition,
    answers: list[QuestionAnswer],
) -> ConditionAnswerSummary:
    summaries = summarize_condition_answers(requirement, answers)

    return next(
        summary
        for summary in summaries
        if summary.condition_id == "health_affiliation"
    )


def test_condition_not_started() -> None:
    requirement = get_requirement()

    summary = get_health_summary(requirement, [])

    assert determine_condition_collection_status(summary) == (
        ConditionCollectionStatus.NOT_STARTED
    )


def test_condition_partially_answered() -> None:
    requirement = requirement_with_two_health_questions()

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
    ]

    summary = get_health_summary(requirement, answers)

    assert summary.unanswered_question_ids == [
        "q_health_support"
    ]

    assert determine_condition_collection_status(summary) == (
        ConditionCollectionStatus.PARTIAL
    )


def test_unresolved_answer_takes_priority_over_pending_question() -> None:
    requirement = requirement_with_two_health_questions()

    answers = [
        build_answer(requirement, "q_health_affiliation", "No sé"),
    ]

    summary = get_health_summary(requirement, answers)

    assert summary.unresolved_question_ids == [
        "q_health_affiliation"
    ]

    assert summary.unanswered_question_ids == [
        "q_health_support"
    ]

    assert determine_condition_collection_status(summary) == (
        ConditionCollectionStatus.NEEDS_RESOLUTION
    )


def test_all_answers_interpreted_with_different_values() -> None:
    requirement = requirement_with_two_health_questions()

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
        build_answer(requirement, "q_health_support", False),
    ]

    summary = get_health_summary(requirement, answers)

    assert summary.unanswered_question_ids == []
    assert summary.unresolved_question_ids == []

    assert [
        interpretation.interpreted_value
        for interpretation in summary.interpretations
    ] == [True, False]

    assert determine_condition_collection_status(summary) == (
        ConditionCollectionStatus.ANSWERS_INTERPRETED
    )


@pytest.mark.parametrize(
    "raw_answer",
    [
        "No sé",
        8,
    ],
)
def test_condition_needs_resolution_for_uninterpretable_answer(
    raw_answer: str | int,
) -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", raw_answer),
    ]

    summary = get_health_summary(requirement, answers)

    assert summary.unanswered_question_ids == []
    assert summary.unresolved_question_ids == [
        "q_health_affiliation"
    ]

    assert determine_condition_collection_status(summary) == (
        ConditionCollectionStatus.NEEDS_RESOLUTION
    )


def test_rejects_condition_without_registered_questions() -> None:
    summary = ConditionAnswerSummary(
        requirement_id="test_requirement",
        condition_id="test_condition",
    )

    with pytest.raises(ValueError):
        determine_condition_collection_status(summary)
