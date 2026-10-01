
import json
from copy import deepcopy
from pathlib import Path

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.preliminary_diagnosis import (
    run_preliminary_diagnosis,
)


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v2.json"
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


def test_pilot_reports_its_actual_coverage():
    result = run_diagnosis()

    assert result.coverage.status == "not_established"
    assert result.coverage.included_requirement_count == 1
    assert result.coverage.included_requirement_ids == [
        "res0312_art3_afiliacion_1_10"
    ]

    assert [
        requirement.requirement_id
        for requirement in result.questionnaire.requirements
    ] == result.coverage.included_requirement_ids


def test_coverage_is_included_in_serialized_result():
    result = run_diagnosis()

    data = json.loads(result.model_dump_json())

    assert data["coverage"]["status"] == "not_established"
    assert data["coverage"]["included_requirement_count"] == 1
    assert len(data["coverage"]["included_requirement_ids"]) == 1
    assert data["coverage"]["explanation"]

    assert data["questionnaire"]["catalog_version"] == (
        data["report"]["catalog_version"]
    )


def test_coverage_counts_all_selected_requirements(tmp_path: Path):
    """
    Agrega un requisito sintético para comprobar el conteo.

    No modifica el catálogo piloto ni amplía su cobertura
    normativa real.
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

    result = run_diagnosis(test_catalog)

    assert result.coverage.included_requirement_count == 2
    assert result.coverage.included_requirement_ids == [
        "res0312_art3_afiliacion_1_10",
        "test_second_requirement",
    ]

    # Aumentar el número de requisitos no demuestra
    # que el catálogo tenga cobertura normativa completa.
    assert result.coverage.status == "not_established"

    assert [
        requirement.requirement_id
        for requirement in result.report.requirements
    ] == result.coverage.included_requirement_ids
