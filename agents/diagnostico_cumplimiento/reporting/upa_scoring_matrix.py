from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    DeclarativeAssessmentStatus,
)
from agents.diagnostico_cumplimiento.reporting.orientative_report import (
    OrientativeReport,
    RequirementReport,
)


DATA_DIR = Path(__file__).resolve().parent / "data"

UPA_1_10_CATALOG_ID = (
    "res0312_riesgo_i_1_10_agropecuaria"
)

DEFAULT_UPA_SCORING_PATH = (
    DATA_DIR
    / "res0312_upa_1_10_scoring.json"
)


class UPATableStatus(StrEnum):
    """
    Estados visibles en la tabla especial de UPA.

    El sistema oficial contempla también cumplimiento
    parcial, pero el Agente 2 todavía no deriva ese estado
    automáticamente.
    """

    COMPLIES_FULLY = "complies_fully"
    COMPLIES_PARTIALLY = "complies_partially"
    DOES_NOT_COMPLY = "does_not_comply"
    NOT_APPLICABLE = "not_applicable"


class UPAScoringRow(BaseModel):
    """
    Resultado de uno de los tres Estándares Mínimos
    aplicables a UPA de diez (10) o menos trabajadores
    permanentes.
    """

    model_config = ConfigDict(extra="forbid")

    order: int

    requirement_id: str
    name: str

    maximum_score: float

    assessment_status: DeclarativeAssessmentStatus

    table_status: UPATableStatus

    complies_fully: bool
    complies_partially: bool
    does_not_comply: bool
    not_applicable: bool

    score: float

    comment: str


class UPAScoringSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_standards: int

    complies_fully_standards: int
    complies_partially_standards: int
    does_not_comply_standards: int
    not_applicable_standards: int

    insufficient_information_standards: int

    total_score: float
    maximum_score: float = 100.0


class UPAScoringMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scoring_id: str
    catalog_id: str

    rows: list[UPAScoringRow] = Field(
        min_length=3,
        max_length=3,
    )

    summary: UPAScoringSummary


def build_upa_scoring_matrix(
    report: OrientativeReport,
    *,
    scoring_path: Path = DEFAULT_UPA_SCORING_PATH,
) -> UPAScoringMatrix:
    """
    Construye la matriz especial de calificación para
    Unidades de Producción Agropecuaria de diez (10)
    o menos trabajadores permanentes.

    Esta función no vuelve a evaluar requisitos.
    Utiliza los resultados declarativos ya calculados
    por el Agente 2.
    """

    if report.catalog_id != UPA_1_10_CATALOG_ID:
        raise ValueError(
            "La matriz UPA solo puede utilizarse con "
            f"el catálogo {UPA_1_10_CATALOG_ID!r}. "
            f"Se recibió {report.catalog_id!r}."
        )

    scoring = _load_json(
        scoring_path
    )

    if scoring["catalog_id"] != report.catalog_id:
        raise ValueError(
            "La configuración de calificación UPA "
            "no corresponde al catálogo utilizado "
            "por el diagnóstico."
        )

    requirements_by_id = {
        requirement.requirement_id: requirement
        for requirement in report.requirements
    }

    expected_requirement_ids = {
        standard["requirement_id"]
        for standard in scoring["standards"]
    }

    report_requirement_ids = set(
        requirements_by_id
    )

    missing_requirements = (
        expected_requirement_ids
        - report_requirement_ids
    )

    unexpected_requirements = (
        report_requirement_ids
        - expected_requirement_ids
    )

    if missing_requirements:
        raise ValueError(
            "El informe UPA no contiene todos los "
            "estándares esperados: "
            f"{sorted(missing_requirements)}"
        )

    if unexpected_requirements:
        raise ValueError(
            "El informe UPA contiene requisitos no "
            "definidos en la configuración de "
            "calificación: "
            f"{sorted(unexpected_requirements)}"
        )

    rows = [
        _build_scoring_row(
            standard=standard,
            requirement=requirements_by_id[
                standard["requirement_id"]
            ],
        )
        for standard in scoring["standards"]
    ]

    _validate_rows(
        rows
    )

    summary = _build_summary(
        rows
    )

    return UPAScoringMatrix(
        scoring_id=scoring["scoring_id"],
        catalog_id=scoring["catalog_id"],
        rows=rows,
        summary=summary,
    )


def _build_scoring_row(
    *,
    standard: dict,
    requirement: RequirementReport,
) -> UPAScoringRow:
    status = requirement.assessment_status

    if status is None:
        raise ValueError(
            "El requisito "
            f"{requirement.requirement_id!r} "
            "no tiene resultado declarativo."
        )

    maximum_score = float(
        standard["maximum_score"]
    )

    if (
        status
        == DeclarativeAssessmentStatus.COMPLIES_AS_DECLARED
    ):
        table_status = (
            UPATableStatus.COMPLIES_FULLY
        )
        score = maximum_score

    elif (
        status
        == DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED
    ):
        table_status = (
            UPATableStatus.DOES_NOT_COMPLY
        )
        score = 0.0

    elif (
        status
        == DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
    ):
        # El sistema oficial contempla cumplimiento
        # parcial, pero el Agente 2 no debe inferirlo
        # a partir de información incompleta.
        #
        # Para la salida numérica se mantiene la
        # política conservadora utilizada en la tabla
        # del artículo 27: puntaje cero.
        table_status = (
            UPATableStatus.DOES_NOT_COMPLY
        )
        score = 0.0

    elif (
        status
        == DeclarativeAssessmentStatus.NOT_APPLICABLE
    ):
        # Los tres estándares del artículo 7 forman
        # parte del paquete UPA completo. Actualmente
        # no existe una regla normativa implementada
        # que permita excluir individualmente alguno.
        raise ValueError(
            "El requisito UPA "
            f"{requirement.requirement_id!r} "
            "fue clasificado como No aplica, pero "
            "el Agente 2 no tiene una regla de "
            "no aplicabilidad implementada para los "
            "tres estándares del artículo 7."
        )

    else:
        raise ValueError(
            "Estado declarativo no soportado para "
            f"{requirement.requirement_id!r}: "
            f"{status}"
        )

    return UPAScoringRow(
        order=int(
            standard["order"]
        ),
        requirement_id=(
            requirement.requirement_id
        ),
        name=standard["name"],
        maximum_score=maximum_score,
        assessment_status=status,
        table_status=table_status,
        complies_fully=(
            table_status
            == UPATableStatus.COMPLIES_FULLY
        ),
        complies_partially=(
            table_status
            == UPATableStatus.COMPLIES_PARTIALLY
        ),
        does_not_comply=(
            table_status
            == UPATableStatus.DOES_NOT_COMPLY
        ),
        not_applicable=(
            table_status
            == UPATableStatus.NOT_APPLICABLE
        ),
        score=score,
        comment=_build_comment(
            requirement
        ),
    )


def _build_comment(
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
                "clasificar el estándar como cumplido "
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
            return " ".join(
                negative_findings
            )

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
                    "confirmar el cumplimiento del estándar."
                )
            )

        return (
            "Información insuficiente. "
            f"{detail} "
            "No se infiere cumplimiento parcial. "
            "Para la calificación automática el estándar "
            "se mantiene con puntaje cero."
        )

    raise ValueError(
        "No fue posible construir el comentario para "
        f"{requirement.requirement_id!r}."
    )


def _build_summary(
    rows: list[UPAScoringRow],
) -> UPAScoringSummary:
    return UPAScoringSummary(
        total_standards=len(rows),
        complies_fully_standards=sum(
            row.complies_fully
            for row in rows
        ),
        complies_partially_standards=sum(
            row.complies_partially
            for row in rows
        ),
        does_not_comply_standards=sum(
            row.does_not_comply
            for row in rows
        ),
        not_applicable_standards=sum(
            row.not_applicable
            for row in rows
        ),
        insufficient_information_standards=sum(
            row.assessment_status
            == DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            for row in rows
        ),
        total_score=round(
            sum(
                row.score
                for row in rows
            ),
            2,
        ),
    )


def _validate_rows(
    rows: list[UPAScoringRow],
) -> None:
    if len(rows) != 3:
        raise ValueError(
            "La matriz UPA debe contener exactamente "
            f"3 estándares y contiene {len(rows)}."
        )

    requirement_ids = [
        row.requirement_id
        for row in rows
    ]

    if len(set(requirement_ids)) != 3:
        raise ValueError(
            "La matriz UPA contiene identificadores "
            "de requisito duplicados."
        )

    maximum_score = sum(
        row.maximum_score
        for row in rows
    )

    if abs(
        maximum_score - 100.0
    ) > 1e-9:
        raise ValueError(
            "Los valores máximos de la matriz UPA "
            "deben sumar 100 y suman "
            f"{maximum_score}."
        )


def _load_json(
    path: Path,
) -> dict:
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(
            file
        )
