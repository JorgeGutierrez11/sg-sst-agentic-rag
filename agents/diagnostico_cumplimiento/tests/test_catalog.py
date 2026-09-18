import pytest
from pydantic import ValidationError

from agents.diagnostico_cumplimiento.catalog.schemas import (
    AssessmentCatalog,
    ConditionDefinition,
    CriterionDefinition,
    QuestionDefinition,
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.enums import QuestionType
from agents.diagnostico_cumplimiento.domain.models import (
    ApplicabilityRule,
    NormativeSource,
)

import json
from pathlib import Path

from agents.diagnostico_cumplimiento.catalog.loader import (
    CatalogLoadError,
    load_catalog,
)


def build_requirement() -> RequirementDefinition:
    return RequirementDefinition(
        id="example_requirement",
        source=NormativeSource(
            regulation="Resolución 0312 de 2019",
            article="Artículo 3",
            official_url=(
                "https://www.fondoriesgoslaborales.gov.co/"
                "wp-content/uploads/2018/09/"
                "RESOLUCION-0312-DEL-2019.pdf"
            ),
        ),
        applicability=ApplicabilityRule(
            risk_classes=["I"],
            worker_count_min=1,
            worker_count_max=10,
        ),
        criterion=CriterionDefinition(
            name="Criterio de ejemplo",
            official_text="Texto normativo de ejemplo.",
            verification_method="Modo de verificación de ejemplo.",
        ),
        conditions=[
            ConditionDefinition(
                id="exists",
                description="El elemento requerido existe.",
                required=True,
            ),
        ],
        questions=[
            QuestionDefinition(
                id="example_q1",
                condition_id="exists",
                text="¿Cuenta actualmente con el elemento requerido?",
                type=QuestionType.BOOLEAN,
            ),
        ],
        official_weight=None,
    )


def test_requirement_definition_is_valid() -> None:
    requirement = build_requirement()

    assert requirement.id == "example_requirement"
    assert requirement.applicability.worker_count_min == 1
    assert len(requirement.conditions) == 1
    assert len(requirement.questions) == 1
    assert requirement.official_weight is None


def test_catalog_is_valid() -> None:
    catalog = AssessmentCatalog(
        catalog_version="res0312-riesgo-i-v1",
        regulation="Resolución 0312 de 2019",
        requirements=[build_requirement()],
    )

    assert catalog.catalog_version == "res0312-riesgo-i-v1"
    assert len(catalog.requirements) == 1


def test_requirement_rejects_empty_conditions() -> None:
    requirement = build_requirement()

    with pytest.raises(ValidationError):
        RequirementDefinition(
            id=requirement.id,
            source=requirement.source,
            applicability=requirement.applicability,
            criterion=requirement.criterion,
            conditions=[],
            questions=requirement.questions,
        )


def test_question_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        QuestionDefinition(
            id="q1",
            condition_id="exists",
            text="",
            type=QuestionType.BOOLEAN,
        )


def test_requirement_rejects_negative_weight() -> None:
    requirement = build_requirement()

    with pytest.raises(ValidationError):
        RequirementDefinition(
            id=requirement.id,
            source=requirement.source,
            applicability=requirement.applicability,
            criterion=requirement.criterion,
            conditions=requirement.conditions,
            questions=requirement.questions,
            official_weight=-1,
        )

def test_requirement_rejects_unknown_condition_reference() -> None:
    requirement = build_requirement()

    with pytest.raises(ValidationError):
        RequirementDefinition(
            id=requirement.id,
            source=requirement.source,
            applicability=requirement.applicability,
            criterion=requirement.criterion,
            conditions=requirement.conditions,
            questions=[
                QuestionDefinition(
                    id="q_unknown",
                    condition_id="does_not_exist",
                    text="¿Pregunta inválida?",
                    type=QuestionType.BOOLEAN,
                )
            ],
        )

def test_requirement_rejects_duplicate_condition_ids() -> None:
    requirement = build_requirement()

    with pytest.raises(ValidationError):
        RequirementDefinition(
            id=requirement.id,
            source=requirement.source,
            applicability=requirement.applicability,
            criterion=requirement.criterion,
            conditions=[
                ConditionDefinition(
                    id="exists",
                    description="Primera condición.",
                ),
                ConditionDefinition(
                    id="exists",
                    description="Condición duplicada.",
                ),
            ],
            questions=requirement.questions,
        )

def test_requirement_rejects_duplicate_question_ids() -> None:
    requirement = build_requirement()

    question = QuestionDefinition(
        id="q1",
        condition_id="exists",
        text="¿Existe?",
        type=QuestionType.BOOLEAN,
    )

    with pytest.raises(ValidationError):
        RequirementDefinition(
            id=requirement.id,
            source=requirement.source,
            applicability=requirement.applicability,
            criterion=requirement.criterion,
            conditions=requirement.conditions,
            questions=[
                question,
                question,
            ],
        )

def test_catalog_rejects_duplicate_requirement_ids() -> None:
    requirement = build_requirement()

    with pytest.raises(ValidationError):
        AssessmentCatalog(
            catalog_version="res0312-riesgo-i-v1",
            regulation="Resolución 0312 de 2019",
            requirements=[
                requirement,
                requirement,
            ],
        )

def test_selection_question_requires_options() -> None:
    with pytest.raises(ValidationError):
        QuestionDefinition(
            id="q1",
            condition_id="condition",
            text="Seleccione una opción.",
            type=QuestionType.SINGLE_CHOICE,
        )

def test_selection_question_accepts_options() -> None:
    question = QuestionDefinition(
        id="q1",
        condition_id="condition",
        text="Seleccione una opción.",
        type=QuestionType.SINGLE_CHOICE,
        options=[
            "Opción A",
            "Opción B",
        ],
    )

    assert question.options == [
        "Opción A",
        "Opción B",
    ]

def test_load_catalog_from_json() -> None:
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "valid_catalog.json"
    )

    catalog = load_catalog(fixture_path)

    assert catalog.catalog_version == "test-v1"
    assert catalog.regulation == "Resolución 0312 de 2019"
    assert len(catalog.requirements) == 1
    assert catalog.requirements[0].id == "test_requirement"

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


