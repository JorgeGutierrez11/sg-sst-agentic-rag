from __future__ import annotations

from typing import TypeAlias

from agents.diagnostico_cumplimiento.reporting.art27_scoring_matrix import (
    Article27ScoringMatrix,
    build_article27_scoring_matrix,
)
from agents.diagnostico_cumplimiento.reporting.orientative_report import (
    OrientativeReport,
)
from agents.diagnostico_cumplimiento.reporting.upa_scoring_matrix import (
    UPAScoringMatrix,
    build_upa_scoring_matrix,
)


UPA_1_10_CATALOG_ID = (
    "res0312_riesgo_i_1_10_agropecuaria"
)

ScoringMatrix: TypeAlias = (
    Article27ScoringMatrix
    | UPAScoringMatrix
)


def build_scoring_matrix(
    report: OrientativeReport,
) -> ScoringMatrix:
    """
    Construye automáticamente la matriz de calificación
    correspondiente al paquete normativo utilizado por
    el diagnóstico.

    - Empresas generales de 1-10 trabajadores:
      Tabla de Valores del artículo 27.

    - Empresas de 11-50 trabajadores:
      Tabla de Valores del artículo 27.

    - Empresas de más de 50 trabajadores:
      Tabla de Valores del artículo 27.

    - UPA de 1-10 trabajadores permanentes:
      esquema especial de tres estándares.
    """

    if report.catalog_id == UPA_1_10_CATALOG_ID:
        return build_upa_scoring_matrix(
            report
        )

    return build_article27_scoring_matrix(
        report
    )
