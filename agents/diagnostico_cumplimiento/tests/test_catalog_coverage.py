
import json
from copy import deepcopy
from pathlib import Path

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.preliminary_diagnosis import (
    run_preliminary_diagnosis,
)


# Frozen v2.1 snapshot of the general 1-10 catalog (7 requirements).
CATALOG_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "valid_catalog.json"
)


def run_diagnosis(catalog_path=CATALOG_PATH):
    return run_preliminary_diagnosis(
        profile=CompanyProfile(
            worker_count=8,
            risk_class=RiskClass.I,
        ),
        answers=[],
        catalog_path=catalog_path,
    )


def test_package_reports_its_actual_coverage():
    result = run_diagnosis()
    catalog = load_catalog(CATALOG_PATH)

    assert result.coverage.status == "selected_package"
    assert result.coverage.included_requirement_count == 7
    assert result.coverage.included_requirement_ids == [
        requirement.id for requirement in catalog.requirements
    ]

    assert [
        requirement.requirement_id
        for requirement in result.questionnaire.requirements
    ] == result.coverage.included_requirement_ids


def test_coverage_is_included_in_serialized_result():
    result = run_diagnosis()

    data = json.loads(result.model_dump_json())

    assert data["coverage"]["status"] == "selected_package"
    assert data["coverage"]["included_requirement_count"] == 7
    assert len(data["coverage"]["included_requirement_ids"]) == 7
    assert data["coverage"]["explanation"]

    assert data["questionnaire"]["catalog_version"] == (
        data["report"]["catalog_version"]
    )


def test_coverage_counts_all_selected_requirements(tmp_path: Path):
    """
    Agrega un requisito sintético para comprobar el conteo.

    No modifica el catálogo real ni amplía su cobertura normativa.
    """

    catalog_data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    section = catalog_data["sections"][0]
    second = deepcopy(section["requirements"][0])
    second["id"] = "test_second_requirement"

    for question in second["questions"]:
        question["id"] += "_second"
        if question.get("depends_on"):
            question["depends_on"]["question_id"] += "_second"

    section["requirements"].append(second)

    test_catalog = tmp_path / "catalogo_sintetico.json"
    test_catalog.write_text(
        json.dumps(catalog_data, ensure_ascii=False),
        encoding="utf-8",
    )

    result = run_diagnosis(test_catalog)

    assert result.coverage.included_requirement_count == 8
    assert result.coverage.included_requirement_ids[0] == (
        "art3_asignacion_persona_sgsst"
    )
    assert "test_second_requirement" in (
        result.coverage.included_requirement_ids
    )

    assert [
        requirement.requirement_id
        for requirement in result.report.requirements
    ] == result.coverage.included_requirement_ids
