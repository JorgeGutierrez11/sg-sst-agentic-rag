import json

from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.preliminary_diagnosis import (
    run_preliminary_diagnosis,
)

AFFILIATION_REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"


def run_diagnosis(catalog_path, answers=None):
    return run_preliminary_diagnosis(
        profile=CompanyProfile(
            worker_count=8,
            risk_class=RiskClass.I,
        ),
        answers=answers or [],
        catalog_path=catalog_path,
    )


def answer(question_id, value):
    return QuestionAnswer(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        question_id=question_id,
        raw_answer=value,
    )


def test_integrated_result_contains_one_applicability_per_requirement(
    catalog_path,
):
    result = run_diagnosis(catalog_path)

    requirement_ids = [
        requirement.requirement_id
        for requirement in result.questionnaire.requirements
    ]

    applicability_ids = [
        decision.requirement_id
        for decision in result.applicability
    ]

    assert len(requirement_ids) == 7
    assert applicability_ids == requirement_ids


def test_selected_requirements_are_registered_as_applicable(catalog_path):
    result = run_diagnosis(catalog_path)

    assert all(
        decision.status.value == "applicable"
        for decision in result.applicability
    )

    # Every requirement of the fixture uses applicability mode "always".
    assert all(
        decision.rule_id == "catalog_requirement_always_applicable"
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


def test_always_applicable_requirements_have_no_screening_trigger(
    catalog_path,
):
    # The v2.1 flow no longer records the profile that activated the
    # selection: "always" requirements are not decided by any question.
    result = run_diagnosis(catalog_path)

    for decision in result.applicability:
        assert decision.triggered_by == []


def test_applicability_is_serialized_with_traceability(catalog_path):
    result = run_diagnosis(catalog_path)

    data = json.loads(result.model_dump_json())

    assert "applicability" in data
    assert len(data["applicability"]) == 7

    for decision in data["applicability"]:
        assert decision["status"] == "applicable"
        assert decision["rule_id"] == (
            "catalog_requirement_always_applicable"
        )
        assert decision["reason"]
        assert decision["normative_basis"]
        assert decision["triggered_by"] == []


def test_question_routing_does_not_change_requirement_applicability(
    catalog_path,
):
    without_answers = run_diagnosis(catalog_path)

    with_answers = run_diagnosis(
        catalog_path,
        [answer("q_health_affiliation", False)],
    )

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

    # In v2.1 the routing lives in each question's routing_state.
    affiliation = next(
        requirement
        for requirement in with_answers.questionnaire.requirements
        if requirement.requirement_id == AFFILIATION_REQUIREMENT_ID
    )
    routing_states = {
        question.question_id: question.routing_state.value
        for question in affiliation.questions
    }

    assert routing_states["q_health_affiliation_support"] == "skipped"

    affiliation_applicability = next(
        decision
        for decision in with_answers.applicability
        if decision.requirement_id == AFFILIATION_REQUIREMENT_ID
    )

    assert affiliation_applicability.status.value == "applicable"
