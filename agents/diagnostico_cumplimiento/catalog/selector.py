from __future__ import annotations

from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"


class CatalogSelectionError(ValueError):
    """No existe un paquete normativo aplicable al perfil recibido."""


CATALOG_FILES = {
    "risk_i_1_10_general": DATA_DIR / "res0312_riesgo_i_1_10_general.json",
    "risk_i_1_10_agricultural": DATA_DIR
    / "res0312_riesgo_i_1_10_agropecuaria.json",
    "risk_i_11_50": DATA_DIR / "res0312_riesgo_i_11_50.json",
    "risk_i_51_plus": DATA_DIR / "res0312_riesgo_i_51_plus.json",
}


def select_catalog_path(profile: Any) -> Path:
    """
    Selecciona el paquete normativo aplicable según el perfil empresarial.

    Alcance actual:
    - Resolución 0312 de 2019.
    - Clase de riesgo I.
    """

    risk_class = str(profile.risk_class).strip().upper()

    if risk_class != "I":
        raise CatalogSelectionError(
            "El diagnóstico actual solo cubre empresas clasificadas en riesgo I."
        )

    is_agricultural = bool(
        getattr(profile, "is_agricultural_production_unit", False)
    )

    worker_count = getattr(profile, "worker_count", None)

    if worker_count is None:
        raise CatalogSelectionError(
            "No se informó la cantidad de trabajadores de la empresa."
        )

    if worker_count < 1:
        raise CatalogSelectionError(
            "La cantidad de trabajadores debe ser mayor o igual a 1."
        )

    # Unidad de Producción Agropecuaria.
    if is_agricultural:
        permanent_worker_count = getattr(
            profile,
            "permanent_worker_count",
            None,
        )

        if permanent_worker_count is None:
            raise CatalogSelectionError(
                "Para una Unidad de Producción Agropecuaria debe "
                "informarse la cantidad de trabajadores permanentes."
            )

        if permanent_worker_count < 1:
            raise CatalogSelectionError(
                "La cantidad de trabajadores permanentes debe "
                "ser mayor o igual a 1."
            )

        if permanent_worker_count <= 10:
            return CATALOG_FILES["risk_i_1_10_agricultural"]

        if permanent_worker_count <= 50:
            return CATALOG_FILES["risk_i_11_50"]

        return CATALOG_FILES["risk_i_51_plus"]

    # Empresa general.
    if worker_count <= 10:
        return CATALOG_FILES["risk_i_1_10_general"]

    if worker_count <= 50:
        return CATALOG_FILES["risk_i_11_50"]

    return CATALOG_FILES["risk_i_51_plus"]