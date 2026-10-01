
import json
from copy import deepcopy
from pathlib import Path

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.questionnaire.questionnaire import run_questionnaire


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v2.json"
)

REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"


def run_pilot(answers, catalog_path=CATALOG_PATH):
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


def test_json_preserves_answers_and_negative_findings():
    result = run_pilot(
        [
            answer("q_health_affiliation", True),
            answer("q_health_affiliation_support", False),
        ]
    )

    data = json.loads(result.model_dump_json())

    requirement = data["requirements"][0]
    findings = data["declarative_findings"][0]
    health = requirement["conditions"][0]
    health_finding = findings["conditions"][0]

    assert findings["requirement_id"] == requirement["requirement_id"]

    assert health["questions"][0]["answer"]["raw_answer"] is True
    assert health["questions"][1]["answer"]["raw_answer"] is False
    assert health["questions"][2]["answer"] is None

    assert health_finding["status"] == "incomplete"
    assert health_finding["negative_question_ids"] == [
        "q_health_affiliation_support"
    ]
    assert health_finding["unanswered_question_ids"] == [
        "q_health_payment_support"
    ]
    assert health_finding["evidence_verified"] is False

    assert health["evaluation"]["status"] == "pending_information"


def test_all_affirmative_answers_do_not_establish_compliance():
    requirement = load_catalog(CATALOG_PATH).requirements[0]

    answers = [
        answer(question.id, True)
        for question in requirement.questions
    ]

    result = run_pilot(answers)

    assert result.requirements[0].collection_status.value == (
        "answers_interpreted"
    )

    assert all(
        finding.status.value == "all_affirmative_declared"
        and finding.evidence_verified is False
        for finding in result.declarative_findings[0].conditions
    )

    assert all(
        condition.evaluation.status.value == "not_evaluated"
        for condition in result.requirements[0].conditions
    )


def test_unanswered_questionnaire_contains_pending_findings():
    result = run_pilot([])

    assert result.requirements[0].collection_status.value == (
        "not_started"
    )

    findings = result.declarative_findings[0].conditions

    assert len(findings) == 3

    for finding in findings:
        assert finding.status.value == "incomplete"
        assert len(finding.unanswered_question_ids) == 3
        assert finding.negative_question_ids == []
        assert finding.evidence_verified is False


def test_findings_match_their_requirement_with_multiple_requirements(
    tmp_path: Path,
):
    """
    Utiliza un segundo requisito sintético únicamente para
    comprobar que no se mezclan respuestas ni hallazgos.
    """

    catalog = load_catalog(CATALOG_PATH)
    catalog_data = catalog.model_dump(mode="json")

    second = deepcopy(catalog_data["requirements"][0])
    second["id"] = "test_second_requirement"
    second["requirement_group_id"] = "test_second_group"

    for condition in second["conditions"]:
        condition["id"] += "_second"

    for question in second["questions"]:
        question["id"] += "_second"
        question["condition_id"] += "_second"

    catalog_data["requirements"].append(second)

    test_catalog = tmp_path / "catalogo_sintetico.json"
    test_catalog.write_text(
        json.dumps(catalog_data, ensure_ascii=False),
        encoding="utf-8",
    )

    result = run_pilot(
        [
            answer("q_health_affiliation", True),
            answer(
                "q_health_affiliation_second",
                False,
                requirement_id="test_second_requirement",
            ),
        ],
        catalog_path=test_catalog,
    )

    assert len(result.requirements) == 2
    assert len(result.declarative_findings) == 2

    for requirement, findings in zip(
        result.requirements,
        result.declarative_findings,
        strict=True,
    ):
        assert findings.requirement_id == requirement.requirement_id

        assert [
            finding.condition_id for finding in findings.conditions
        ] == [
            condition.condition_id
            for condition in requirement.conditions
        ]

    first_findings = result.declarative_findings[0].conditions[0]
    second_findings = result.declarative_findings[1].conditions[0]

    assert first_findings.negative_question_ids == []
    assert second_findings.negative_question_ids == [
        "q_health_affiliation_second"
    ]
