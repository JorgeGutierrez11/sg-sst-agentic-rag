import json
from pathlib import Path

from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.preliminary_diagnosis import (
    run_preliminary_diagnosis,
)
from agents.diagnostico_cumplimiento.rules.routing.affiliation_question_routing import (
    AFFILIATION_REQUIREMENT_ID,
)

from agents.diagnostico_cumplimiento.questionnaire.questionnaire import (
    run_questionnaire,
)

CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v6.json"
)


def answer(question_id, value):
    return QuestionAnswer(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        question_id=question_id,
        raw_answer=value,
    )


def run_diagnosis(answers=None):
    return run_preliminary_diagnosis(
        profile=CompanyProfile(
            worker_count=8,
            risk_class=RiskClass.I,
        ),
        answers=answers or [],
        catalog_path=CATALOG_PATH,
    )

def get_affiliation_routing(result):
    return next(
        routing
        for routing in result.routing
        if routing.requirement_id
        == AFFILIATION_REQUIREMENT_ID
    )

def test_integrated_result_contains_affiliation_routing():
    result = run_diagnosis()

    routing = get_affiliation_routing(result)

    assert routing.requirement_id == AFFILIATION_REQUIREMENT_ID

    assert routing.questions_to_ask == [
        "q_health_affiliation",
        "q_pension_affiliation",
        "q_occupational_risk_affiliation",
    ]

    assert routing.answered_questions == []

    assert len(routing.omitted_questions) == 6


def test_integrated_routing_preserves_mixed_branches():
    result = run_diagnosis([
        answer("q_health_affiliation", True),
        answer("q_pension_affiliation", False),
    ])

    routing = get_affiliation_routing(result)

    assert routing.answered_questions == [
        "q_health_affiliation",
        "q_pension_affiliation",
    ]

    assert routing.questions_to_ask == [
        "q_health_affiliation_support",
        "q_health_payment_support",
        "q_occupational_risk_affiliation",
    ]

    assert routing.omitted_questions == [
        "q_pension_affiliation_support",
        "q_pension_payment_support",
        "q_occupational_risk_affiliation_support",
        "q_occupational_risk_payment_support",
    ]


def test_routing_is_serialized_with_its_reasons():
    result = run_diagnosis([
        answer("q_health_affiliation", False),
    ])

    data = json.loads(result.model_dump_json())

    assert "routing" in data


    routing = next(
        item
        for item in data["routing"]
        if item["requirement_id"]
        == AFFILIATION_REQUIREMENT_ID
    )

    decisions = routing["decisions"]

    support = next(
        decision
        for decision in decisions
        if decision["question_id"]
        == "q_health_affiliation_support"
    )

    assert support["status"] == "omit"
    assert support["rule_id"] == "health_support_dependency"
    assert support["triggered_by"] == "q_health_affiliation=False"
    assert support["reason"]


def test_routing_does_not_change_normative_evaluation():
    answers = [
        answer("q_health_affiliation", True),
        answer("q_pension_affiliation", True),
        answer("q_occupational_risk_affiliation", True),
    ]

    result = run_diagnosis(answers)

    direct_questionnaire = run_questionnaire(
        profile=CompanyProfile(
            worker_count=8,
            risk_class=RiskClass.I,
        ),
        answers=answers,
        catalog_path=CATALOG_PATH,
    )

    integrated_statuses = [
        condition.evaluation.status
        for requirement in result.questionnaire.requirements
        for condition in requirement.conditions
    ]

    direct_statuses = [
        condition.evaluation.status
        for requirement in direct_questionnaire.requirements
        for condition in requirement.conditions
    ]

    # Incorporar routing no debe modificar la evaluación
    # producida por el cuestionario.
    assert integrated_statuses == direct_statuses

    # En este escenario todavía falta información dependiente,
    # por lo que existen condiciones pendientes.
    assert any(
        status.value == "pending_information"
        for status in integrated_statuses
    )

    # El routing no autoriza verificación documental
    # ni evaluación normativa.
    assert all(
        condition.evidence_verified is False
        for requirement in result.report.requirements
        for condition in requirement.conditions
    )

    assert result.coverage.status == "not_established"