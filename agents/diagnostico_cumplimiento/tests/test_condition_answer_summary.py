
from pathlib import Path

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.interpretation import (
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.condition_answer_summary import (
    summarize_condition_answers,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)


def get_requirement() -> RequirementDefinition:
    return load_catalog(PILOT_PATH).requirements[0]


def build_answer(
    requirement: RequirementDefinition,
    question_id: str,
    raw_answer: bool | str,
) -> QuestionAnswer:
    return QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=raw_answer,
    )


def requirement_with_two_health_questions() -> RequirementDefinition:
    """
    Crea una variante sintética del piloto para comprobar
    que una condición puede tener más de una pregunta.

    No modifica el archivo JSON original.
    """
    requirement = get_requirement()
    data = requirement.model_dump()

    additional_question = {
        **data["questions"][0],
        "id": "q_health_support",
        "text": "¿Cuenta con los soportes de afiliación en salud?",
    }

    data["questions"].append(additional_question)

    return RequirementDefinition.model_validate(data)


def test_groups_partial_answers_by_condition() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", "Sí"),
        build_answer(requirement, "q_pension_affiliation", "No sé"),
    ]

    summaries = summarize_condition_answers(requirement, answers)

    assert [summary.condition_id for summary in summaries] == [
        "health_affiliation",
        "pension_affiliation",
        "occupational_risk_affiliation",
    ]

    health, pension, occupational_risk = summaries

    assert health.interpretations[0].status == (
        InterpretationStatus.AFFIRMATIVE
    )
    assert health.unanswered_question_ids == []
    assert health.unresolved_question_ids == []

    assert pension.interpretations[0].status == (
        InterpretationStatus.INSUFFICIENT_INFORMATION
    )
    assert pension.unanswered_question_ids == []
    assert pension.unresolved_question_ids == [
        "q_pension_affiliation"
    ]

    assert occupational_risk.interpretations == []
    assert occupational_risk.unanswered_question_ids == [
        "q_occupational_risk_affiliation"
    ]


def test_tracks_pending_question_within_same_condition() -> None:
    requirement = requirement_with_two_health_questions()

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
    ]

    summaries = summarize_condition_answers(requirement, answers)
    health = summaries[0]

    assert health.condition_id == "health_affiliation"

    assert [item.question_id for item in health.interpretations] == [
        "q_health_affiliation"
    ]

    assert health.unanswered_question_ids == [
        "q_health_support"
    ]

    assert health.unresolved_question_ids == []


def test_tracks_unresolved_question_within_same_condition() -> None:
    requirement = requirement_with_two_health_questions()

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
        build_answer(requirement, "q_health_support", "No sé"),
    ]

    summaries = summarize_condition_answers(requirement, answers)
    health = summaries[0]

    assert [item.status for item in health.interpretations] == [
        InterpretationStatus.AFFIRMATIVE,
        InterpretationStatus.INSUFFICIENT_INFORMATION,
    ]

    assert health.unanswered_question_ids == []
    assert health.unresolved_question_ids == [
        "q_health_support"
    ]


def test_identifies_all_questions_as_pending_without_answers() -> None:
    requirement = get_requirement()

    summaries = summarize_condition_answers(requirement, [])

    assert len(summaries) == 3

    for summary in summaries:
        assert summary.interpretations == []
        assert summary.unresolved_question_ids == []
        assert len(summary.unanswered_question_ids) == 1
