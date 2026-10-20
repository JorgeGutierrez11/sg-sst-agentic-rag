import json

import pytest

from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.preliminary_diagnosis import (
    run_preliminary_diagnosis,
)
from agents.diagnostico_cumplimiento.rules.applicability import (
    OutOfScopeError,
)


def build_profile(risk_class=RiskClass.I):
    return CompanyProfile(
        worker_count=8,
        risk_class=risk_class,
    )


def get_requirement(catalog, index=1):
    # Index 1 is the affiliation requirement of the frozen catalog.
    return catalog.requirements[index]


def build_answer(requirement, question_id, raw_answer):
    return QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=raw_answer,
    )


def find_by_requirement(items, requirement_id):
    return next(
        item for item in items if item.requirement_id == requirement_id
    )


def test_integrated_result_preserves_answers_and_findings(
    catalog,
    catalog_path,
):
    requirement = get_requirement(catalog)

    result = run_preliminary_diagnosis(
        profile=build_profile(),
        answers=[
            build_answer(requirement, "q_health_affiliation", True),
            build_answer(
                requirement, "q_health_affiliation_support", False
            ),
        ],
        catalog_path=catalog_path,
    )

    questionnaire_requirement = find_by_requirement(
        result.questionnaire.requirements, requirement.id
    )
    report_requirement = find_by_requirement(
        result.report.requirements, requirement.id
    )

    questions = {
        question.question_id: question
        for question in questionnaire_requirement.questions
    }

    assert questions["q_health_affiliation"].answer.raw_answer is True
    assert (
        questions["q_health_affiliation_support"].answer.raw_answer
        is False
    )
    assert questions["q_health_payment_support"].answer is None

    assert report_requirement.assessment_evidence_verified is False
    assert report_requirement.assessment_status.value == (
        "insufficient_information"
    )
    assert any(
        "negativa" in finding.lower()
        for finding in report_requirement.findings
    )


def test_integrated_report_preserves_catalog_references(
    catalog,
    catalog_path,
):
    requirement = get_requirement(catalog)

    result = run_preliminary_diagnosis(
        profile=build_profile(),
        answers=[],
        catalog_path=catalog_path,
    )

    report_requirement = find_by_requirement(
        result.report.requirements, requirement.id
    )

    assert result.report.catalog_id == catalog.catalog_id
    assert result.report.catalog_version == catalog.catalog_version
    assert report_requirement.source == requirement.source
    assert (
        report_requirement.official_criterion
        == requirement.official_criterion
    )
    assert (
        report_requirement.official_verification_method
        == requirement.official_verification_method
    )


def test_affirmative_answers_do_not_establish_compliance(
    catalog,
    catalog_path,
):
    requirement = get_requirement(catalog)

    answers = [
        build_answer(requirement, question.id, True)
        for question in requirement.questions
    ]

    result = run_preliminary_diagnosis(
        profile=build_profile(),
        answers=answers,
        catalog_path=catalog_path,
    )

    assert len(answers) == 9

    report_requirement = find_by_requirement(
        result.report.requirements, requirement.id
    )

    # Declared compliance never means verified evidence.
    assert report_requirement.assessment_status.value == (
        "complies_as_declared"
    )
    assert report_requirement.assessment_evidence_verified is False
    assert report_requirement.requires_expert_validation is True

    assert all(
        assessment.evidence_verified is False
        for assessment in result.assessments
    )

    data = json.loads(result.model_dump_json())

    assert "questionnaire" in data
    assert "report" in data


def test_integrated_execution_rejects_out_of_scope_profile(catalog_path):
    with pytest.raises(OutOfScopeError):
        run_preliminary_diagnosis(
            profile=build_profile(risk_class=RiskClass.II),
            answers=[],
            catalog_path=catalog_path,
        )
