
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.catalog.schemas import (
    AssessmentCatalog,
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.rules.applicability import (
    AmbiguousApplicabilityError,
    CatalogCoverageError,
    OutOfScopeError,
    select_applicable_requirements,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "valid_catalog.json"
)


def build_variant(
    requirement_id: str,
    worker_count_min: int,
    worker_count_max: int | None,
) -> RequirementDefinition:
    """
    Construye una variante sintética a partir del fixture existente.

    Todas las variantes pertenecen al mismo ítem oficial de prueba.
    """

    base_requirement = load_catalog(
        FIXTURE_PATH
    ).requirements[0]

    data = base_requirement.model_dump()

    data["id"] = requirement_id

    data["applicability"] = {
        "risk_classes": ["I"],
        "worker_count_min": worker_count_min,
        "worker_count_max": worker_count_max,
    }

    return RequirementDefinition.model_validate(data)


def build_test_catalog() -> AssessmentCatalog:
    """
    Catálogo sintético con tres variantes de un mismo ítem.
    """

    return AssessmentCatalog(
        catalog_version="test-applicability-v1",
        regulation="Norma de prueba",
        requirements=[
            build_variant(
                requirement_id="test_1_10",
                worker_count_min=1,
                worker_count_max=10,
            ),
            build_variant(
                requirement_id="test_11_50",
                worker_count_min=11,
                worker_count_max=50,
            ),
            build_variant(
                requirement_id="test_51_plus",
                worker_count_min=51,
                worker_count_max=None,
            ),
        ],
    )


@pytest.mark.parametrize(
    ("worker_count", "expected_requirement_id"),
    [
        (1, "test_1_10"),
        (8, "test_1_10"),
        (10, "test_1_10"),
        (11, "test_11_50"),
        (35, "test_11_50"),
        (50, "test_11_50"),
        (51, "test_51_plus"),
        (80, "test_51_plus"),
    ],
)
def test_selects_correct_worker_range(
    worker_count: int,
    expected_requirement_id: str,
) -> None:
    profile = CompanyProfile(
        worker_count=worker_count,
        risk_class="I",
    )

    catalog = build_test_catalog()

    requirements = select_applicable_requirements(
        profile,
        catalog,
    )

    assert len(requirements) == 1
    assert requirements[0].id == expected_requirement_id


def test_rejects_company_outside_risk_scope() -> None:
    profile = CompanyProfile(
        worker_count=8,
        risk_class="II",
    )

    catalog = build_test_catalog()

    with pytest.raises(OutOfScopeError):
        select_applicable_requirements(
            profile,
            catalog,
        )


def test_rejects_catalog_without_matching_requirements() -> None:
    profile = CompanyProfile(
        worker_count=35,
        risk_class="I",
    )

    catalog = AssessmentCatalog(
        catalog_version="incomplete-test-v1",
        regulation="Norma de prueba",
        requirements=[
            build_variant(
                requirement_id="only_small_companies",
                worker_count_min=1,
                worker_count_max=10,
            ),
        ],
    )

    with pytest.raises(CatalogCoverageError):
        select_applicable_requirements(
            profile,
            catalog,
        )


def test_rejects_overlapping_variants_of_same_item() -> None:
    profile = CompanyProfile(
        worker_count=8,
        risk_class="I",
    )

    catalog = AssessmentCatalog(
        catalog_version="overlapping-test-v1",
        regulation="Norma de prueba",
        requirements=[
            build_variant(
                requirement_id="variant_a",
                worker_count_min=1,
                worker_count_max=10,
            ),
            build_variant(
                requirement_id="variant_b",
                worker_count_min=1,
                worker_count_max=20,
            ),
        ],
    )

    with pytest.raises(AmbiguousApplicabilityError):
        select_applicable_requirements(
            profile,
            catalog,
        )



def test_allows_distinct_requirements_without_general_item_id() -> None:
    """
    Dos requisitos diferentes de un conjunto reducido pueden
    ser aplicables simultáneamente sin tener identificador
    asignado en la tabla general.
    """

    profile = CompanyProfile(
        worker_count=8,
        risk_class="I",
    )


    first = build_variant(
        requirement_id="test_affiliation",
        worker_count_min=1,
        worker_count_max=10,
    ).model_copy(
        update={
            "requirement_group_id": "test_affiliation",
            "official_item_id": None,
        }
    )

    second = build_variant(
        requirement_id="test_training",
        worker_count_min=1,
        worker_count_max=10,
    ).model_copy(
        update={
            "requirement_group_id": "test_training",
            "official_item_id": None,
        }
    )


    catalog = AssessmentCatalog(
        catalog_version="test-reduced-v1",
        regulation="Norma de prueba",
        requirements=[first, second],
    )

    requirements = select_applicable_requirements(
        profile,
        catalog,
    )

    assert len(requirements) == 2

    assert {requirement.id for requirement in requirements} == {
        "test_affiliation",
        "test_training",
    }


def test_rejects_overlapping_variants_without_general_item_id() -> None:
    """
    Dos variantes del mismo requisito no pueden seleccionarse
    simultáneamente, aunque no tengan official_item_id.
    """

    profile = CompanyProfile(
        worker_count=8,
        risk_class="I",
    )

    first = build_variant(
        requirement_id="variant_a",
        worker_count_min=1,
        worker_count_max=10,
    ).model_copy(
        update={
            "requirement_group_id": "same_requirement",
            "official_item_id": None,
        }
    )

    second = build_variant(
        requirement_id="variant_b",
        worker_count_min=1,
        worker_count_max=20,
    ).model_copy(
        update={
            "requirement_group_id": "same_requirement",
            "official_item_id": None,
        }
    )

    catalog = AssessmentCatalog(
        catalog_version="test-overlap-v1",
        regulation="Norma de prueba",
        requirements=[first, second],
    )

    with pytest.raises(AmbiguousApplicabilityError):
        select_applicable_requirements(
            profile,
            catalog,
        )
