
import json
from copy import deepcopy
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
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
    CatalogCoverageError,
    OutOfScopeError,
)
from agents.diagnostico_cumplimiento.questionnaire.questionnaire import (
    run_questionnaire,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)

REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"


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


def test_runs_complete_questionnaire_with_partial_answers() -> None:
    answers = [
        build_answer("q_health_affiliation", "Sí"),
        build_answer("q_pension_affiliation", "No sé"),
    ]

    result = run_questionnaire(
        profile=build_profile(),
        answers=answers,
        catalog_path=PILOT_PATH,
    )

    assert result.catalog_version == "res0312-piloto-v1"
    assert result.company_profile.worker_count == 8
    assert len(result.requirements) == 1

    requirement = result.requirements[0]

    assert requirement.requirement_id == REQUIREMENT_ID
    assert requirement.collection_status.value == "needs_resolution"

    assert [
        condition.collection_status.value
        for condition in requirement.conditions
    ] == [
        "answers_interpreted",
        "needs_resolution",
        "not_started",
    ]

    assert [
        condition.evaluation.status.value
        for condition in requirement.conditions
    ] == [
        "not_evaluated",
        "pending_information",
        "pending_information",
    ]

    assert requirement.conditions[0].questions[0].answer.raw_answer == "Sí"
    assert requirement.conditions[1].questions[0].answer.raw_answer == "No sé"
    assert requirement.conditions[2].questions[0].answer is None

    assert [answer.raw_answer for answer in answers] == ["Sí", "No sé"]


def test_questionnaire_without_answers() -> None:
    result = run_questionnaire(
        profile=build_profile(),
        answers=[],
        catalog_path=PILOT_PATH,
    )

    requirement = result.requirements[0]

    assert requirement.collection_status.value == "not_started"

    assert all(
        condition.evaluation.status.value == "pending_information"
        for condition in requirement.conditions
    )


def test_questionnaire_produces_serializable_json() -> None:
    result = run_questionnaire(
        profile=build_profile(),
        answers=[build_answer("q_health_affiliation", True)],
        catalog_path=PILOT_PATH,
    )

    data = json.loads(result.model_dump_json())

    assert data["catalog_version"] == "res0312-piloto-v1"
    assert data["company_profile"]["worker_count"] == 8

    requirement = data["requirements"][0]

    assert requirement["collection_status"] == "in_progress"

    health = requirement["conditions"][0]

    assert health["questions"][0]["answer"]["raw_answer"] is True
    assert health["evaluation"]["status"] == "not_evaluated"

    assert data["scope_note"]


def test_rejects_company_outside_risk_scope() -> None:
    with pytest.raises(OutOfScopeError):
        run_questionnaire(
            profile=build_profile(risk_class=RiskClass.II),
            answers=[],
            catalog_path=PILOT_PATH,
        )


def test_rejects_profile_not_covered_by_pilot_catalog() -> None:
    with pytest.raises(CatalogCoverageError):
        run_questionnaire(
            profile=build_profile(worker_count=11),
            answers=[],
            catalog_path=PILOT_PATH,
        )


def test_rejects_answer_for_non_applicable_requirement() -> None:
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
            catalog_path=PILOT_PATH,
        )


def test_rejects_unknown_question() -> None:
    answers = [
        build_answer("unknown_question", True),
    ]

    with pytest.raises(AnswerReferenceError):
        run_questionnaire(
            profile=build_profile(),
            answers=answers,
            catalog_path=PILOT_PATH,
        )


def test_rejects_duplicate_answers() -> None:
    answers = [
        build_answer("q_health_affiliation", True),
        build_answer("q_health_affiliation", False),
    ]

    with pytest.raises(DuplicateAnswerError):
        run_questionnaire(
            profile=build_profile(),
            answers=answers,
            catalog_path=PILOT_PATH,
        )


def test_processes_multiple_requirements_independently(
    tmp_path: Path,
) -> None:
    """
    Construye un catálogo sintético con dos requisitos.

    No modifica el catálogo piloto ni representa una
    ampliación validada de la matriz normativa.
    """

    catalog = load_catalog(PILOT_PATH)
    catalog_data = catalog.model_dump(mode="json")

    second_requirement = deepcopy(
        catalog_data["requirements"][0]
    )

    second_requirement["id"] = "test_second_requirement"
    second_requirement["requirement_group_id"] = (
        "test_second_requirement_group"
    )

    # Los identificadores del segundo requisito son distintos.
    for condition in second_requirement["conditions"]:
        condition["id"] += "_second"

    for question in second_requirement["questions"]:
        question["id"] += "_second"
        question["condition_id"] += "_second"

    catalog_data["requirements"].append(second_requirement)

    test_catalog_path = tmp_path / "catalogo_dos_requisitos.json"

    test_catalog_path.write_text(
        json.dumps(catalog_data, ensure_ascii=False),
        encoding="utf-8",
    )

    answers = [
        build_answer("q_health_affiliation", True),
        build_answer(
            "q_health_affiliation_second",
            False,
            requirement_id="test_second_requirement",
        ),
    ]

    result = run_questionnaire(
        profile=build_profile(),
        answers=answers,
        catalog_path=test_catalog_path,
    )

    assert len(result.requirements) == 2

    first, second = result.requirements

    assert first.requirement_id == REQUIREMENT_ID
    assert second.requirement_id == "test_second_requirement"

    first_answer = first.conditions[0].questions[0].answer
    second_answer = second.conditions[0].questions[0].answer

    assert first_answer.raw_answer is True
    assert second_answer.raw_answer is False

    assert all(
        condition.evaluation.status.value != "satisfied_as_declared"
        for requirement in result.requirements
        for condition in requirement.conditions
    )
