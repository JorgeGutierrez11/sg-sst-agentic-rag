import json
from copy import deepcopy
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.catalog.schemas import AssessmentCatalog
from agents.diagnostico_cumplimiento.catalog.selector import (
    CATALOG_FILES,
    CatalogSelectionError,
    select_catalog_path,
)
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile
from agents.diagnostico_cumplimiento.rules.applicability import (
    CatalogCoverageError,
    OutOfScopeError,
    select_applicable_requirements,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "valid_catalog.json"
)


def build_empty_catalog() -> AssessmentCatalog:
    """Valid v2.1 catalog whose sections contain no requirements."""

    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for section in data["sections"]:
        section["requirements"] = []

    return AssessmentCatalog.model_validate(data)


@pytest.mark.parametrize(
    ("worker_count", "expected_catalog_key"),
    [
        (1, "risk_i_1_10_general"),
        (8, "risk_i_1_10_general"),
        (10, "risk_i_1_10_general"),
        (11, "risk_i_11_50"),
        (35, "risk_i_11_50"),
        (50, "risk_i_11_50"),
        (51, "risk_i_51_plus"),
        (80, "risk_i_51_plus"),
    ],
)
def test_selects_correct_worker_range(
    worker_count: int,
    expected_catalog_key: str,
) -> None:
    # The worker-range variant is chosen by the catalog selector, which
    # hands one normative package per profile to select_applicable_requirements.
    profile = CompanyProfile(
        worker_count=worker_count,
        risk_class="I",
    )

    assert select_catalog_path(profile) == CATALOG_FILES[expected_catalog_key]


def test_selector_rejects_non_risk_i_profile() -> None:
    profile = CompanyProfile(
        worker_count=8,
        risk_class="II",
    )

    with pytest.raises(CatalogSelectionError):
        select_catalog_path(profile)


def test_returns_every_requirement_of_selected_package() -> None:
    profile = CompanyProfile(
        worker_count=8,
        risk_class="I",
    )

    catalog = load_catalog(FIXTURE_PATH)

    requirements = select_applicable_requirements(
        profile,
        catalog,
    )

    assert [requirement.id for requirement in requirements] == [
        requirement.id for requirement in catalog.requirements
    ]
    assert len(requirements) == 7


def test_rejects_company_outside_risk_scope() -> None:
    profile = CompanyProfile(
        worker_count=8,
        risk_class="II",
    )

    catalog = load_catalog(FIXTURE_PATH)

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

    with pytest.raises(CatalogCoverageError):
        select_applicable_requirements(
            profile,
            build_empty_catalog(),
        )


def test_allows_distinct_requirements_in_same_package() -> None:
    """
    Dos requisitos diferentes del mismo paquete normativo pueden
    ser aplicables simultáneamente.
    """

    profile = CompanyProfile(
        worker_count=8,
        risk_class="I",
    )

    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    section = data["sections"][0]
    original = section["requirements"][0]

    extra = deepcopy(original)
    extra["id"] = "test_extra_requirement"
    for question in extra["questions"]:
        question["id"] += "_extra"
        if question.get("depends_on"):
            question["depends_on"]["question_id"] += "_extra"
    section["requirements"].append(extra)

    catalog = AssessmentCatalog.model_validate(data)

    requirements = select_applicable_requirements(
        profile,
        catalog,
    )

    assert {original["id"], "test_extra_requirement"} <= {
        requirement.id for requirement in requirements
    }
