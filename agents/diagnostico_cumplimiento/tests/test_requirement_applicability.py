import pytest
from pydantic import ValidationError

from agents.diagnostico_cumplimiento.domain.requirement_applicability import (
    RequirementApplicabilityDecision,
    RequirementApplicabilityStatus,
)


def test_applicable_requires_normative_basis():
    decision = RequirementApplicabilityDecision(
        requirement_id="example_requirement",
        status=RequirementApplicabilityStatus.APPLICABLE,
        rule_id="profile_matches_scope",
        reason=(
            "El perfil empresarial satisface las condiciones "
            "de aplicabilidad de la regla."
        ),
        normative_basis="Resolución de ejemplo, artículo X.",
        triggered_by=[
            "worker_count=8",
            "risk_class=I",
        ],
    )

    assert decision.status.value == "applicable"
    assert decision.normative_basis
    assert decision.triggered_by == [
        "worker_count=8",
        "risk_class=I",
    ]
    assert decision.missing_information == []


def test_not_applicable_requires_normative_basis():
    decision = RequirementApplicabilityDecision(
        requirement_id="example_requirement",
        status=RequirementApplicabilityStatus.NOT_APPLICABLE,
        rule_id="documented_exception",
        reason=(
            "Una regla normativa permite excluir el requisito "
            "para el caso analizado."
        ),
        normative_basis="Fuente normativa de ejemplo.",
        triggered_by=[
            "example_condition=False",
        ],
    )

    assert decision.status.value == "not_applicable"
    assert decision.normative_basis
    assert decision.triggered_by


def test_definitive_applicability_without_normative_basis_is_rejected():
    for status in (
        RequirementApplicabilityStatus.APPLICABLE,
        RequirementApplicabilityStatus.NOT_APPLICABLE,
    ):
        with pytest.raises(ValidationError):
            RequirementApplicabilityDecision(
                requirement_id="example_requirement",
                status=status,
                rule_id="unsupported_rule",
                reason="Decisión sin fundamento normativo.",
            )


def test_undetermined_requires_missing_information():
    decision = RequirementApplicabilityDecision(
        requirement_id="example_requirement",
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

    assert decision.status.value == "undetermined"
    assert decision.normative_basis is None
    assert decision.missing_information == [
        "modalidad de vinculación",
    ]


def test_undetermined_without_missing_information_is_rejected():
    with pytest.raises(ValidationError):
        RequirementApplicabilityDecision(
            requirement_id="example_requirement",
            status=RequirementApplicabilityStatus.UNDETERMINED,
            rule_id="missing_context",
            reason="No existe información suficiente.",
        )