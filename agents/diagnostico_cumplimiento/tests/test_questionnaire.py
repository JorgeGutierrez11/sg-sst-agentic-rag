import json
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.questionnaire.answer_collection import (
    DuplicateAnswerError,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_validation import (
    AnswerReferenceError,
)
from agents.diagnostico_cumplimiento.rules.applicability import (
    OutOfScopeError,
)
from agents.diagnostico_cumplimiento.questionnaire.questionnaire import (
    run_questionnaire,
)


REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"
TRAINING_REQUIREMENT_ID = "res0312_art3_capacitacion_1_10"


def build_profile(
    worker_count: int = 8,
    risk_class: RiskClass = RiskClass.I,
) -> CompanyProfile:
    return CompanyProfile(
        worker_count=worker_count,
        risk_class=risk_class,
        economic_activity="Actividades administrativas de oficina",
    )


def build_answer(
    question_id: str,
    raw_answer: bool | str,
    requirement_id: str = REQUIREMENT_ID,
) -> QuestionAnswer:
    return QuestionAnswer(
        requirement_id=requirement_id,
        question_id=question_id,
        raw_answer=raw_answer,
    )


def get_snapshot(result, requirement_id: str = REQUIREMENT_ID):
    return next(
        requirement
        for requirement in result.requirements
        if requirement.requirement_id == requirement_id
    )


def test_runs_complete_questionnaire_with_partial_answers(
    catalog_path: Path,
) -> None:
    answers = [
        build_answer("q_health_affiliation", "Sí"),
        build_answer("q_pension_affiliation", "No sé"),
    ]

    result = run_questionnaire(
        profile=build_profile(),
        answers=answers,
        catalog_path=catalog_path,
    )

    assert result.catalog_id == "res0312_riesgo_i_1_10_general"
    assert result.catalog_version == "2.1"
    assert result.company_profile.worker_count == 8

    # The catalog holds several requirements; all of them are selected.
    assert len(result.requirements) == 7
    assert len(result.declarative_findings) == 7

    requirement = get_snapshot(result)

    assert requirement.collection_status.value == "needs_resolution"
    assert requirement.unresolved_question_ids == ["q_pension_affiliation"]

    questions = {
        question.question_id: question
        for question in requirement.questions
    }

    assert questions["q_health_affiliation"].answer.raw_answer == "Sí"
    assert questions["q_pension_affiliation"].answer.raw_answer == "No sé"
    assert questions["q_occupational_risk_affiliation"].answer is None

    assert [answer.raw_answer for answer in answers] == ["Sí", "No sé"]


def test_questionnaire_without_answers(catalog_path: Path) -> None:
    result = run_questionnaire(
        profile=build_profile(),
        answers=[],
        catalog_path=catalog_path,
    )

    assert all(
        requirement.collection_status.value == "not_started"
        for requirement in result.requirements
    )

    requirement = get_snapshot(result)

    assert all(
        question.answer is None and question.interpretation is None
        for question in requirement.questions
    )


def test_questionnaire_produces_serializable_json(
    catalog_path: Path,
) -> None:
    result = run_questionnaire(
        profile=build_profile(),
        answers=[build_answer("q_health_affiliation", True)],
        catalog_path=catalog_path,
    )

    data = json.loads(result.model_dump_json())

    assert data["catalog_version"] == "2.1"
    assert data["company_profile"]["worker_count"] == 8

    requirement = next(
        item
        for item in data["requirements"]
        if item["requirement_id"] == REQUIREMENT_ID
    )

    assert requirement["collection_status"] == "in_progress"

    health = requirement["questions"][0]

    assert health["question_id"] == "q_health_affiliation"
    assert health["answer"]["raw_answer"] is True

    assert data["scope_note"]


def test_rejects_company_outside_risk_scope(catalog_path: Path) -> None:
    with pytest.raises(OutOfScopeError):
        run_questionnaire(
            profile=build_profile(risk_class=RiskClass.II),
            answers=[],
            catalog_path=catalog_path,
        )


def test_selects_catalog_by_profile_when_no_path_is_given() -> None:
    small = run_questionnaire(
        profile=build_profile(worker_count=8),
        answers=[],
    )
    medium = run_questionnaire(
        profile=build_profile(worker_count=11),
        answers=[],
    )

    assert small.catalog_id != medium.catalog_id


def test_rejects_answer_for_non_applicable_requirement(
    catalog_path: Path,
) -> None:
    answers = [
        build_answer(
            "q_health_affiliation",
            True,
            requirement_id="another_requirement",
        ),
    ]

    with pytest.raises(ValueError):
        run_questionnaire(
            profile=build_profile(),
            answers=answers,
            catalog_path=catalog_path,
        )


def test_rejects_unknown_question(catalog_path: Path) -> None:
    answers = [
        build_answer("unknown_question", True),
    ]

    with pytest.raises(AnswerReferenceError):
        run_questionnaire(
            profile=build_profile(),
            answers=answers,
            catalog_path=catalog_path,
        )


def test_rejects_duplicate_answers(catalog_path: Path) -> None:
    answers = [
        build_answer("q_health_affiliation", True),
        build_answer("q_health_affiliation", False),
    ]

    with pytest.raises(DuplicateAnswerError):
        run_questionnaire(
            profile=build_profile(),
            answers=answers,
            catalog_path=catalog_path,
        )


def test_processes_multiple_requirements_independently(
    catalog_path: Path,
) -> None:
    answers = [
        build_answer("q_health_affiliation", True),
        build_answer(
            "q_training_preparation",
            False,
            requirement_id=TRAINING_REQUIREMENT_ID,
        ),
    ]

    result = run_questionnaire(
        profile=build_profile(),
        answers=answers,
        catalog_path=catalog_path,
    )

    first = get_snapshot(result, REQUIREMENT_ID)
    second = get_snapshot(result, TRAINING_REQUIREMENT_ID)

    first_answered = [
        question.question_id
        for question in first.questions
        if question.answer is not None
    ]
    second_answered = [
        question.question_id
        for question in second.questions
        if question.answer is not None
    ]

    # Each requirement only sees its own answers.
    assert first_answered == ["q_health_affiliation"]
    assert second_answered == ["q_training_preparation"]

    assert first.collection_status.value == "in_progress"
    assert second.collection_status.value == "answers_interpreted"
    assert "q_training_execution" in second.skipped_question_ids
