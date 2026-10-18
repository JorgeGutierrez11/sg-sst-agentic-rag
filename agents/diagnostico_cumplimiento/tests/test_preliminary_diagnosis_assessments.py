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

AFFILIATION_PRIMARY_QUESTION_IDS = [
    "q_health_affiliation",
    "q_pension_affiliation",
    "q_occupational_risk_affiliation",
]


def answer(question_id, value):
    return QuestionAnswer(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        question_id=question_id,
        raw_answer=value,
    )


def run_diagnosis(catalog_path, answers=None):
    return run_preliminary_diagnosis(
        profile=CompanyProfile(
            worker_count=8,
            risk_class=RiskClass.I,
        ),
        answers=answers or [],
        catalog_path=catalog_path,
    )


def get_affiliation_assessment(result):
    return next(
        assessment
        for assessment in result.assessments
        if assessment.requirement_id
        == AFFILIATION_REQUIREMENT_ID
    )


def test_integrated_result_contains_affiliation_assessment(catalog_path):
    result = run_diagnosis(catalog_path)

    assessment = get_affiliation_assessment(result)

    assert assessment.requirement_id == (
        AFFILIATION_REQUIREMENT_ID
    )

    assert assessment.status.value == (
        "insufficient_information"
    )

    assert assessment.evidence_verified is False

    assert assessment.requires_expert_validation is True

    # One assessment per requirement of the selected catalog.
    assert len(result.assessments) == 7


def test_all_affirmative_answers_are_only_declared_compliance(
    catalog,
    catalog_path,
):
    requirement = catalog.requirements[1]
    assert requirement.id == AFFILIATION_REQUIREMENT_ID

    question_ids = [question.id for question in requirement.questions]

    result = run_diagnosis(
        catalog_path,
        [answer(question_id, True) for question_id in question_ids],
    )

    assessment = get_affiliation_assessment(result)

    # Compliance is only "as declared": evidence is never verified and an
    # expert must still validate it.
    assert assessment.status.value == "complies_as_declared"
    assert assessment.supporting_question_ids == question_ids
    assert assessment.missing_information == []
    assert assessment.evidence_verified is False
    assert assessment.requires_expert_validation is True

    # La aplicación ya está determinada para este perfil,
    # pero eso no autoriza una conclusión de cumplimiento.
    assert assessment.applicability.status.value == "applicable"


def test_negative_answer_does_not_become_no_apply(catalog_path):
    result = run_diagnosis(
        catalog_path,
        [
            answer(question_id, False)
            for question_id in AFFILIATION_PRIMARY_QUESTION_IDS
        ],
    )

    assessment = get_affiliation_assessment(result)

    assert assessment.status.value == (
        "does_not_comply_as_declared"
    )

    assert assessment.status.value != "not_applicable"

    assert assessment.applicability.status.value == "applicable"

    assert "negativa" in assessment.explanation.lower()

    assert assessment.supporting_question_ids == (
        AFFILIATION_PRIMARY_QUESTION_IDS
    )

    # La respuesta negativa sí afecta el routing: los soportes
    # dependientes se omiten y no quedan como información pendiente.
    affiliation = next(
        requirement
        for requirement in result.questionnaire.requirements
        if requirement.requirement_id == AFFILIATION_REQUIREMENT_ID
    )

    assert "q_health_affiliation_support" in (
        affiliation.skipped_question_ids
    )
    assert "q_health_payment_support" in (
        affiliation.skipped_question_ids
    )
    assert assessment.missing_information == []


def test_assessment_is_serialized_with_full_traceability(catalog_path):
    result = run_diagnosis(
        catalog_path,
        [answer("q_health_affiliation", True)],
    )

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

    assert assessment["missing_information"]

    # Las capas principales deben coexistir en la misma salida.
    assert "questionnaire" in data
    assert "report" in data
    assert "coverage" in data
    assert "applicability" in data
    assert "routing" in data
