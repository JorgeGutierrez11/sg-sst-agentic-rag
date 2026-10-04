from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    DeclarativeAssessmentStatus,
)

from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementSource,
)
from agents.diagnostico_cumplimiento.reporting.orientative_report import (
    OrientativeReport,
)

class NormativeGapCandidate(BaseModel):
    """
    Requisito del diagnóstico que requiere atención y que será
    utilizado para construir el análisis orientativo de la brecha.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

    official_item_id: str | None = None

    requirement_name: str = Field(min_length=1)

    status: DeclarativeAssessmentStatus

    assessment_explanation: str = Field(min_length=1)

    findings: list[str] = Field(
        default_factory=list,
    )

    missing_information: list[str] = Field(
        default_factory=list,
    )

    official_criterion: str = Field(min_length=1)

    official_verification_method: str | None = None

    verification_method_source: str = Field(min_length=1)

    suggested_actions: list[str] = Field(
        default_factory=list,
    )

    catalog_source: RequirementSource

class NormativeGapSource(BaseModel):
    """
    Fuente normativa del catálogo utilizada para sustentar
    el análisis de una brecha.
    """

    model_config = ConfigDict(extra="forbid")

    norm: str = Field(min_length=1)

    reference: str = Field(min_length=1)

    url: str | None = None


class NormativeGapFinding(BaseModel):
    """
    Brecha identificada a partir del diagnóstico declarativo
    y sustentada con la información normativa del catálogo.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

    official_item_id: str | None = None

    requirement_name: str = Field(min_length=1)

    status: DeclarativeAssessmentStatus

    finding_reason: str = Field(min_length=1)

    normative_requirement: str = Field(min_length=1)

    orientative_action: str = Field(min_length=1)

    sources: list[NormativeGapSource] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_gap_status(self):
        allowed_statuses = {
            DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED,
            DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION,
        }

        if self.status not in allowed_statuses:
            raise ValueError(
                "Una brecha normativa solo puede construirse para "
                "requisitos que no cumplen según lo declarado o que "
                "presentan información insuficiente."
            )

        return self


class NormativeGapAnalysis(BaseModel):
    """
    Resultado del análisis de los requisitos que requieren atención.
    """

    model_config = ConfigDict(extra="forbid")

    findings: list[NormativeGapFinding] = Field(
        default_factory=list,
    )


def build_normative_gap_candidates(
    report: OrientativeReport,
) -> list[NormativeGapCandidate]:
    """
    Selecciona los requisitos del diagnóstico que requieren atención.

    No realiza recuperación normativa, no invoca LLM y no modifica
    el resultado declarativo del diagnóstico.
    """

    attention_statuses = {
        DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED,
        DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION,
    }

    candidates: list[NormativeGapCandidate] = []

    for requirement in report.requirements:
        if requirement.assessment_status not in attention_statuses:
            continue

        if requirement.assessment_explanation is None:
            raise ValueError(
                "Un requisito que requiere atención debe contener "
                "assessment_explanation: "
                f"{requirement.requirement_id}"
            )

        candidates.append(
            NormativeGapCandidate(
                requirement_id=requirement.requirement_id,
                official_item_id=requirement.official_item_id,
                requirement_name=requirement.name,
                status=requirement.assessment_status,
                assessment_explanation=(
                    requirement.assessment_explanation
                ),
                findings=list(requirement.findings),
                missing_information=list(
                    requirement.missing_information
                ),
                official_criterion=requirement.official_criterion,

                official_verification_method=(
                    requirement.official_verification_method
                ),
                verification_method_source=(
                    requirement.verification_method_source
                ),
                suggested_actions=list(
                    requirement.suggested_actions
                ),

                catalog_source=requirement.source,
            )
        )

    return candidates