from agents.diagnostico_cumplimiento.domain.enums import (
    AssessmentStatus,
    QuestionType,
)

import pytest
from pydantic import ValidationError

from agents.diagnostico_cumplimiento.domain.enums import (
    AssessmentStatus,
    QuestionType,
)
from agents.diagnostico_cumplimiento.domain.models import (
    ApplicabilityRule,
    CompanyProfile,
    NormativeSource,
)

def test_assessment_status_values() -> None:
    assert AssessmentStatus.DECLARED_COMPLIANT == "declared_compliant"
    assert AssessmentStatus.DECLARED_NON_COMPLIANT == "declared_non_compliant"
    assert (
        AssessmentStatus.INSUFFICIENT_INFORMATION
        == "insufficient_information"
    )
    assert AssessmentStatus.NOT_APPLICABLE == "not_applicable"


def test_question_type_values() -> None:
    assert QuestionType.BOOLEAN == "boolean"
    assert QuestionType.INTEGER == "integer"
    assert QuestionType.TEXT == "text"
    assert QuestionType.SINGLE_CHOICE == "single_choice"
    assert QuestionType.MULTIPLE_CHOICE == "multiple_choice"

def test_company_profile_accepts_supported_company() -> None:
    profile = CompanyProfile(
        worker_count=8,
        risk_class="I",
        economic_activity="Mantenimiento y reparación de motocicletas",
        ciiu_code="4542",
    )

    assert profile.worker_count == 8
    assert profile.risk_class == "I"
    assert profile.economic_activity == (
        "Mantenimiento y reparación de motocicletas"
    )
    assert profile.ciiu_code == "4542"


def test_company_profile_rejects_zero_workers() -> None:
    with pytest.raises(ValidationError):
        CompanyProfile(
            worker_count=0,
            risk_class="I",
        )


def test_company_profile_rejects_unsupported_risk_class() -> None:
    with pytest.raises(ValidationError):
        CompanyProfile(
            worker_count=8,
            risk_class="II",
        )


def test_normative_source() -> None:
    source = NormativeSource(
        regulation="Resolución 0312 de 2019",
        article="Artículo 3",
        official_url=(
            "https://www.fondoriesgoslaborales.gov.co/"
            "wp-content/uploads/2018/09/"
            "RESOLUCION-0312-DEL-2019.pdf"
        ),
    )

    assert source.regulation == "Resolución 0312 de 2019"
    assert source.article == "Artículo 3"


def test_applicability_rule_with_worker_range() -> None:
    rule = ApplicabilityRule(
        risk_classes=["I"],
        worker_count_min=1,
        worker_count_max=10,
    )

    assert rule.worker_count_min == 1
    assert rule.worker_count_max == 10


def test_applicability_rule_without_upper_limit() -> None:
    rule = ApplicabilityRule(
        risk_classes=["I"],
        worker_count_min=51,
        worker_count_max=None,
    )

    assert rule.worker_count_min == 51
    assert rule.worker_count_max is None

def test_applicability_rule_rejects_invalid_worker_range() -> None:
    with pytest.raises(ValidationError):
        ApplicabilityRule(
            risk_classes=["I"],
            worker_count_min=50,
            worker_count_max=10,
        )
