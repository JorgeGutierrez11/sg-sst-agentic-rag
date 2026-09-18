import json
from pathlib import Path

from pydantic import ValidationError

from agents.diagnostico_cumplimiento.catalog.schemas import AssessmentCatalog


class CatalogLoadError(Exception):
    """
    Error producido al intentar cargar o validar un catálogo normativo.
    """


def load_catalog(path: str | Path) -> AssessmentCatalog:
    """
    Carga un catálogo de evaluación desde un archivo JSON.

    El archivo debe cumplir completamente el schema definido por
    AssessmentCatalog. Cualquier error de lectura, JSON o validación
    produce CatalogLoadError.
    """

    catalog_path = Path(path)

    if not catalog_path.exists():
        raise CatalogLoadError(
            f"Catalog file does not exist: {catalog_path}"
        )

    if not catalog_path.is_file():
        raise CatalogLoadError(
            f"Catalog path is not a file: {catalog_path}"
        )

    try:
        raw_data = catalog_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogLoadError(
            f"Could not read catalog file: {catalog_path}"
        ) from exc

    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise CatalogLoadError(
            f"Catalog contains invalid JSON: {catalog_path}"
        ) from exc

    try:
        return AssessmentCatalog.model_validate(data)
    except ValidationError as exc:
        raise CatalogLoadError(
            f"Catalog does not match the expected schema: {catalog_path}"
        ) from exc