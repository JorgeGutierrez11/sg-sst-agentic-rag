import pytest

from agents.diagnostico_cumplimiento.catalog.schemas import (
    AssessmentCatalog,
    CatalogRequirementDefinition,
)
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
from agents.diagnostico_cumplimiento.questionnaire.requirement_progress import (
    RequirementCollectionStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_snapshot import (
    QuestionRoutingState,
    build_requirement_snapshot,
)


REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"


def get_requirement(
    catalog: AssessmentCatalog,
) -> CatalogRequirementDefinition:
    return next(
        requirement
        for requirement in catalog.requirements
        if requirement.id == REQUIREMENT_ID
    )


def build_answer(requirement, question_id, raw_answer):
    return QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=raw_answer,
    )


def questions_by_id(snapshot):
    return {question.question_id: question for question in snapshot.questions}


def test_snapshot_preserves_original_answers_and_interpretations(
    catalog: AssessmentCatalog,
) -> None:
    requirement = get_requirement(catalog)

    answers = [
        build_answer(requirement, "q_health_affiliation", "Sí"),
        build_answer(requirement, "q_pension_affiliation", "No sé"),
    ]

    snapshot = build_requirement_snapshot(requirement, answers)

    assert snapshot.requirement_id == requirement.id
    assert snapshot.criterion_name == requirement.name
    assert snapshot.collection_status == (
        RequirementCollectionStatus.NEEDS_RESOLUTION
    )

    questions = questions_by_id(snapshot)

    health_question = questions["q_health_affiliation"]
    pension_question = questions["q_pension_affiliation"]
    risk_question = questions["q_occupational_risk_affiliation"]

    assert health_question.answer.raw_answer == "Sí"
    assert health_question.interpretation.status == (
        InterpretationStatus.AFFIRMATIVE
    )
    assert health_question.interpretation.interpreted_value is True

    assert pension_question.answer.raw_answer == "No sé"
    assert pension_question.interpretation.status == (
        InterpretationStatus.INSUFFICIENT_INFORMATION
    )
    assert pension_question.interpretation.interpreted_value is None

    assert risk_question.answer is None
    assert risk_question.interpretation is None

    # La salida no modifica las respuestas originales.
    assert [answer.raw_answer for answer in answers] == ["Sí", "No sé"]


def test_snapshot_contains_questions_in_catalog_order(
    catalog: AssessmentCatalog,
) -> None:
    requirement = get_requirement(catalog)

    snapshot = build_requirement_snapshot(requirement, [])

    assert [question.question_id for question in snapshot.questions] == [
        question.id for question in requirement.questions
    ]

    # Role and dependency are copied from the catalog definition.
    for snapshot_question, question in zip(
        snapshot.questions,
        requirement.questions,
        strict=True,
    ):
        assert snapshot_question.role == question.role
        assert snapshot_question.depends_on == question.depends_on


def test_snapshot_with_no_answers_remains_pending(
    catalog: AssessmentCatalog,
) -> None:
    requirement = get_requirement(catalog)

    snapshot = build_requirement_snapshot(requirement, [])

    assert snapshot.collection_status == (
        RequirementCollectionStatus.NOT_STARTED
    )

    for question in snapshot.questions:
        assert question.answer is None
        assert question.interpretation is None

        expected_state = (
            QuestionRoutingState.BLOCKED
            if question.depends_on is not None
            else QuestionRoutingState.ACTIVE
        )
        assert question.routing_state == expected_state


def test_all_affirmative_answers_do_not_imply_compliance(
    catalog: AssessmentCatalog,
) -> None:
    requirement = get_requirement(catalog)

    answers = [
        build_answer(requirement, question.id, True)
        for question in requirement.questions
    ]

    snapshot = build_requirement_snapshot(requirement, answers)

    assert snapshot.collection_status == (
        RequirementCollectionStatus.ANSWERS_INTERPRETED
    )

    # The snapshot only consolidates declarations: it exposes no
    # compliance verdict, and every question is simply active.
    assert not hasattr(snapshot, "compliance_status")
    assert all(
        question.routing_state == QuestionRoutingState.ACTIVE
        for question in snapshot.questions
    )
    assert snapshot.unanswered_question_ids == []
    assert snapshot.blocked_question_ids == []


def test_negative_parent_skips_dependent_questions(
    catalog: AssessmentCatalog,
) -> None:
    requirement = get_requirement(catalog)

    answers = [
        build_answer(requirement, "q_health_affiliation", False),
    ]

    snapshot = build_requirement_snapshot(requirement, answers)
    questions = questions_by_id(snapshot)

    assert questions["q_health_affiliation_support"].routing_state == (
        QuestionRoutingState.SKIPPED
    )
    assert questions["q_health_payment_support"].routing_state == (
        QuestionRoutingState.SKIPPED
    )
    assert snapshot.skipped_question_ids == [
        "q_health_affiliation_support",
        "q_health_payment_support",
    ]


def test_snapshot_can_be_serialized_to_json(
    catalog: AssessmentCatalog,
) -> None:
    requirement = get_requirement(catalog)

    answers = [
        build_answer(requirement, "q_health_affiliation", "Sí"),
    ]

    snapshot = build_requirement_snapshot(requirement, answers)

    data = snapshot.model_dump(mode="json")

    assert isinstance(data, dict)
    assert data["requirement_id"] == requirement.id
    assert data["collection_status"] == "in_progress"

    health = data["questions"][0]

    assert health["question_id"] == "q_health_affiliation"
    assert health["role"] == "primary"
    assert health["routing_state"] == "active"
    assert health["answer"]["raw_answer"] == "Sí"
    assert health["interpretation"]["status"] == "affirmative"

    pension = next(
        question
        for question in data["questions"]
        if question["question_id"] == "q_pension_affiliation"
    )
    assert pension["answer"] is None

    # Comprueba también que el modelo produce JSON serializable.
    assert isinstance(snapshot.model_dump_json(), str)


def test_rejects_duplicate_answers(catalog: AssessmentCatalog) -> None:
    requirement = get_requirement(catalog)

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
        build_answer(requirement, "q_health_affiliation", False),
    ]

    with pytest.raises(DuplicateAnswerError):
        build_requirement_snapshot(requirement, answers)


def test_rejects_answer_for_another_requirement(
    catalog: AssessmentCatalog,
) -> None:
    requirement = get_requirement(catalog)

    answer = QuestionAnswer(
        requirement_id="another_requirement",
        question_id="q_health_affiliation",
        raw_answer=True,
    )

    with pytest.raises(AnswerReferenceError):
        build_requirement_snapshot(requirement, [answer])
