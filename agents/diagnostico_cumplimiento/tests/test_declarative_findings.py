
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.reporting.declarative_findings import (
    DeclarationFindingStatus,
    summarize_requirement_declarations,
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


def build_findings(
    overrides: dict[str, bool | str] | None = None,
    omitted: set[str] | None = None,
):
    """Ejecuta el cuestionario y genera sus hallazgos declarativos."""

    requirement = load_catalog(CATALOG_PATH).requirements[0]
    overrides = overrides or {}
    omitted = omitted or set()

    answers = [
        QuestionAnswer(
            requirement_id=requirement.id,
            question_id=question.id,
            raw_answer=overrides.get(question.id, True),
        )
        for question in requirement.questions
        if question.id not in omitted
    ]

    questionnaire = run_questionnaire(
        profile=CompanyProfile(
            worker_count=8,
            risk_class=RiskClass.I,
        ),
        answers=answers,
        catalog_path=CATALOG_PATH,
    )

    return (
        questionnaire.requirements[0],
        summarize_requirement_declarations(
            questionnaire.requirements[0]
        ),
    )


def test_all_affirmative_answers_are_only_declarations():
    requirement, findings = build_findings()

    assert len(findings.conditions) == 3

    for condition in findings.conditions:
        assert condition.status == (
            DeclarationFindingStatus.ALL_AFFIRMATIVE_DECLARED
        )
        assert condition.negative_question_ids == []
        assert condition.unanswered_question_ids == []
        assert condition.unresolved_question_ids == []
        assert condition.evidence_verified is False

    # El cuestionario tampoco establece cumplimiento normativo.
    assert all(
        condition.evaluation.status.value == "not_evaluated"
        for condition in requirement.conditions
    )


def test_negative_answer_identifies_the_correct_question():
    _, findings = build_findings(
        overrides={"q_health_affiliation_support": False}
    )

    health = findings.conditions[0]

    assert health.status == (
        DeclarationFindingStatus.HAS_NEGATIVE_DECLARATION
    )
    assert health.negative_question_ids == [
        "q_health_affiliation_support"
    ]
    assert health.evidence_verified is False

    assert all(
        condition.status
        == DeclarationFindingStatus.ALL_AFFIRMATIVE_DECLARED
        for condition in findings.conditions[1:]
    )


def test_multiple_negative_answers_are_preserved():
    _, findings = build_findings(
        overrides={
            "q_health_affiliation": False,
            "q_health_payment_support": False,
        }
    )

    health = findings.conditions[0]

    assert health.status == (
        DeclarationFindingStatus.HAS_NEGATIVE_DECLARATION
    )
    assert health.negative_question_ids == [
        "q_health_affiliation",
        "q_health_payment_support",
    ]


def test_missing_answer_identifies_incomplete_condition():
    _, findings = build_findings(
        omitted={"q_pension_payment_support"}
    )

    pension = findings.conditions[1]

    assert pension.status == DeclarationFindingStatus.INCOMPLETE
    assert pension.unanswered_question_ids == [
        "q_pension_payment_support"
    ]
    assert pension.unresolved_question_ids == []
    assert pension.evidence_verified is False


def test_negative_answer_is_preserved_when_information_is_missing():
    _, findings = build_findings(
        overrides={"q_health_affiliation_support": False},
        omitted={"q_health_payment_support"},
    )

    health = findings.conditions[0]

    assert health.status == DeclarationFindingStatus.INCOMPLETE
    assert health.negative_question_ids == [
        "q_health_affiliation_support"
    ]
    assert health.unanswered_question_ids == [
        "q_health_payment_support"
    ]


def test_uncertain_answer_requires_clarification():
    _, findings = build_findings(
        overrides={"q_pension_affiliation_support": "No sé"}
    )

    pension = findings.conditions[1]

    assert pension.status == (
        DeclarationFindingStatus.NEEDS_CLARIFICATION
    )
    assert pension.unresolved_question_ids == [
        "q_pension_affiliation_support"
    ]
    assert pension.evidence_verified is False


def test_unresolved_answer_does_not_hide_other_findings():
    _, findings = build_findings(
        overrides={
            "q_health_affiliation": False,
            "q_health_affiliation_support": "No sé",
        },
        omitted={"q_health_payment_support"},
    )

    health = findings.conditions[0]

    assert health.status == (
        DeclarationFindingStatus.NEEDS_CLARIFICATION
    )
    assert health.negative_question_ids == [
        "q_health_affiliation"
    ]
    assert health.unresolved_question_ids == [
        "q_health_affiliation_support"
    ]
    assert health.unanswered_question_ids == [
        "q_health_payment_support"
    ]


def test_findings_can_be_serialized_to_json():
    _, findings = build_findings(
        overrides={"q_health_affiliation_support": False}
    )

    data = findings.model_dump(mode="json")

    assert data["conditions"][0]["status"] == (
        "has_negative_declaration"
    )
    assert data["conditions"][0]["evidence_verified"] is False
    assert isinstance(findings.model_dump_json(), str)
