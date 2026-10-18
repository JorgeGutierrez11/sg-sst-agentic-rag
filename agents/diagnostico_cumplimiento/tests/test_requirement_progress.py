from agents.diagnostico_cumplimiento.catalog.schemas import (
    AssessmentCatalog,
    CatalogRequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.questionnaire.requirement_progress import (
    RequirementCollectionStatus,
    determine_requirement_progress,
)


REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"

PRIMARY_IDS = [
    "q_health_affiliation",
    "q_pension_affiliation",
    "q_occupational_risk_affiliation",
]

SUPPORT_IDS = {
    "q_health_affiliation": [
        "q_health_affiliation_support",
        "q_health_payment_support",
    ],
    "q_pension_affiliation": [
        "q_pension_affiliation_support",
        "q_pension_payment_support",
    ],
    "q_occupational_risk_affiliation": [
        "q_occupational_risk_affiliation_support",
        "q_occupational_risk_payment_support",
    ],
}


def get_requirement(
    catalog: AssessmentCatalog,
) -> CatalogRequirementDefinition:
    return next(
        requirement
        for requirement in catalog.requirements
        if requirement.id == REQUIREMENT_ID
    )


def build_answer(
    requirement: CatalogRequirementDefinition,
    question_id: str,
    raw_answer: bool | str | int,
) -> QuestionAnswer:
    return QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=raw_answer,
    )


def test_requirement_not_started(catalog: AssessmentCatalog) -> None:
    requirement = get_requirement(catalog)

    result = determine_requirement_progress(requirement, [])

    assert result.requirement_id == requirement.id
    assert result.status == RequirementCollectionStatus.NOT_STARTED

    # Only the root (primary) questions are active; every evidence
    # question waits for its parent answer.
    assert result.active_question_ids == PRIMARY_IDS
    assert result.unanswered_question_ids == PRIMARY_IDS
    assert result.blocked_question_ids == [
        support_id
        for primary_id in PRIMARY_IDS
        for support_id in SUPPORT_IDS[primary_id]
    ]
    assert result.skipped_question_ids == []
    assert result.interpretations == []


def test_requirement_in_progress(catalog: AssessmentCatalog) -> None:
    requirement = get_requirement(catalog)

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
    ]

    result = determine_requirement_progress(requirement, answers)

    assert result.status == RequirementCollectionStatus.IN_PROGRESS

    # The affirmative answer activates its dependent evidence questions.
    assert result.active_question_ids == [
        "q_health_affiliation",
        *SUPPORT_IDS["q_health_affiliation"],
        "q_pension_affiliation",
        "q_occupational_risk_affiliation",
    ]
    assert result.unanswered_question_ids == [
        *SUPPORT_IDS["q_health_affiliation"],
        "q_pension_affiliation",
        "q_occupational_risk_affiliation",
    ]
    assert result.blocked_question_ids == [
        *SUPPORT_IDS["q_pension_affiliation"],
        *SUPPORT_IDS["q_occupational_risk_affiliation"],
    ]
    assert result.unresolved_question_ids == []


def test_requirement_needs_resolution(catalog: AssessmentCatalog) -> None:
    requirement = get_requirement(catalog)

    answers = [
        build_answer(requirement, "q_health_affiliation", "Sí"),
        build_answer(requirement, "q_pension_affiliation", "No sé"),
    ]

    result = determine_requirement_progress(requirement, answers)

    assert result.status == RequirementCollectionStatus.NEEDS_RESOLUTION
    assert result.unresolved_question_ids == ["q_pension_affiliation"]

    # An unresolved parent keeps its dependents blocked, not skipped.
    assert set(SUPPORT_IDS["q_pension_affiliation"]) <= set(
        result.blocked_question_ids
    )
    assert result.skipped_question_ids == []


def test_requirement_with_all_answers_interpreted(
    catalog: AssessmentCatalog,
) -> None:
    requirement = get_requirement(catalog)

    # Health is affirmative and fully supported; the other two are
    # negative, so their evidence questions are skipped by routing.
    answers = [
        build_answer(requirement, "q_health_affiliation", True),
        build_answer(requirement, "q_health_affiliation_support", True),
        build_answer(requirement, "q_health_payment_support", True),
        build_answer(requirement, "q_pension_affiliation", False),
        build_answer(
            requirement,
            "q_occupational_risk_affiliation",
            False,
        ),
    ]

    result = determine_requirement_progress(requirement, answers)

    assert result.status == (
        RequirementCollectionStatus.ANSWERS_INTERPRETED
    )

    assert result.unanswered_question_ids == []
    assert result.unresolved_question_ids == []
    assert result.blocked_question_ids == []
    assert result.skipped_question_ids == [
        *SUPPORT_IDS["q_pension_affiliation"],
        *SUPPORT_IDS["q_occupational_risk_affiliation"],
    ]

    assert [
        (item.question_id, item.interpreted_value)
        for item in result.interpretations
    ] == [
        ("q_health_affiliation", True),
        ("q_health_affiliation_support", True),
        ("q_health_payment_support", True),
        ("q_pension_affiliation", False),
        ("q_occupational_risk_affiliation", False),
    ]


def test_invalid_format_requires_resolution(
    catalog: AssessmentCatalog,
) -> None:
    requirement = get_requirement(catalog)

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
    assert result.unresolved_question_ids == ["q_health_affiliation"]


def test_requirement_with_partially_answered_dependents(
    catalog: AssessmentCatalog,
) -> None:
    requirement = get_requirement(catalog)

    # Every primary is affirmative, but only one of the two evidence
    # questions under health has been answered.
    answers = [
        build_answer(requirement, "q_health_affiliation", True),
        build_answer(requirement, "q_health_affiliation_support", True),
        build_answer(requirement, "q_pension_affiliation", True),
        build_answer(
            requirement,
            "q_occupational_risk_affiliation",
            True,
        ),
    ]

    result = determine_requirement_progress(requirement, answers)

    assert result.status == RequirementCollectionStatus.IN_PROGRESS
    assert "q_health_payment_support" in result.unanswered_question_ids
    assert "q_health_affiliation_support" not in (
        result.unanswered_question_ids
    )
    assert result.blocked_question_ids == []
