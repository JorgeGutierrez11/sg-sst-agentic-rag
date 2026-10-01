from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    DeclarativeAssessmentStatus,
)
from agents.diagnostico_cumplimiento.reporting.orientative_report import (
    OrientativeReport,
    RequirementReport,
)


DATA_DIR = Path(__file__).resolve().parent / "data"

DEFAULT_ART27_TABLE_PATH = (
    DATA_DIR / "res0312_art27_scoring_table.json"
)

DEFAULT_1_10_GENERAL_MAPPING_PATH = (
    DATA_DIR
    / "res0312_art27_mapping_1_10_general.json"
)

DEFAULT_11_50_MAPPING_PATH = (
    DATA_DIR
    / "res0312_art27_mapping_11_50.json"
)

DEFAULT_51_PLUS_MAPPING_PATH = (
    DATA_DIR
    / "res0312_art27_mapping_51_plus.json"
)

ARTICLE27_MAPPING_PATHS = {
    "res0312_riesgo_i_1_10_general": (
        DEFAULT_1_10_GENERAL_MAPPING_PATH
    ),
    "res0312_riesgo_i_11_50": (
        DEFAULT_11_50_MAPPING_PATH
    ),
    "res0312_riesgo_i_51_plus": (
        DEFAULT_51_PLUS_MAPPING_PATH
    ),
}


class Article27TableStatus(StrEnum):
    COMPLIES = "complies"
    DOES_NOT_COMPLY = "does_not_comply"
    NOT_APPLICABLE = "not_applicable"


class Article27ScoringRow(BaseModel):
    """
    Fila diligenciada de la Tabla de Valores y Calificación
    del artículo 27 de la Resolución 0312 de 2019.

    ``assessment_status`` conserva el resultado interno del
    diagnóstico.

    ``table_status`` representa la selección que se mostrará
    en las columnas oficiales:

    - Cumple totalmente
    - No cumple
    - No aplica
    """

    model_config = ConfigDict(extra="forbid")

    cycle_id: str
    cycle_name: str

    component_id: str
    component_name: str

    standard_id: str
    standard_name: str
    weight_percent: float

    official_item_id: str
    description: str
    item_value: float

    requirement_id: str | None = None

    assessment_status: DeclarativeAssessmentStatus | None = None

    table_status: Article27TableStatus

    complies_fully: bool
    does_not_comply: bool
    not_applicable: bool

    score: float

    comment: str


class Article27ScoringSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_items: int

    evaluated_items: int
    not_applicable_items: int

    complies_items: int
    does_not_comply_items: int

    insufficient_information_items: int

    total_score: float
    maximum_score: float = 100.0


class Article27ScoringMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_id: str
    mapping_id: str
    catalog_id: str

    rows: list[Article27ScoringRow] = Field(
        min_length=60,
        max_length=60,
    )

    summary: Article27ScoringSummary


def build_article27_scoring_matrix(
    report: OrientativeReport,
    *,
    table_path: Path = DEFAULT_ART27_TABLE_PATH,
    mapping_path: Path | None = None,
) -> Article27ScoringMatrix:
    """
    Convierte el resultado orientativo del Agente 2 en las
    60 filas de la Tabla de Valores y Calificación del
    artículo 27.

    Esta función no vuelve a evaluar requisitos.

    Utiliza:

    1. La tabla normativa de 60 ítems.
    2. El mapeo del paquete normativo hacia la tabla.
    3. Los resultados declarativos ya calculados por el agente.
    """

    table = _load_json(table_path)

    resolved_mapping_path = _resolve_mapping_path(
        report=report,
        mapping_path=mapping_path,
    )

    mapping = _load_json(
        resolved_mapping_path
    )

    if mapping["catalog_id"] != report.catalog_id:
        raise ValueError(
            "El mapeo seleccionado no corresponde al "
            "catálogo utilizado por el diagnóstico: "
            f"report={report.catalog_id!r}, "
            f"mapping={mapping['catalog_id']!r}."
        )

    requirements_by_id = {
        requirement.requirement_id: requirement
        for requirement in report.requirements
    }

    evaluated_mapping = {
        item["official_item_id"]: item
        for item in mapping["evaluated_items"]
    }

    _validate_mapping_requirements(
        requirements_by_id=requirements_by_id,
        evaluated_mapping=evaluated_mapping,
    )

    rows: list[Article27ScoringRow] = []

    for cycle in table["cycles"]:
        for component in cycle["components"]:
            for standard in component["standards"]:
                for item in standard["items"]:
                    official_item_id = item[
                        "official_item_id"
                    ]

                    mapped = evaluated_mapping.get(
                        official_item_id
                    )

                    if mapped is None:
                        row = _build_not_applicable_row(
                            cycle=cycle,
                            component=component,
                            standard=standard,
                            item=item,
                            non_applicability_reason=(
                                mapping
                                .get(
                                    "non_applicability",
                                    {},
                                )
                                .get("reason")
                            ),
                        )
                    else:
                        requirement = requirements_by_id[
                            mapped["requirement_id"]
                        ]

                        row = _build_evaluated_row(
                            cycle=cycle,
                            component=component,
                            standard=standard,
                            item=item,
                            requirement=requirement,
                        )

                    rows.append(row)

    _validate_rows(rows)

    summary = _build_summary(rows)

    return Article27ScoringMatrix(
        table_id=table["catalog_id"],
        mapping_id=mapping["mapping_id"],
        catalog_id=mapping["catalog_id"],
        rows=rows,
        summary=summary,
    )


def _resolve_mapping_path(
    *,
    report: OrientativeReport,
    mapping_path: Path | None,
) -> Path:
    """
    Selecciona el mapeo de la Tabla de Valores del
    artículo 27 correspondiente al catálogo utilizado
    por el diagnóstico.

    El paquete UPA de diez (10) o menos trabajadores
    permanentes utiliza un esquema de calificación
    específico de tres estándares y no debe procesarse
    mediante la matriz de 60 ítems.
    """

    if mapping_path is not None:
        return mapping_path

    if (
        report.catalog_id
        == "res0312_riesgo_i_1_10_agropecuaria"
    ):
        raise ValueError(
            "El catálogo "
            "'res0312_riesgo_i_1_10_agropecuaria' "
            "no utiliza la matriz del artículo 27. "
            "Debe procesarse mediante el esquema "
            "especial de calificación UPA de tres "
            "estándares."
        )

    try:
        return ARTICLE27_MAPPING_PATHS[
            report.catalog_id
        ]
    except KeyError as exc:
        raise ValueError(
            "No existe un mapeo de la Tabla de Valores "
            "del artículo 27 para el catálogo "
            f"{report.catalog_id!r}."
        ) from exc


def _build_evaluated_row(
    *,
    cycle: dict,
    component: dict,
    standard: dict,
    item: dict,
    requirement: RequirementReport,
) -> Article27ScoringRow:
    status = requirement.assessment_status

    if status is None:
        raise ValueError(
            "El requisito "
            f"'{requirement.requirement_id}' "
            "no tiene resultado declarativo."
        )

    item_value = float(item["item_value"])

    if (
        status
        == DeclarativeAssessmentStatus.COMPLIES_AS_DECLARED
    ):
        table_status = Article27TableStatus.COMPLIES
        score = item_value

    elif (
        status
        == DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED
    ):
        table_status = (
            Article27TableStatus.DOES_NOT_COMPLY
        )
        score = 0.0

    elif (
        status
        == DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
    ):
        # La tabla oficial no contempla un cuarto estado.
        # Para la salida del artículo 27 se adopta una
        # política conservadora: No cumple = 0.
        # El estado interno se conserva y se explica
        # expresamente en el comentario.
        table_status = (
            Article27TableStatus.DOES_NOT_COMPLY
        )
        score = 0.0

    elif (
        status
        == DeclarativeAssessmentStatus.NOT_APPLICABLE
    ):
        table_status = Article27TableStatus.NOT_APPLICABLE
        score = item_value

    else:
        raise ValueError(
            "Estado declarativo no soportado para "
            f"'{requirement.requirement_id}': {status}"
        )

    return Article27ScoringRow(
        cycle_id=cycle["id"],
        cycle_name=cycle["name"],
        component_id=component["id"],
        component_name=component["name"],
        standard_id=standard["id"],
        standard_name=standard["name"],
        weight_percent=float(
            standard["weight_percent"]
        ),
        official_item_id=item["official_item_id"],
        description=item["description"],
        item_value=item_value,
        requirement_id=requirement.requirement_id,
        assessment_status=status,
        table_status=table_status,
        complies_fully=(
            table_status
            == Article27TableStatus.COMPLIES
        ),
        does_not_comply=(
            table_status
            == Article27TableStatus.DOES_NOT_COMPLY
        ),
        not_applicable=(
            table_status
            == Article27TableStatus.NOT_APPLICABLE
        ),
        score=score,
        comment=_build_assessment_comment(
            requirement
        ),
    )


def _build_not_applicable_row(
    *,
    cycle: dict,
    component: dict,
    standard: dict,
    item: dict,
    non_applicability_reason: str | None,
) -> Article27ScoringRow:
    item_value = float(item["item_value"])

    return Article27ScoringRow(
        cycle_id=cycle["id"],
        cycle_name=cycle["name"],
        component_id=component["id"],
        component_name=component["name"],
        standard_id=standard["id"],
        standard_name=standard["name"],
        weight_percent=float(
            standard["weight_percent"]
        ),
        official_item_id=item["official_item_id"],
        description=item["description"],
        item_value=item_value,
        requirement_id=None,
        assessment_status=None,
        table_status=(
            Article27TableStatus.NOT_APPLICABLE
        ),
        complies_fully=False,
        does_not_comply=False,
        not_applicable=True,
        score=item_value,
        comment=(
            "No aplica para el paquete de Estándares "
            "Mínimos seleccionado. "
            + (
                non_applicability_reason
                or (
                    "El ítem no forma parte de los "
                    "requisitos evaluados por este paquete "
                    "normativo."
                )
            )
        ),
    )


def _build_assessment_comment(
    requirement: RequirementReport,
) -> str:
    status = requirement.assessment_status

    if (
        status
        == DeclarativeAssessmentStatus.COMPLIES_AS_DECLARED
    ):
        return (
            requirement.assessment_explanation
            or (
                "Las declaraciones recopiladas permiten "
                "clasificar el requisito como cumplido "
                "según lo declarado."
            )
        )

    if (
        status
        == DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED
    ):
        negative_findings = [
            finding
            for finding in requirement.findings
            if (
                "situación negativa" in finding
                or "no satisfecha" in finding
            )
        ]

        if negative_findings:
            return " ".join(negative_findings)

        return (
            requirement.assessment_explanation
            or (
                "Las declaraciones recopiladas permiten "
                "identificar una condición requerida que "
                "no se encuentra satisfecha."
            )
        )

    if (
        status
        == DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
    ):
        information_findings = [
            finding
            for finding in requirement.findings
            if (
                "Falta información" in finding
                or "requiere aclaración" in finding
                or "No fue posible resolver" in finding
            )
        ]

        if information_findings:
            detail = " ".join(
                information_findings
            )
        elif requirement.missing_information:
            detail = (
                "Información pendiente: "
                + "; ".join(
                    requirement.missing_information
                )
            )
        else:
            detail = (
                requirement.assessment_explanation
                or (
                    "La información declarada no permite "
                    "confirmar el cumplimiento del requisito."
                )
            )

        return (
            "Información insuficiente. "
            f"{detail} "
            "Para efectos de la tabla de calificación, "
            "el ítem se registra como No cumple con "
            "puntaje cero, conservando internamente el "
            "estado de información insuficiente."
        )

    if (
        status
        == DeclarativeAssessmentStatus.NOT_APPLICABLE
    ):
        reason = (
            requirement.applicability_reason
            or requirement.assessment_explanation
            or (
                "El requisito fue determinado como no "
                "aplicable para el caso declarado."
            )
        )

        return f"No aplica. {reason}"

    raise ValueError(
        "No fue posible construir el comentario para "
        f"'{requirement.requirement_id}'."
    )


def _build_summary(
    rows: list[Article27ScoringRow],
) -> Article27ScoringSummary:
    evaluated_rows = [
        row
        for row in rows
        if row.requirement_id is not None
    ]

    return Article27ScoringSummary(
        total_items=len(rows),
        evaluated_items=len(evaluated_rows),
        not_applicable_items=sum(
            row.not_applicable
            for row in rows
        ),
        complies_items=sum(
            row.complies_fully
            for row in rows
        ),
        does_not_comply_items=sum(
            row.does_not_comply
            for row in rows
        ),
        insufficient_information_items=sum(
            row.assessment_status
            == DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            for row in rows
        ),
        total_score=round(
            sum(row.score for row in rows),
            2,
        ),
    )


def _validate_mapping_requirements(
    *,
    requirements_by_id: dict[str, RequirementReport],
    evaluated_mapping: dict[str, dict],
) -> None:
    mapped_requirement_ids = {
        mapped["requirement_id"]
        for mapped in evaluated_mapping.values()
    }

    missing_requirements = (
        mapped_requirement_ids
        - set(requirements_by_id)
    )

    if missing_requirements:
        raise ValueError(
            "El informe no contiene todos los requisitos "
            "esperados por el mapeo del artículo 27: "
            f"{sorted(missing_requirements)}"
        )


def _validate_rows(
    rows: list[Article27ScoringRow],
) -> None:
    if len(rows) != 60:
        raise ValueError(
            "La matriz del artículo 27 debe contener "
            f"60 ítems y contiene {len(rows)}."
        )

    ids = [
        row.official_item_id
        for row in rows
    ]

    if len(set(ids)) != 60:
        raise ValueError(
            "La matriz del artículo 27 contiene "
            "identificadores de ítem duplicados."
        )

    maximum_score = sum(
        row.item_value
        for row in rows
    )

    if abs(maximum_score - 100.0) > 1e-9:
        raise ValueError(
            "Los valores máximos de la matriz del "
            "artículo 27 no suman 100."
        )

    for row in rows:
        selected_columns = sum(
            (
                row.complies_fully,
                row.does_not_comply,
                row.not_applicable,
            )
        )

        if selected_columns != 1:
            raise ValueError(
                "Cada fila debe marcar exactamente una "
                "columna de calificación. "
                f"Ítem: {row.official_item_id}"
            )


def _load_json(
    path: Path,
) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)
