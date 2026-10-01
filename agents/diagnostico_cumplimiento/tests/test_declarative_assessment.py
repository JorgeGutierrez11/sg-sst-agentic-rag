import pytest
from pydantic import ValidationError

from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    DeclarativeAssessmentStatus,
    RequirementDeclarativeAssessment,
)
from agents.diagnostico_cumplimiento.domain.requirement_applicability import (
    RequirementApplicabilityDecision,
    RequirementApplicabilityStatus,
)


REQUIREMENT_ID = "example_requirement"


def applicable():
    return RequirementApplicabilityDecision(
        requirement_id=REQUIREMENT_ID,
        status=RequirementApplicabilityStatus.APPLICABLE,
        rule_id="profile_matches_scope",
        reason="El requisito aplica al perfil empresarial.",
        normative_basis="Fuente normativa de ejemplo.",
        triggered_by=[
            "worker_count=8",
            "risk_class=I",
        ],
    )


def not_applicable():
    return RequirementApplicabilityDecision(
        requirement_id=REQUIREMENT_ID,
        status=RequirementApplicabilityStatus.NOT_APPLICABLE,
        rule_id="documented_exception",
        reason=(
            "Existe una regla normativa que excluye "
            "el requisito para este caso."
        ),
        normative_basis="Fuente normativa de ejemplo.",
        triggered_by=[
            "example_condition=False",
        ],
    )


def undetermined():
    return RequirementApplicabilityDecision(
        requirement_id=REQUIREMENT_ID,
        status=RequirementApplicabilityStatus.UNDETERMINED,
        rule_id="missing_context",
        reason=(
            "No existe información suficiente para decidir "
            "la aplicabilidad."
        ),
        missing_information=[
            "modalidad de vinculación",
        ],
    )


def test_applicable_requirement_can_comply_as_declared():
    assessment = RequirementDeclarativeAssessment(
        requirement_id=REQUIREMENT_ID,
        status=DeclarativeAssessmentStatus.COMPLIES_AS_DECLARED,
        explanation=(
            "Las respuestas utilizadas por la regla fueron "
            "declaradas afirmativamente."
        ),
        applicability=applicable(),
        supporting_question_ids=[
            "q_example_1",
            "q_example_2",
        ],
    )

    assert assessment.status.value == "complies_as_declared"
    assert assessment.evidence_verified is False
    assert assessment.requires_expert_validation is True


def test_applicable_requirement_can_not_comply_as_declared():
    assessment = RequirementDeclarativeAssessment(
        requirement_id=REQUIREMENT_ID,
        status=(
            DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED
        ),
        explanation=(
            "Una respuesta relevante fue declarada negativamente."
        ),
        applicability=applicable(),
        supporting_question_ids=[
            "q_example_1",
        ],
    )

    assert assessment.status.value == (
        "does_not_comply_as_declared"
    )

    assert assessment.evidence_verified is False


def test_not_applicable_requires_matching_applicability():
    assessment = RequirementDeclarativeAssessment(
        requirement_id=REQUIREMENT_ID,
        status=DeclarativeAssessmentStatus.NOT_APPLICABLE,
        explanation=(
            "El requisito fue excluido mediante una regla "
            "de aplicabilidad fundamentada."
        ),
        applicability=not_applicable(),
    )

    assert assessment.status.value == "not_applicable"
    assert assessment.applicability.status.value == (
        "not_applicable"
    )


def test_applicable_requirement_cannot_be_marked_not_applicable():
    with pytest.raises(ValidationError):
        RequirementDeclarativeAssessment(
            requirement_id=REQUIREMENT_ID,
            status=DeclarativeAssessmentStatus.NOT_APPLICABLE,
            explanation="Intento incorrecto de exclusión.",
            applicability=applicable(),
        )


def test_undetermined_applicability_requires_insufficient_information():
    assessment = RequirementDeclarativeAssessment(
        requirement_id=REQUIREMENT_ID,
        status=(
            DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
        ),
        explanation=(
            "Falta información para resolver la aplicabilidad."
        ),
        applicability=undetermined(),
        missing_information=[
            "modalidad de vinculación",
        ],
    )

    assert assessment.status.value == "insufficient_information"

    assert assessment.missing_information == [
        "modalidad de vinculación",
    ]


def test_insufficient_information_requires_missing_information():
    with pytest.raises(ValidationError):
        RequirementDeclarativeAssessment(
            requirement_id=REQUIREMENT_ID,
            status=(
                DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            ),
            explanation="Falta información.",
            applicability=applicable(),
        )