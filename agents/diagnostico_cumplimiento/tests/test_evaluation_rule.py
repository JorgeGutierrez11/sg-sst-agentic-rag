
import pytest
from pydantic import ValidationError

from agents.diagnostico_cumplimiento.domain.evaluation_rule import (
    ConditionEvaluationRule,
    EvaluationOperator,
    RuleReviewStatus,
)


def build_rule(**overrides) -> ConditionEvaluationRule:
    data = {
        "id": "pilot_health_rule_v1",
        "requirement_id": "res0312_art3_afiliacion_1_10",
        "condition_id": "health_affiliation",
        "criterion_reference": "res0312_art3_afiliacion_integral",
        "question_ids": ["q_health_affiliation"],
        "operator": EvaluationOperator.ALL_AFFIRMATIVE,
    }

    data.update(overrides)

    return ConditionEvaluationRule(**data)


def test_accepts_valid_draft_rule() -> None:
    rule = build_rule()

    assert rule.id == "pilot_health_rule_v1"
    assert rule.operator == EvaluationOperator.ALL_AFFIRMATIVE
    assert rule.review_status == RuleReviewStatus.DRAFT


def test_accepts_explicit_validated_status() -> None:
    rule = build_rule(
        review_status=RuleReviewStatus.VALIDATED,
    )

    assert rule.review_status == RuleReviewStatus.VALIDATED


def test_accepts_multiple_distinct_questions() -> None:
    rule = build_rule(
        question_ids=[
            "q_health_affiliation",
            "q_health_support",
        ],
    )

    assert rule.question_ids == [
        "q_health_affiliation",
        "q_health_support",
    ]


def test_rejects_duplicate_question_ids() -> None:
    with pytest.raises(ValidationError):
        build_rule(
            question_ids=[
                "q_health_affiliation",
                "q_health_affiliation",
            ],
        )


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "requirement_id",
        "condition_id",
        "criterion_reference",
    ],
)
def test_rejects_empty_required_identifier(field: str) -> None:
    with pytest.raises(ValidationError):
        build_rule(**{field: ""})


def test_rejects_empty_question_list() -> None:
    with pytest.raises(ValidationError):
        build_rule(question_ids=[])


def test_rejects_blank_question_identifier() -> None:
    with pytest.raises(ValidationError):
        build_rule(
            question_ids=["q_health_affiliation", "   "],
        )


def test_rejects_unknown_operator() -> None:
    with pytest.raises(ValidationError):
        build_rule(operator="unknown_operator")


def test_rejects_unknown_review_status() -> None:
    with pytest.raises(ValidationError):
        build_rule(review_status="approved_automatically")


def test_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        build_rule(unexpected_field="unexpected_value")
