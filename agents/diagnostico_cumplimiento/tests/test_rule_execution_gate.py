
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.evaluation_rule import (
    ConditionEvaluationRule,
    EvaluationOperator,
    RuleReviewStatus,
)
from agents.diagnostico_cumplimiento.rules.evaluation_rule_validation import (
    EvaluationRuleReferenceError,
)
from agents.diagnostico_cumplimiento.rules.rule_execution_gate import (
    RuleExecutionStatus,
    check_rule_execution_readiness,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)


def get_requirement():
    return load_catalog(PILOT_PATH).requirements[0]


def build_rule(requirement, **overrides):
    data = {
        "id": "pilot_health_rule_v1",
        "requirement_id": requirement.id,
        "condition_id": "health_affiliation",
        "criterion_reference": "res0312_art3_afiliacion_integral",
        "question_ids": ["q_health_affiliation"],
        "operator": EvaluationOperator.ALL_AFFIRMATIVE,
    }

    data.update(overrides)

    return ConditionEvaluationRule(**data)


def test_draft_rule_is_blocked() -> None:
    requirement = get_requirement()
    rule = build_rule(requirement)

    decision = check_rule_execution_readiness(rule, requirement)

    assert decision.rule_id == rule.id
    assert decision.status == RuleExecutionStatus.BLOCKED_DRAFT
    assert decision.authorized is False

    assert rule.review_status == RuleReviewStatus.DRAFT


def test_validated_status_alone_does_not_authorize_execution() -> None:
    requirement = get_requirement()

    rule = build_rule(
        requirement,
        review_status=RuleReviewStatus.VALIDATED,
    )

    decision = check_rule_execution_readiness(rule, requirement)

    assert decision.status == (
        RuleExecutionStatus.BLOCKED_PENDING_COVERAGE
    )
    assert decision.authorized is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"requirement_id": "another_requirement"},
        {"condition_id": "unknown_condition"},
        {"question_ids": ["unknown_question"]},
        {"question_ids": ["q_pension_affiliation"]},
    ],
)
def test_rejects_rule_with_invalid_references(overrides) -> None:
    requirement = get_requirement()
    rule = build_rule(requirement, **overrides)

    with pytest.raises(EvaluationRuleReferenceError):
        check_rule_execution_readiness(rule, requirement)


def test_check_does_not_change_review_status() -> None:
    requirement = get_requirement()
    rule = build_rule(requirement)

    check_rule_execution_readiness(rule, requirement)

    assert rule.review_status == RuleReviewStatus.DRAFT
