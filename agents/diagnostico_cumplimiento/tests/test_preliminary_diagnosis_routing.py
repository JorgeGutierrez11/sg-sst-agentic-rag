import json

from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.preliminary_diagnosis import (
    run_preliminary_diagnosis,
)
from agents.diagnostico_cumplimiento.questionnaire.questionnaire import (
    run_questionnaire,
)

AFFILIATION_REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"

# In v2.1 the routing is not a separate result list: it lives in each
# question's ``routing_state`` inside the RequirementSnapshot.


def answer(question_id, value):
    return QuestionAnswer(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        question_id=question_id,
        raw_answer=value,
    )


def build_profile():
    return CompanyProfile(
        worker_count=8,
        risk_class=RiskClass.I,
    )


def run_diagnosis(catalog_path, answers=None):
    return run_preliminary_diagnosis(
        profile=build_profile(),
        answers=answers or [],
        catalog_path=catalog_path,
    )


def get_affiliation_requirement(result):
    return next(
        requirement
        for requirement in result.questionnaire.requirements
        if requirement.requirement_id == AFFILIATION_REQUIREMENT_ID
    )


def question_ids_in_state(requirement, state):
    return [
        question.question_id
        for question in requirement.questions
        if question.routing_state.value == state
    ]


def test_integrated_result_contains_affiliation_routing(catalog_path):
    result = run_diagnosis(catalog_path)

    requirement = get_affiliation_requirement(result)

    assert question_ids_in_state(requirement, "active") == [
        "q_health_affiliation",
        "q_pension_affiliation",
        "q_occupational_risk_affiliation",
    ]

    assert [
        question.question_id
        for question in requirement.questions
        if question.answer is not None
    ] == []

    # Dependent questions wait for their (still unanswered) parent.
    assert len(question_ids_in_state(requirement, "blocked")) == 6
    assert question_ids_in_state(requirement, "skipped") == []

    # The legacy top-level routing list is intentionally empty.
    assert result.routing == []


def test_integrated_routing_preserves_mixed_branches(catalog_path):
    result = run_diagnosis(
        catalog_path,
        [
            answer("q_health_affiliation", True),
            answer("q_pension_affiliation", False),
        ],
    )

    requirement = get_affiliation_requirement(result)

    assert [
        question.question_id
        for question in requirement.questions
        if question.answer is not None
    ] == [
        "q_health_affiliation",
        "q_pension_affiliation",
    ]

    assert question_ids_in_state(requirement, "active") == [
        "q_health_affiliation",
        "q_health_affiliation_support",
        "q_health_payment_support",
        "q_pension_affiliation",
        "q_occupational_risk_affiliation",
    ]

    assert question_ids_in_state(requirement, "skipped") == [
        "q_pension_affiliation_support",
        "q_pension_payment_support",
    ]

    assert question_ids_in_state(requirement, "blocked") == [
        "q_occupational_risk_affiliation_support",
        "q_occupational_risk_payment_support",
    ]


def test_routing_is_serialized_with_its_reasons(catalog_path):
    result = run_diagnosis(
        catalog_path,
        [answer("q_health_affiliation", False)],
    )

    data = json.loads(result.model_dump_json())

    requirement = next(
        item
        for item in data["questionnaire"]["requirements"]
        if item["requirement_id"] == AFFILIATION_REQUIREMENT_ID
    )

    support = next(
        question
        for question in requirement["questions"]
        if question["question_id"] == "q_health_affiliation_support"
    )

    assert support["routing_state"] == "skipped"
    assert support["depends_on"] == {
        "question_id": "q_health_affiliation",
        "value": True,
    }
    assert "q_health_affiliation_support" in (
        requirement["skipped_question_ids"]
    )


def test_routing_does_not_change_normative_evaluation(catalog_path):
    answers = [
        answer("q_health_affiliation", True),
        answer("q_pension_affiliation", True),
        answer("q_occupational_risk_affiliation", True),
    ]

    result = run_diagnosis(catalog_path, answers)

    direct_questionnaire = run_questionnaire(
        profile=build_profile(),
        answers=answers,
        catalog_path=catalog_path,
    )

    # Incorporar routing no debe modificar lo producido por el
    # cuestionario.
    assert result.questionnaire.model_dump(mode="json") == (
        direct_questionnaire.model_dump(mode="json")
    )

    # En este escenario todavía falta información dependiente,
    # por lo que existen requisitos con recolección en progreso.
    affiliation = get_affiliation_requirement(result)

    assert affiliation.collection_status.value == "in_progress"
    assert len(affiliation.unanswered_question_ids) == 6

    # El routing no autoriza verificación documental
    # ni evaluación normativa.
    assert all(
        requirement.assessment_evidence_verified is not True
        for requirement in result.report.requirements
    )

    assert all(
        assessment.evidence_verified is False
        for assessment in result.assessments
    )

    assert result.coverage.status == "selected_package"
