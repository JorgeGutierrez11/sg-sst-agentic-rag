import pytest
from pydantic import ValidationError

from agents.diagnostico_cumplimiento.catalog.schemas import (
    AssessmentCatalog,
)

import json
from copy import deepcopy
from pathlib import Path

from agents.diagnostico_cumplimiento.catalog.loader import (
    CatalogLoadError,
    load_catalog,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "valid_catalog.json"


def load_fixture_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_catalog_is_valid() -> None:
    catalog = load_catalog(FIXTURE_PATH)

    assert isinstance(catalog, AssessmentCatalog)
    assert catalog.catalog_version == catalog.schema_version == "2.1"
    assert catalog.regulation == catalog.norm
    assert len(catalog.requirements) == 7


def test_catalog_rejects_duplicate_requirement_ids() -> None:
    data = load_fixture_data()
    first_section = data["sections"][0]
    first_section["requirements"].append(
        deepcopy(first_section["requirements"][0])
    )

    with pytest.raises(ValidationError):
        AssessmentCatalog.model_validate(data)


def test_load_catalog_from_json() -> None:
    catalog = load_catalog(FIXTURE_PATH)

    assert catalog.catalog_id == "res0312_riesgo_i_1_10_general"
    assert catalog.schema_version == "2.1"
    assert catalog.regulation == "Resolución 0312 de 2019"
    assert len(catalog.requirements) == 7
    assert catalog.requirements[0].id == "art3_asignacion_persona_sgsst"
    assert catalog.requirements[0].questions[0].id == "q_designer_assigned"


def test_load_catalog_rejects_missing_file(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "does_not_exist.json"

    with pytest.raises(CatalogLoadError):
        load_catalog(missing_path)

def test_load_catalog_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "invalid.json"

    catalog_path.write_text(
        "{ invalid json",
        encoding="utf-8",
    )

    with pytest.raises(CatalogLoadError):
        load_catalog(catalog_path)


def test_load_catalog_rejects_invalid_schema(
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "invalid_schema.json"

    catalog_path.write_text(
        json.dumps(
            {
                "catalog_version": "v1",
                "regulation": "Resolución 0312 de 2019",
                "requirements": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CatalogLoadError):
        load_catalog(catalog_path)


def test_catalog_allows_requirements_with_distinct_ids_and_same_applicability() -> None:
    data = load_fixture_data()
    section = data["sections"][0]

    extra = deepcopy(section["requirements"][0])
    extra["id"] = "extra_requirement"
    for question in extra["questions"]:
        question["id"] += "_extra"
        if question.get("depends_on"):
            question["depends_on"]["question_id"] += "_extra"
    section["requirements"].append(extra)

    catalog = AssessmentCatalog.model_validate(data)

    assert len(catalog.requirements) == 8
    assert (
        catalog.requirements[0].applicability
        == catalog.requirements[-1].applicability
    )
    assert catalog.requirements[0].id != catalog.requirements[-1].id
