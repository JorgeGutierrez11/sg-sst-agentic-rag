
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.evaluation_rule import (
    ConditionEvaluationRule,
    EvaluationOperator,
)
from agents.diagnostico_cumplimiento.rules.evaluation_rule_validation import (
    EvaluationRuleReferenceError,
    validate_evaluation_rule_references,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)


def get_requirement():
    return load_catalog(PILOT_PATH).requirements[0]


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


def test_accepts_existing_references() -> None:
    requirement = get_requirement()
    rule = build_rule()

    validate_evaluation_rule_references(rule, requirement)


def test_rejects_reference_to_another_requirement() -> None:
    requirement = get_requirement()

    rule = build_rule(
        requirement_id="another_requirement",
    )

    with pytest.raises(EvaluationRuleReferenceError):
        validate_evaluation_rule_references(rule, requirement)


def test_rejects_unknown_condition() -> None:
    requirement = get_requirement()

    rule = build_rule(
        condition_id="unknown_condition",
    )

    with pytest.raises(EvaluationRuleReferenceError):
        validate_evaluation_rule_references(rule, requirement)


def test_rejects_unknown_question() -> None:
    requirement = get_requirement()

    rule = build_rule(
        question_ids=["unknown_question"],
    )

    with pytest.raises(EvaluationRuleReferenceError):
        validate_evaluation_rule_references(rule, requirement)


def test_rejects_question_from_another_condition() -> None:
    requirement = get_requirement()

    rule = build_rule(
        condition_id="health_affiliation",
        question_ids=["q_pension_affiliation"],
    )

    with pytest.raises(EvaluationRuleReferenceError):
        validate_evaluation_rule_references(rule, requirement)


def test_rejects_mixed_questions_from_different_conditions() -> None:
    requirement = get_requirement()

    rule = build_rule(
        question_ids=[
            "q_health_affiliation",
            "q_pension_affiliation",
        ],
    )

    with pytest.raises(EvaluationRuleReferenceError):
        validate_evaluation_rule_references(rule, requirement)
