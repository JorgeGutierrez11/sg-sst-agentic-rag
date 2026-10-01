
import pytest
from pydantic import ValidationError

from agents.diagnostico_cumplimiento.domain.condition_evaluation import (
    ConditionEvaluation,
    ConditionEvaluationStatus,
)


REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"
CONDITION_ID = "health_affiliation"
QUESTION_ID = "q_health_affiliation"


def build_evaluation(
    status: ConditionEvaluationStatus,
    **kwargs,
) -> ConditionEvaluation:
    return ConditionEvaluation(
        requirement_id=REQUIREMENT_ID,
        condition_id=CONDITION_ID,
        status=status,
        explanation="Resultado de prueba.",
        **kwargs,
    )


def test_accepts_not_evaluated_condition() -> None:
    result = build_evaluation(
        ConditionEvaluationStatus.NOT_EVALUATED,
    )

    assert result.status == ConditionEvaluationStatus.NOT_EVALUATED
    assert result.criterion_reference is None
    assert result.evaluated_question_ids == []


def test_accepts_condition_pending_information() -> None:
    result = build_evaluation(
        ConditionEvaluationStatus.PENDING_INFORMATION,
    )

    assert result.status == (
        ConditionEvaluationStatus.PENDING_INFORMATION
    )
    assert result.criterion_reference is None
    assert result.evaluated_question_ids == []


@pytest.mark.parametrize(
    "status",
    [
        ConditionEvaluationStatus.SATISFIED_AS_DECLARED,
        ConditionEvaluationStatus.NOT_SATISFIED_AS_DECLARED,
    ],
)
def test_accepts_evaluated_condition_with_traceability(
    status: ConditionEvaluationStatus,
) -> None:
    result = build_evaluation(
        status,
        criterion_reference="pilot_criterion_v1",
        evaluated_question_ids=[QUESTION_ID],
    )

    assert result.status == status
    assert result.criterion_reference == "pilot_criterion_v1"
    assert result.evaluated_question_ids == [QUESTION_ID]


@pytest.mark.parametrize(
    "status",
    [
        ConditionEvaluationStatus.SATISFIED_AS_DECLARED,
        ConditionEvaluationStatus.NOT_SATISFIED_AS_DECLARED,
    ],
)
def test_rejects_evaluated_condition_without_criterion(
    status: ConditionEvaluationStatus,
) -> None:
    with pytest.raises(ValidationError):
        build_evaluation(
            status,
            evaluated_question_ids=[QUESTION_ID],
        )


def test_rejects_evaluated_condition_without_question_references() -> None:
    with pytest.raises(ValidationError):
        build_evaluation(
            ConditionEvaluationStatus.SATISFIED_AS_DECLARED,
            criterion_reference="pilot_criterion_v1",
        )


def test_rejects_duplicate_question_references() -> None:
    with pytest.raises(ValidationError):
        build_evaluation(
            ConditionEvaluationStatus.SATISFIED_AS_DECLARED,
            criterion_reference="pilot_criterion_v1",
            evaluated_question_ids=[QUESTION_ID, QUESTION_ID],
        )


def test_rejects_criterion_for_not_evaluated_condition() -> None:
    with pytest.raises(ValidationError):
        build_evaluation(
            ConditionEvaluationStatus.NOT_EVALUATED,
            criterion_reference="pilot_criterion_v1",
        )


def test_rejects_evaluated_questions_for_pending_condition() -> None:
    with pytest.raises(ValidationError):
        build_evaluation(
            ConditionEvaluationStatus.PENDING_INFORMATION,
            evaluated_question_ids=[QUESTION_ID],
        )


def test_rejects_empty_explanation() -> None:
    with pytest.raises(ValidationError):
        ConditionEvaluation(
            requirement_id=REQUIREMENT_ID,
            condition_id=CONDITION_ID,
            status=ConditionEvaluationStatus.NOT_EVALUATED,
            explanation="",
        )
