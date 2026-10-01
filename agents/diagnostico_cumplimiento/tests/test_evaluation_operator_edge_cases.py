
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.enums import QuestionType
from agents.diagnostico_cumplimiento.domain.evaluation_rule import (
    ConditionEvaluationRule,
    EvaluationOperator,
)
from agents.diagnostico_cumplimiento.questionnaire.condition_answer_summary import (
    summarize_condition_answers,
)
from agents.diagnostico_cumplimiento.rules.evaluation_operator import (
    RuleLogicStatus,
    evaluate_rule_logic,
)
from agents.diagnostico_cumplimiento.rules.evaluation_rule_validation import (
    EvaluationRuleReferenceError,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)


def get_requirement() -> RequirementDefinition:
    return load_catalog(PILOT_PATH).requirements[0]


def build_rule(
    requirement: RequirementDefinition,
    question_ids: list[str],
) -> ConditionEvaluationRule:
    return ConditionEvaluationRule(
        id="test_health_rule",
        requirement_id=requirement.id,
        condition_id="health_affiliation",
        criterion_reference="test_criterion",
        question_ids=question_ids,
        operator=EvaluationOperator.ALL_AFFIRMATIVE,
    )


def test_rejects_non_boolean_question() -> None:
    requirement = get_requirement()
    data = requirement.model_dump(mode="json")

    data["questions"][0]["type"] = QuestionType.TEXT.value

    requirement = RequirementDefinition.model_validate(data)

    rule = build_rule(
        requirement,
        ["q_health_affiliation"],
    )

    summary = summarize_condition_answers(requirement, [])[0]

    with pytest.raises(ValueError):
        evaluate_rule_logic(rule, requirement, summary)


def test_rejects_summary_from_another_requirement() -> None:
    requirement = get_requirement()

    rule = build_rule(
        requirement,
        ["q_health_affiliation"],
    )

    summary = summarize_condition_answers(requirement, [])[0]

    incorrect_summary = summary.model_copy(
        update={"requirement_id": "another_requirement"}
    )

    with pytest.raises(EvaluationRuleReferenceError):
        evaluate_rule_logic(
            rule,
            requirement,
            incorrect_summary,
        )


def test_negative_answer_and_missing_answer_remain_pending() -> None:
    requirement = get_requirement()
    data = requirement.model_dump(mode="json")

    additional_question = {
        **data["questions"][0],
        "id": "q_health_support",
        "text": "¿Cuenta con los soportes de afiliación en salud?",
    }

    data["questions"].append(additional_question)

    requirement = RequirementDefinition.model_validate(data)

    rule = build_rule(
        requirement,
        [
            "q_health_affiliation",
            "q_health_support",
        ],
    )

    answers = [
        QuestionAnswer(
            requirement_id=requirement.id,
            question_id="q_health_affiliation",
            raw_answer=False,
        ),
    ]

    summary = summarize_condition_answers(
        requirement,
        answers,
    )[0]

    result = evaluate_rule_logic(
        rule,
        requirement,
        summary,
    )

    assert result.status == RuleLogicStatus.PENDING_INFORMATION
    assert summary.unanswered_question_ids == ["q_health_support"]
