
import json
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.reporting.orientative_report import (
    build_orientative_report,
)
from agents.diagnostico_cumplimiento.questionnaire.questionnaire import (
    run_questionnaire,
)


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v2.json"
)


def build_questionnaire(answer_values=None):
    requirement = load_catalog(CATALOG_PATH).requirements[0]

    answers = [
        QuestionAnswer(
            requirement_id=requirement.id,
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
        catalog_path=CATALOG_PATH,
    )


def test_report_identifies_negative_and_missing_answers():
    questionnaire = build_questionnaire(
        {
            "q_health_affiliation": True,
            "q_health_affiliation_support": False,
        }
    )

    report = build_orientative_report(questionnaire)

    assert report.catalog_version == "res0312-piloto-v2"
    assert len(report.requirements) == 1

    health = report.requirements[0].conditions[0]

    assert health.condition_id == "health_affiliation"
    assert health.declaration_status.value == "incomplete"
    assert health.evidence_verified is False

    assert any(
        "soportes" in finding.lower()
        and "negativamente" in finding.lower()
        for finding in health.findings
    )

    assert any(
        "comprobantes" in finding.lower()
        and "falta responder" in finding.lower()
        for finding in health.findings
    )

    assert len(health.suggested_actions) == 2


def test_affirmative_answers_do_not_establish_compliance():
    requirement = load_catalog(CATALOG_PATH).requirements[0]

    questionnaire = build_questionnaire(
        {
            question.id: True
            for question in requirement.questions
        }
    )

    report = build_orientative_report(questionnaire)

    for condition in report.requirements[0].conditions:
        assert condition.declaration_status.value == (
            "all_affirmative_declared"
        )
        assert condition.evidence_verified is False
        assert any(
            "declaraciones" in finding.lower()
            for finding in condition.findings
        )

    assert all(
        condition.evaluation.status.value == "not_evaluated"
        for condition in questionnaire.requirements[0].conditions
    )


def test_report_is_serializable_to_json():
    questionnaire = build_questionnaire(
        {"q_health_affiliation_support": False}
    )

    report = build_orientative_report(questionnaire)
    data = json.loads(report.model_dump_json())

    assert data["catalog_version"] == "res0312-piloto-v2"
    assert len(data["requirements"]) == 1
    assert len(data["requirements"][0]["conditions"]) == 3

    assert all(
        condition["evidence_verified"] is False
        for condition in data["requirements"][0]["conditions"]
    )

    assert data["scope_note"]


def test_report_rejects_findings_for_another_requirement():
    questionnaire = build_questionnaire()

    incorrect_findings = questionnaire.declarative_findings[0].model_copy(
        update={"requirement_id": "another_requirement"}
    )

    incorrect_questionnaire = questionnaire.model_copy(
        update={"declarative_findings": [incorrect_findings]}
    )

    with pytest.raises(ValueError):
        build_orientative_report(incorrect_questionnaire)


def test_report_rejects_findings_for_another_condition():
    questionnaire = build_questionnaire()

    original_findings = questionnaire.declarative_findings[0]

    incorrect_condition = original_findings.conditions[0].model_copy(
        update={"condition_id": "another_condition"}
    )

    incorrect_findings = original_findings.model_copy(
        update={
            "conditions": [
                incorrect_condition,
                *original_findings.conditions[1:],
            ]
        }
    )

    incorrect_questionnaire = questionnaire.model_copy(
        update={"declarative_findings": [incorrect_findings]}
    )

    with pytest.raises(ValueError):
        build_orientative_report(incorrect_questionnaire)
