
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.condition_evaluation import (
    ConditionEvaluationStatus,
)
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
    build_requirement_snapshot,
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


def test_snapshot_preserves_original_answers_and_interpretations() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", "Sí"),
        build_answer(requirement, "q_pension_affiliation", "No sé"),
    ]

    snapshot = build_requirement_snapshot(requirement, answers)

    assert snapshot.requirement_id == requirement.id
    assert snapshot.criterion_name == requirement.criterion.name
    assert snapshot.collection_status == (
        RequirementCollectionStatus.NEEDS_RESOLUTION
    )

    health_question = snapshot.conditions[0].questions[0]
    pension_question = snapshot.conditions[1].questions[0]
    risk_question = snapshot.conditions[2].questions[0]

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


def test_snapshot_contains_questions_in_catalog_order() -> None:
    requirement = get_requirement()

    snapshot = build_requirement_snapshot(requirement, [])

    assert [condition.condition_id for condition in snapshot.conditions] == [
        condition.id for condition in requirement.conditions
    ]

    question_ids = [
        question.question_id
        for condition in snapshot.conditions
        for question in condition.questions
    ]

    assert question_ids == [
        question.id for question in requirement.questions
    ]


def test_snapshot_with_no_answers_remains_pending() -> None:
    requirement = get_requirement()

    snapshot = build_requirement_snapshot(requirement, [])

    assert snapshot.collection_status == (
        RequirementCollectionStatus.NOT_STARTED
    )

    for condition in snapshot.conditions:
        assert condition.evaluation.status == (
            ConditionEvaluationStatus.PENDING_INFORMATION
        )

        for question in condition.questions:
            assert question.answer is None
            assert question.interpretation is None


def test_all_affirmative_answers_do_not_imply_compliance() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, question.id, True)
        for question in requirement.questions
    ]

    snapshot = build_requirement_snapshot(requirement, answers)

    assert snapshot.collection_status == (
        RequirementCollectionStatus.ANSWERS_INTERPRETED
    )

    assert all(
        condition.evaluation.status
        == ConditionEvaluationStatus.NOT_EVALUATED
        for condition in snapshot.conditions
    )


def test_snapshot_can_be_serialized_to_json() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", "Sí"),
    ]

    snapshot = build_requirement_snapshot(requirement, answers)

    data = snapshot.model_dump(mode="json")

    assert isinstance(data, dict)
    assert data["requirement_id"] == requirement.id
    assert data["collection_status"] == "in_progress"

    health = data["conditions"][0]

    assert health["collection_status"] == "answers_interpreted"
    assert health["evaluation"]["status"] == "not_evaluated"

    assert health["questions"][0]["answer"]["raw_answer"] == "Sí"
    assert health["questions"][0]["interpretation"]["status"] == (
        "affirmative"
    )

    assert data["conditions"][1]["questions"][0]["answer"] is None

    # Comprueba también que el modelo produce JSON serializable.
    assert isinstance(snapshot.model_dump_json(), str)


def test_rejects_duplicate_answers() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
        build_answer(requirement, "q_health_affiliation", False),
    ]

    with pytest.raises(DuplicateAnswerError):
        build_requirement_snapshot(requirement, answers)


def test_rejects_answer_for_another_requirement() -> None:
    requirement = get_requirement()

    answer = QuestionAnswer(
        requirement_id="another_requirement",
        question_id="q_health_affiliation",
        raw_answer=True,
    )

    with pytest.raises(AnswerReferenceError):
        build_requirement_snapshot(requirement, [answer])
