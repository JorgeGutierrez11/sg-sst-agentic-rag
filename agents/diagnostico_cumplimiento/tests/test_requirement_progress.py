
from pathlib import Path

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.questionnaire.condition_progress import (
    ConditionCollectionStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_progress import (
    RequirementCollectionStatus,
    determine_requirement_progress,
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
    raw_answer: bool | str | int,
) -> QuestionAnswer:
    return QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=raw_answer,
    )


def test_requirement_not_started() -> None:
    requirement = get_requirement()

    result = determine_requirement_progress(requirement, [])

    assert result.requirement_id == requirement.id
    assert result.status == RequirementCollectionStatus.NOT_STARTED
    assert len(result.conditions) == 3

    assert all(
        condition.status == ConditionCollectionStatus.NOT_STARTED
        for condition in result.conditions
    )


def test_requirement_in_progress() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
    ]

    result = determine_requirement_progress(requirement, answers)

    assert result.status == RequirementCollectionStatus.IN_PROGRESS

    assert [condition.status for condition in result.conditions] == [
        ConditionCollectionStatus.ANSWERS_INTERPRETED,
        ConditionCollectionStatus.NOT_STARTED,
        ConditionCollectionStatus.NOT_STARTED,
    ]


def test_requirement_needs_resolution() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", "Sí"),
        build_answer(requirement, "q_pension_affiliation", "No sé"),
    ]

    result = determine_requirement_progress(requirement, answers)

    assert result.status == RequirementCollectionStatus.NEEDS_RESOLUTION

    assert [condition.status for condition in result.conditions] == [
        ConditionCollectionStatus.ANSWERS_INTERPRETED,
        ConditionCollectionStatus.NEEDS_RESOLUTION,
        ConditionCollectionStatus.NOT_STARTED,
    ]

    assert result.conditions[1].summary.unresolved_question_ids == [
        "q_pension_affiliation",
    ]


def test_requirement_with_all_answers_interpreted() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
        build_answer(requirement, "q_pension_affiliation", False),
        build_answer(
            requirement,
            "q_occupational_risk_affiliation",
            True,
        ),
    ]

    result = determine_requirement_progress(requirement, answers)

    assert result.status == (
        RequirementCollectionStatus.ANSWERS_INTERPRETED
    )

    assert all(
        condition.status == ConditionCollectionStatus.ANSWERS_INTERPRETED
        for condition in result.conditions
    )

    assert [
        condition.summary.interpretations[0].interpreted_value
        for condition in result.conditions
    ] == [True, False, True]


def test_invalid_format_requires_resolution() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", 8),
        build_answer(requirement, "q_pension_affiliation", True),
        build_answer(
            requirement,
            "q_occupational_risk_affiliation",
            True,
        ),
    ]

    result = determine_requirement_progress(requirement, answers)

    assert result.status == RequirementCollectionStatus.NEEDS_RESOLUTION

    assert result.conditions[0].status == (
        ConditionCollectionStatus.NEEDS_RESOLUTION
    )

    assert result.conditions[0].summary.unresolved_question_ids == [
        "q_health_affiliation",
    ]


def test_requirement_with_partially_answered_condition() -> None:
    requirement = get_requirement()

    # Variante sintética: agregamos una segunda pregunta a salud.
    # El catálogo piloto original no se modifica.
    data = requirement.model_dump()

    additional_question = {
        **data["questions"][0],
        "id": "q_health_support",
        "text": "¿Cuenta con los soportes de afiliación en salud?",
    }

    data["questions"].append(additional_question)

    requirement = RequirementDefinition.model_validate(data)

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
        build_answer(requirement, "q_pension_affiliation", True),
        build_answer(
            requirement,
            "q_occupational_risk_affiliation",
            True,
        ),
    ]

    result = determine_requirement_progress(requirement, answers)

    assert result.status == RequirementCollectionStatus.IN_PROGRESS

    assert result.conditions[0].status == (
        ConditionCollectionStatus.PARTIAL
    )

    assert result.conditions[0].summary.unanswered_question_ids == [
        "q_health_support",
    ]
