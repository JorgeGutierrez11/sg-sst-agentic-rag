import json

import pytest

from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.reporting.orientative_report import (
    build_orientative_report,
)
from agents.diagnostico_cumplimiento.questionnaire.questionnaire import (
    run_questionnaire,
)
from agents.diagnostico_cumplimiento.rules.assessment.generic_requirement_assessment import (
    assess_requirement_as_declared,
)

AFFILIATION_REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"


def build_questionnaire(catalog_path, answer_values=None):
    answers = [
        QuestionAnswer(
            requirement_id=AFFILIATION_REQUIREMENT_ID,
            question_id=question_id,
            raw_answer=value,
        )
        for question_id, value in (answer_values or {}).items()
    ]

    return run_questionnaire(
        profile=CompanyProfile(
            worker_count=8,
            risk_class=RiskClass.I,
        ),
        answers=answers,
        catalog_path=catalog_path,
    )


def get_affiliation_report(report):
    return next(
        requirement
        for requirement in report.requirements
        if requirement.requirement_id == AFFILIATION_REQUIREMENT_ID
    )


def test_report_identifies_negative_and_missing_answers(catalog_path):
    questionnaire = build_questionnaire(
        catalog_path,
        {
            "q_health_affiliation": True,
            "q_health_affiliation_support": False,
        },
    )

    report = build_orientative_report(questionnaire)

    assert report.catalog_version == "2.1"
    assert len(report.requirements) == 7

    affiliation = get_affiliation_report(report)

    assert any(
        "negativa" in finding.lower()
        and "soportes" in finding.lower()
        and "salud" in finding.lower()
        for finding in affiliation.findings
    )

    assert any(
        "falta información" in finding.lower()
        and "comprobantes" in finding.lower()
        and "salud" in finding.lower()
        for finding in affiliation.findings
    )

    # One suggested action per negative or unanswered active question.
    assert len(affiliation.suggested_actions) == 4


def test_affirmative_answers_do_not_establish_compliance(
    catalog,
    catalog_path,
):
    requirement = next(
        item
        for item in catalog.requirements
        if item.id == AFFILIATION_REQUIREMENT_ID
    )

    questionnaire = build_questionnaire(
        catalog_path,
        {question.id: True for question in requirement.questions},
    )

    assessments = [
        assess_requirement_as_declared(snapshot)
        for snapshot in questionnaire.requirements
    ]

    report = build_orientative_report(
        questionnaire,
        assessments=assessments,
    )

    affiliation = get_affiliation_report(report)

    assert affiliation.assessment_status.value == "complies_as_declared"
    assert affiliation.assessment_evidence_verified is False
    assert affiliation.requires_expert_validation is True
    assert any(
        "declaraciones" in finding.lower()
        for finding in affiliation.findings
    )

    assert all(
        question.interpretation_status is not None
        for question in affiliation.questions
    )


def test_report_is_serializable_to_json(catalog_path):
    questionnaire = build_questionnaire(
        catalog_path,
        {"q_health_affiliation_support": False},
    )

    report = build_orientative_report(questionnaire)
    data = json.loads(report.model_dump_json())

    assert data["catalog_version"] == "2.1"
    assert len(data["requirements"]) == 7

    affiliation = next(
        item
        for item in data["requirements"]
        if item["requirement_id"] == AFFILIATION_REQUIREMENT_ID
    )

    assert len(affiliation["questions"]) == 9
    assert {question["role"] for question in affiliation["questions"]} == {
        "primary",
        "evidence",
    }

    # Without assessments the report never claims verified evidence.
    assert all(
        requirement["assessment_evidence_verified"] is None
        for requirement in data["requirements"]
    )

    assert data["scope_note"]


def test_report_rejects_findings_for_another_requirement(catalog_path):
    questionnaire = build_questionnaire(catalog_path)

    incorrect_findings = questionnaire.declarative_findings[0].model_copy(
        update={"requirement_id": "another_requirement"}
    )

    incorrect_questionnaire = questionnaire.model_copy(
        update={"declarative_findings": [incorrect_findings]}
    )

    with pytest.raises(ValueError):
        build_orientative_report(incorrect_questionnaire)


def test_report_rejects_assessment_for_another_requirement(catalog_path):
    # v2.1 has no conditions; the equivalent consistency guard is that an
    # assessment must belong to a requirement of the questionnaire.
    questionnaire = build_questionnaire(catalog_path)

    assessment = assess_requirement_as_declared(
        questionnaire.requirements[0]
    )

    incorrect_assessment = assessment.model_copy(
        update={"requirement_id": "another_requirement"}
    )

    with pytest.raises(ValueError):
        build_orientative_report(
            questionnaire,
            assessments=[incorrect_assessment],
        )
