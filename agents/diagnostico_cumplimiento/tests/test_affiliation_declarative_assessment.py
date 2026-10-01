import pytest

from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.requirement_applicability import (
    RequirementApplicabilityDecision,
    RequirementApplicabilityStatus,
)
from agents.diagnostico_cumplimiento.rules.assessment.affiliation_declarative_assessment import (
    AFFILIATION_QUESTION_IDS,
    assess_affiliation_as_declared,
)
from agents.diagnostico_cumplimiento.rules.routing.affiliation_question_routing import (
    AFFILIATION_REQUIREMENT_ID,
)


def applicable():
    return RequirementApplicabilityDecision(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        status=RequirementApplicabilityStatus.APPLICABLE,
        rule_id="catalog_profile_match",
        reason=(
            "El requisito fue seleccionado para el perfil empresarial."
        ),
        normative_basis="Resolución 0312 de 2019, artículo 3.",
        triggered_by=[
            "worker_count=8",
            "risk_class=I",
        ],
    )


def not_applicable():
    return RequirementApplicabilityDecision(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        status=RequirementApplicabilityStatus.NOT_APPLICABLE,
        rule_id="documented_exception",
        reason=(
            "Una regla normativa documentada excluye el requisito "
            "para este caso."
        ),
        normative_basis="Fuente normativa de prueba.",
        triggered_by=[
            "documented_exception=True",
        ],
    )


def undetermined():
    return RequirementApplicabilityDecision(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        status=RequirementApplicabilityStatus.UNDETERMINED,
        rule_id="missing_context",
        reason=(
            "La información disponible no permite determinar "
            "la aplicabilidad."
        ),
        missing_information=[
            "modalidad de vinculación",
        ],
    )


def answer(question_id, value):
    return QuestionAnswer(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        question_id=question_id,
        raw_answer=value,
    )


def test_without_answers_returns_insufficient_information():
    assessment = assess_affiliation_as_declared(
        answers=[],
        applicability=applicable(),
    )

    assert assessment.status.value == "insufficient_information"

    assert assessment.supporting_question_ids == []

    # Solo las tres preguntas iniciales están activas.
    # Las seis preguntas dependientes todavía están omitidas por routing.
    # Se añade además el bloqueo por validación experta.
    assert len(assessment.missing_information) == 4

    for question_id in [
        "q_health_affiliation",
        "q_pension_affiliation",
        "q_occupational_risk_affiliation",
    ]:
        assert any(
            question_id in item
            for item in assessment.missing_information
        )

    for question_id in [
        "q_health_affiliation_support",
        "q_health_payment_support",
        "q_pension_affiliation_support",
        "q_pension_payment_support",
        "q_occupational_risk_affiliation_support",
        "q_occupational_risk_payment_support",
    ]:
        assert not any(
            question_id in item
            for item in assessment.missing_information
        )

    assert assessment.evidence_verified is False
    assert assessment.requires_expert_validation is True


def test_all_affirmative_answers_do_not_yet_establish_compliance():
    answers = [
        answer(question_id, True)
        for question_id in AFFILIATION_QUESTION_IDS
    ]

    assessment = assess_affiliation_as_declared(
        answers=answers,
        applicability=applicable(),
    )

    assert assessment.status.value == "insufficient_information"

    assert assessment.supporting_question_ids == (
        AFFILIATION_QUESTION_IDS
    )

    assert len(assessment.missing_information) == 1

    assert "validación" in (
        assessment.missing_information[0].lower()
    )

    assert "draft" in assessment.explanation.lower()
    assert "validada" in assessment.explanation.lower()

    assert assessment.evidence_verified is False


def test_negative_declaration_is_preserved_without_final_conclusion():
    assessment = assess_affiliation_as_declared(
        answers=[
            answer("q_health_affiliation", False),
        ],
        applicability=applicable(),
    )

    assert assessment.status.value == "insufficient_information"

    assert assessment.supporting_question_ids == [
        "q_health_affiliation",
    ]

    assert "negativas" in assessment.explanation.lower()

    # Todavía no se transforma automáticamente una respuesta
    # negativa en DOES_NOT_COMPLY_AS_DECLARED.
    assert assessment.status.value != (
        "does_not_comply_as_declared"
    )


def test_not_applicable_comes_only_from_applicability_decision():
    assessment = assess_affiliation_as_declared(
        answers=[],
        applicability=not_applicable(),
    )

    assert assessment.status.value == "not_applicable"

    assert assessment.applicability.status.value == (
        "not_applicable"
    )

    assert assessment.evidence_verified is False


def test_undetermined_applicability_returns_insufficient_information():
    assessment = assess_affiliation_as_declared(
        answers=[],
        applicability=undetermined(),
    )

    assert assessment.status.value == "insufficient_information"

    assert assessment.missing_information == [
        "modalidad de vinculación",
    ]

    assert assessment.applicability.status.value == "undetermined"


def test_unknown_affiliation_question_is_rejected():
    with pytest.raises(ValueError):
        assess_affiliation_as_declared(
            answers=[
                answer(
                    "q_unknown_affiliation_question",
                    True,
                ),
            ],
            applicability=applicable(),
        )