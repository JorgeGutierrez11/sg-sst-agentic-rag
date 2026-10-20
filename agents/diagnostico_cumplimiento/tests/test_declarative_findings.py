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

AFFILIATION_REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"


def build_findings(
    catalog,
    catalog_path,
    overrides: dict[str, bool | str] | None = None,
    omitted: set[str] | None = None,
):
    """Ejecuta el cuestionario y genera sus hallazgos declarativos."""

    requirement = next(
        item
        for item in catalog.requirements
        if item.id == AFFILIATION_REQUIREMENT_ID
    )
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
        catalog_path=catalog_path,
    )

    snapshot = next(
        item
        for item in questionnaire.requirements
        if item.requirement_id == requirement.id
    )

    return (
        snapshot,
        summarize_requirement_declarations(snapshot),
    )


def test_all_affirmative_answers_are_only_declarations(
    catalog,
    catalog_path,
):
    requirement, findings = build_findings(catalog, catalog_path)

    assert findings.requirement_id == AFFILIATION_REQUIREMENT_ID
    assert findings.status == (
        DeclarationFindingStatus.ALL_AFFIRMATIVE_DECLARED
    )
    assert findings.negative_question_ids == []
    assert findings.unanswered_question_ids == []
    assert findings.unresolved_question_ids == []
    assert findings.skipped_question_ids == []
    assert findings.blocked_question_ids == []
    assert findings.evidence_verified is False

    # All nine questions were active and declared.
    assert len(requirement.active_question_ids) == 9


def test_negative_answer_identifies_the_correct_question(
    catalog,
    catalog_path,
):
    _, findings = build_findings(
        catalog,
        catalog_path,
        overrides={"q_health_affiliation_support": False},
    )

    assert findings.status == (
        DeclarationFindingStatus.HAS_NEGATIVE_DECLARATION
    )
    assert findings.negative_question_ids == [
        "q_health_affiliation_support"
    ]
    assert findings.evidence_verified is False


def test_negative_primary_answer_skips_dependent_questions(
    catalog,
    catalog_path,
):
    # Dependent questions omitted by routing are neither pending nor
    # negative: only the negative primary answer is reported.
    _, findings = build_findings(
        catalog,
        catalog_path,
        overrides={"q_health_affiliation": False},
        omitted={
            "q_health_affiliation_support",
            "q_health_payment_support",
        },
    )

    assert findings.status == (
        DeclarationFindingStatus.HAS_NEGATIVE_DECLARATION
    )
    assert findings.negative_question_ids == ["q_health_affiliation"]
    assert findings.unanswered_question_ids == []
    assert findings.skipped_question_ids == [
        "q_health_affiliation_support",
        "q_health_payment_support",
    ]


def test_multiple_negative_answers_are_preserved(catalog, catalog_path):
    _, findings = build_findings(
        catalog,
        catalog_path,
        overrides={
            "q_health_affiliation_support": False,
            "q_pension_payment_support": False,
        },
    )

    assert findings.status == (
        DeclarationFindingStatus.HAS_NEGATIVE_DECLARATION
    )
    assert findings.negative_question_ids == [
        "q_health_affiliation_support",
        "q_pension_payment_support",
    ]


def test_missing_answer_identifies_incomplete_requirement(
    catalog,
    catalog_path,
):
    _, findings = build_findings(
        catalog,
        catalog_path,
        omitted={"q_pension_payment_support"},
    )

    assert findings.status == DeclarationFindingStatus.INCOMPLETE
    assert findings.unanswered_question_ids == [
        "q_pension_payment_support"
    ]
    assert findings.unresolved_question_ids == []
    assert findings.evidence_verified is False


def test_negative_answer_is_preserved_when_information_is_missing(
    catalog,
    catalog_path,
):
    _, findings = build_findings(
        catalog,
        catalog_path,
        overrides={"q_health_affiliation_support": False},
        omitted={"q_health_payment_support"},
    )

    assert findings.status == DeclarationFindingStatus.INCOMPLETE
    assert findings.negative_question_ids == [
        "q_health_affiliation_support"
    ]
    assert findings.unanswered_question_ids == [
        "q_health_payment_support"
    ]


def test_uncertain_answer_requires_clarification(catalog, catalog_path):
    _, findings = build_findings(
        catalog,
        catalog_path,
        overrides={"q_pension_affiliation_support": "No sé"},
    )

    assert findings.status == (
        DeclarationFindingStatus.NEEDS_CLARIFICATION
    )
    assert findings.unresolved_question_ids == [
        "q_pension_affiliation_support"
    ]
    assert findings.evidence_verified is False


def test_unresolved_answer_does_not_hide_other_findings(
    catalog,
    catalog_path,
):
    _, findings = build_findings(
        catalog,
        catalog_path,
        overrides={
            "q_pension_affiliation_support": False,
            "q_health_affiliation_support": "No sé",
        },
        omitted={"q_health_payment_support"},
    )

    assert findings.status == (
        DeclarationFindingStatus.NEEDS_CLARIFICATION
    )
    assert findings.negative_question_ids == [
        "q_pension_affiliation_support"
    ]
    assert findings.unresolved_question_ids == [
        "q_health_affiliation_support"
    ]
    assert findings.unanswered_question_ids == [
        "q_health_payment_support"
    ]


def test_findings_can_be_serialized_to_json(catalog, catalog_path):
    _, findings = build_findings(
        catalog,
        catalog_path,
        overrides={"q_health_affiliation_support": False},
    )

    data = findings.model_dump(mode="json")

    assert data["requirement_id"] == AFFILIATION_REQUIREMENT_ID
    assert data["status"] == "has_negative_declaration"
    assert data["negative_question_ids"] == [
        "q_health_affiliation_support"
    ]
    assert data["evidence_verified"] is False
    assert isinstance(findings.model_dump_json(), str)
