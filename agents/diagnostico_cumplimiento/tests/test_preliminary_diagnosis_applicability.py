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


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v6.json"
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


def answer(question_id, value):
    return QuestionAnswer(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        question_id=question_id,
        raw_answer=value,
    )


def test_integrated_result_contains_one_applicability_per_requirement():
    result = run_diagnosis()

    requirement_ids = [
        requirement.requirement_id
        for requirement in result.questionnaire.requirements
    ]

    applicability_ids = [
        decision.requirement_id
        for decision in result.applicability
    ]

    assert len(requirement_ids) == 5
    assert applicability_ids == requirement_ids


def test_selected_requirements_are_registered_as_applicable():
    result = run_diagnosis()

    assert all(
        decision.status.value == "applicable"
        for decision in result.applicability
    )

    assert all(
        decision.rule_id == "catalog_profile_match"
        for decision in result.applicability
    )

    assert all(
        decision.normative_basis
        for decision in result.applicability
    )

    assert all(
        decision.missing_information == []
        for decision in result.applicability
    )


def test_applicability_records_profile_that_activated_selection():
    result = run_diagnosis()

    for decision in result.applicability:
        assert decision.triggered_by == [
            "worker_count=8",
            "risk_class=I",
        ]


def test_applicability_is_serialized_with_traceability():
    result = run_diagnosis()

    data = json.loads(result.model_dump_json())

    assert "applicability" in data
    assert len(data["applicability"]) == 5

    for decision in data["applicability"]:
        assert decision["status"] == "applicable"
        assert decision["rule_id"] == "catalog_profile_match"
        assert decision["reason"]
        assert decision["normative_basis"]
        assert decision["triggered_by"] == [
            "worker_count=8",
            "risk_class=I",
        ]


def test_question_routing_does_not_change_requirement_applicability():
    without_answers = run_diagnosis()

    with_answers = run_diagnosis([
        answer("q_health_affiliation", False),
    ])

    applicability_before = [
        decision.model_dump(mode="json")
        for decision in without_answers.applicability
    ]

    applicability_after = [
        decision.model_dump(mode="json")
        for decision in with_answers.applicability
    ]

    # Una respuesta puede modificar el flujo interno de preguntas,
    # pero no debe modificar por sí sola la aplicabilidad normativa
    # que ya fue determinada por el perfil y el catálogo.
    assert applicability_before == applicability_after

    routing = with_answers.routing[0]

    assert "q_health_affiliation_support" in (
        routing.omitted_questions
    )

    affiliation_applicability = next(
        decision
        for decision in with_answers.applicability
        if decision.requirement_id == AFFILIATION_REQUIREMENT_ID
    )

    assert affiliation_applicability.status.value == "applicable"