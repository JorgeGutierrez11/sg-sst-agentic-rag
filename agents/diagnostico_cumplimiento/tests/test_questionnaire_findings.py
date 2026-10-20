import json
from pathlib import Path

from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.questionnaire.questionnaire import run_questionnaire


REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"
TRAINING_REQUIREMENT_ID = "res0312_art3_capacitacion_1_10"


def run_pilot(answers, catalog_path):
    return run_questionnaire(
        profile=CompanyProfile(
            worker_count=8,
            risk_class=RiskClass.I,
        ),
        answers=answers,
        catalog_path=catalog_path,
    )


def answer(question_id, value, requirement_id=REQUIREMENT_ID):
    return QuestionAnswer(
        requirement_id=requirement_id,
        question_id=question_id,
        raw_answer=value,
    )


def find_by_requirement(items, requirement_id):
    return next(
        item for item in items if item.requirement_id == requirement_id
    )


def test_json_preserves_answers_and_negative_findings(catalog_path):
    result = run_pilot(
        [
            answer("q_health_affiliation", True),
            answer("q_health_affiliation_support", False),
        ],
        catalog_path,
    )

    data = json.loads(result.model_dump_json())

    requirement = next(
        item
        for item in data["requirements"]
        if item["requirement_id"] == REQUIREMENT_ID
    )
    findings = next(
        item
        for item in data["declarative_findings"]
        if item["requirement_id"] == REQUIREMENT_ID
    )

    questions = {
        question["question_id"]: question
        for question in requirement["questions"]
    }

    assert questions["q_health_affiliation"]["answer"]["raw_answer"] is True
    assert (
        questions["q_health_affiliation_support"]["answer"]["raw_answer"]
        is False
    )
    assert questions["q_health_payment_support"]["answer"] is None

    assert findings["status"] == "incomplete"
    assert findings["negative_question_ids"] == [
        "q_health_affiliation_support"
    ]
    assert "q_health_payment_support" in findings["unanswered_question_ids"]
    assert findings["evidence_verified"] is False


def test_all_affirmative_answers_do_not_establish_compliance(
    catalog,
    catalog_path,
):
    requirement = next(
        item for item in catalog.requirements if item.id == REQUIREMENT_ID
    )

    answers = [
        answer(question.id, True)
        for question in requirement.questions
    ]

    result = run_pilot(answers, catalog_path)

    snapshot = find_by_requirement(result.requirements, REQUIREMENT_ID)
    findings = find_by_requirement(
        result.declarative_findings,
        REQUIREMENT_ID,
    )

    assert snapshot.collection_status.value == "answers_interpreted"

    assert findings.status.value == "all_affirmative_declared"
    assert findings.evidence_verified is False
    assert findings.negative_question_ids == []


def test_unanswered_questionnaire_contains_pending_findings(catalog_path):
    result = run_pilot([], catalog_path)

    snapshot = find_by_requirement(result.requirements, REQUIREMENT_ID)

    assert snapshot.collection_status.value == "not_started"

    for finding in result.declarative_findings:
        assert finding.status.value == "incomplete"
        assert finding.negative_question_ids == []
        assert finding.evidence_verified is False

    findings = find_by_requirement(
        result.declarative_findings,
        REQUIREMENT_ID,
    )

    # Only the three primary questions are askable before any answer;
    # evidence questions stay blocked behind them.
    assert findings.unanswered_question_ids == [
        "q_health_affiliation",
        "q_pension_affiliation",
        "q_occupational_risk_affiliation",
    ]
    assert len(findings.blocked_question_ids) == 6


def test_findings_match_their_requirement_with_multiple_requirements(
    catalog_path: Path,
):
    """
    Checks that answers and findings of different requirements are
    not mixed up.
    """

    result = run_pilot(
        [
            answer("q_health_affiliation", True),
            answer(
                "q_training_preparation",
                False,
                requirement_id=TRAINING_REQUIREMENT_ID,
            ),
        ],
        catalog_path,
    )

    assert len(result.requirements) == len(result.declarative_findings)

    for requirement, findings in zip(
        result.requirements,
        result.declarative_findings,
        strict=True,
    ):
        assert findings.requirement_id == requirement.requirement_id

    first = find_by_requirement(
        result.declarative_findings,
        REQUIREMENT_ID,
    )
    second = find_by_requirement(
        result.declarative_findings,
        TRAINING_REQUIREMENT_ID,
    )

    assert first.negative_question_ids == []
    assert second.negative_question_ids == ["q_training_preparation"]
    assert second.status.value == "has_negative_declaration"
