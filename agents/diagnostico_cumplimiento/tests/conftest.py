"""Shared fixtures for the compliance-diagnosis test suite."""

from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.catalog.schemas import AssessmentCatalog

# Frozen v2.1 snapshot of res0312_riesgo_i_1_10_general.json. Tests use this
# copy instead of the live catalog so catalog edits do not break behavior tests.
CATALOG_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "valid_catalog.json"


@pytest.fixture
def catalog_path() -> Path:
    return CATALOG_FIXTURE_PATH


@pytest.fixture
def catalog() -> AssessmentCatalog:
    return load_catalog(CATALOG_FIXTURE_PATH)
