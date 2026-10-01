
import json
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.preliminary_diagnosis import (
    run_preliminary_diagnosis,
)
from agents.diagnostico_cumplimiento.rules.applicability import (
    OutOfScopeError,
)


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v2.json"
)


def build_profile(risk_class=RiskClass.I):
    return CompanyProfile(
        worker_count=8,
        risk_class=risk_class,
    )


def build_answer(question_id, raw_answer):
    requirement = load_catalog(CATALOG_PATH).requirements[0]

    return QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=raw_answer,
    )


def test_integrated_result_preserves_answers_and_findings():
    result = run_preliminary_diagnosis(
        profile=build_profile(),
        answers=[
            build_answer("q_health_affiliation", True),
            build_answer("q_health_affiliation_support", False),
        ],
        catalog_path=CATALOG_PATH,
    )

    questionnaire_requirement = result.questionnaire.requirements[0]
    report_requirement = result.report.requirements[0]

    assert (
        questionnaire_requirement.requirement_id
        == report_requirement.requirement_id
    )

    health_answers = questionnaire_requirement.conditions[0].questions

    assert health_answers[0].answer.raw_answer is True
    assert health_answers[1].answer.raw_answer is False
    assert health_answers[2].answer is None

    health_report = report_requirement.conditions[0]

    assert health_report.declaration_status.value == "incomplete"
    assert health_report.evidence_verified is False
    assert any(
        "negativamente" in finding.lower()
        for finding in health_report.findings
    )


def test_integrated_report_preserves_catalog_references():
    catalog = load_catalog(CATALOG_PATH)
    requirement = catalog.requirements[0]

    result = run_preliminary_diagnosis(
        profile=build_profile(),
        answers=[],
        catalog_path=CATALOG_PATH,
    )

    report_requirement = result.report.requirements[0]

    assert result.report.catalog_version == catalog.catalog_version
    assert report_requirement.source == requirement.source
    assert (
        report_requirement.criterion_official_text
        == requirement.criterion.official_text
    )
    assert (
        report_requirement.verification_method
        == requirement.criterion.verification_method
    )


def test_affirmative_answers_do_not_establish_compliance():
    requirement = load_catalog(CATALOG_PATH).requirements[0]

    answers = [
        build_answer(question.id, True)
        for question in requirement.questions
    ]

    result = run_preliminary_diagnosis(
        profile=build_profile(),
        answers=answers,
        catalog_path=CATALOG_PATH,
    )

    assert len(answers) == 9

    assert all(
        condition.evaluation.status.value == "not_evaluated"
        for condition in result.questionnaire.requirements[0].conditions
    )

    assert all(
        condition.evidence_verified is False
        for condition in result.report.requirements[0].conditions
    )

    data = json.loads(result.model_dump_json())

    assert "questionnaire" in data
    assert "report" in data


def test_integrated_execution_rejects_out_of_scope_profile():
    with pytest.raises(OutOfScopeError):
        run_preliminary_diagnosis(
            profile=build_profile(risk_class=RiskClass.II),
            answers=[],
            catalog_path=CATALOG_PATH,
        )
