import json
from pathlib import Path
from unittest import result

from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.preliminary_diagnosis import (
    run_preliminary_diagnosis,
)
from agents.diagnostico_cumplimiento.rules.assessment.affiliation_declarative_assessment import (
    AFFILIATION_QUESTION_IDS,
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

def get_affiliation_assessment(result):
    return next(
        assessment
        for assessment in result.assessments
        if assessment.requirement_id
        == AFFILIATION_REQUIREMENT_ID
    )


def get_affiliation_routing(result):
    return next(
        routing
        for routing in result.routing
        if routing.requirement_id
        == AFFILIATION_REQUIREMENT_ID
    )

def test_integrated_result_contains_affiliation_assessment():
    result = run_diagnosis()

    assessment = get_affiliation_assessment(result)

    assert assessment.requirement_id == (
        AFFILIATION_REQUIREMENT_ID
    )

    assert assessment.status.value == (
        "insufficient_information"
    )

    assert assessment.evidence_verified is False

    assert assessment.requires_expert_validation is True


def test_all_affirmative_answers_remain_blocked():
    result = run_diagnosis([
        answer(question_id, True)
        for question_id in AFFILIATION_QUESTION_IDS
    ])

    assessment = get_affiliation_assessment(result)

    assert assessment.status.value == (
        "insufficient_information"
    )

    assert assessment.supporting_question_ids == (
        AFFILIATION_QUESTION_IDS
    )

    assert len(assessment.missing_information) == 1

    assert "validación" in (
        assessment.missing_information[0].lower()
    )

    # La aplicación ya está determinada para este perfil,
    # pero eso no autoriza una conclusión de cumplimiento.
    assert assessment.applicability.status.value == "applicable"


def test_negative_answer_does_not_become_no_apply():
    result = run_diagnosis([
        answer("q_health_affiliation", False),
    ])

    assessment = get_affiliation_assessment(result)

    assert assessment.status.value == (
        "insufficient_information"
    )

    assert assessment.status.value != "not_applicable"

    assert assessment.applicability.status.value == "applicable"

    assert "negativas" in assessment.explanation.lower()

    # La respuesta negativa sí afecta el routing.
    routing = result.routing[0]

    assert "q_health_affiliation_support" in (
        routing.omitted_questions
    )

    assert "q_health_payment_support" in (
        routing.omitted_questions
    )


def test_assessment_is_serialized_with_full_traceability():
    result = run_diagnosis([
        answer("q_health_affiliation", True),
    ])

    data = json.loads(result.model_dump_json())

    assert "assessments" in data


    assessment = next(
        item
        for item in data["assessments"]
        if item["requirement_id"]
        == AFFILIATION_REQUIREMENT_ID
    )

    assert assessment["requirement_id"] == (
        AFFILIATION_REQUIREMENT_ID
    )

    assert assessment["status"] == (
        "insufficient_information"
    )

    assert assessment["evidence_verified"] is False

    assert assessment["requires_expert_validation"] is True

    assert assessment["applicability"]["status"] == "applicable"

    assert assessment["supporting_question_ids"] == [
        "q_health_affiliation",
    ]

    # Las capas principales deben coexistir en la misma salida.
    assert "questionnaire" in data
    assert "report" in data
    assert "coverage" in data
    assert "applicability" in data
    assert "routing" in data