
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.evaluation_rule import (
    ConditionEvaluationRule,
    EvaluationOperator,
    RuleReviewStatus,
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
    question_ids: list[str] | None = None,
    condition_id: str = "health_affiliation",
) -> ConditionEvaluationRule:
    return ConditionEvaluationRule(
        id="pilot_health_rule_v1",
        requirement_id=requirement.id,
        condition_id=condition_id,
        criterion_reference="res0312_art3_afiliacion_integral",
        question_ids=(
            question_ids
            if question_ids is not None
            else ["q_health_affiliation"]
        ),
        operator=EvaluationOperator.ALL_AFFIRMATIVE,
    )


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


def get_health_summary(
    requirement: RequirementDefinition,
    answers: list[QuestionAnswer],
):
    summaries = summarize_condition_answers(requirement, answers)
    return summaries[0]


def requirement_with_two_health_questions() -> RequirementDefinition:
    """
    Agrega una segunda pregunta a la condición de salud
    únicamente para las pruebas.
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


@pytest.mark.parametrize(
    ("raw_answer", "expected_status"),
    [
        (True, RuleLogicStatus.ALL_AFFIRMATIVE),
        (False, RuleLogicStatus.HAS_NEGATIVE),
        ("No sé", RuleLogicStatus.PENDING_INFORMATION),
        (
            "Creo que sí, pero no estoy seguro.",
            RuleLogicStatus.PENDING_INFORMATION,
        ),
    ],
)
def test_evaluates_single_question(
    raw_answer: bool | str,
    expected_status: RuleLogicStatus,
) -> None:
    requirement = get_requirement()
    rule = build_rule(requirement)

    answers = [
        build_answer(requirement, "q_health_affiliation", raw_answer),
    ]

    summary = get_health_summary(requirement, answers)

    result = evaluate_rule_logic(rule, requirement, summary)

    assert result.status == expected_status
    assert result.rule_id == rule.id
    assert result.requirement_id == requirement.id
    assert result.condition_id == "health_affiliation"
    assert result.question_ids == ["q_health_affiliation"]

    # La operación lógica no cambia el estado de revisión.
    assert rule.review_status == RuleReviewStatus.DRAFT


def test_missing_answer_produces_pending_information() -> None:
    requirement = get_requirement()
    rule = build_rule(requirement)

    summary = get_health_summary(requirement, [])

    result = evaluate_rule_logic(rule, requirement, summary)

    assert result.status == RuleLogicStatus.PENDING_INFORMATION


def test_all_affirmative_with_multiple_questions() -> None:
    requirement = requirement_with_two_health_questions()

    rule = build_rule(
        requirement,
        question_ids=[
            "q_health_affiliation",
            "q_health_support",
        ],
    )

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
        build_answer(requirement, "q_health_support", True),
    ]

    summary = get_health_summary(requirement, answers)

    result = evaluate_rule_logic(rule, requirement, summary)

    assert result.status == RuleLogicStatus.ALL_AFFIRMATIVE
    assert result.question_ids == [
        "q_health_affiliation",
        "q_health_support",
    ]


def test_negative_answer_with_multiple_questions() -> None:
    requirement = requirement_with_two_health_questions()

    rule = build_rule(
        requirement,
        question_ids=[
            "q_health_affiliation",
            "q_health_support",
        ],
    )

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
        build_answer(requirement, "q_health_support", False),
    ]

    summary = get_health_summary(requirement, answers)

    result = evaluate_rule_logic(rule, requirement, summary)

    assert result.status == RuleLogicStatus.HAS_NEGATIVE


def test_pending_answer_with_multiple_questions() -> None:
    requirement = requirement_with_two_health_questions()

    rule = build_rule(
        requirement,
        question_ids=[
            "q_health_affiliation",
            "q_health_support",
        ],
    )

    answers = [
        build_answer(requirement, "q_health_affiliation", True),
    ]

    summary = get_health_summary(requirement, answers)

    result = evaluate_rule_logic(rule, requirement, summary)

    assert result.status == RuleLogicStatus.PENDING_INFORMATION


def test_rejects_summary_from_another_condition() -> None:
    requirement = get_requirement()
    rule = build_rule(requirement)

    summaries = summarize_condition_answers(requirement, [])

    pension_summary = summaries[1]

    with pytest.raises(EvaluationRuleReferenceError):
        evaluate_rule_logic(
            rule,
            requirement,
            pension_summary,
        )


def test_rejects_rule_with_question_from_another_condition() -> None:
    requirement = get_requirement()

    rule = build_rule(
        requirement,
        question_ids=["q_pension_affiliation"],
    )

    summary = get_health_summary(requirement, [])

    with pytest.raises(EvaluationRuleReferenceError):
        evaluate_rule_logic(rule, requirement, summary)
