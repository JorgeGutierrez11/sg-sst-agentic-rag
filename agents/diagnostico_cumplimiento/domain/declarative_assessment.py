from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents.diagnostico_cumplimiento.domain.requirement_applicability import (
    RequirementApplicabilityDecision,
    RequirementApplicabilityStatus,
)


class DeclarativeAssessmentStatus(StrEnum):
    """
    Estado orientativo de un requisito basado únicamente
    en la información declarada por la empresa.
    """

    COMPLIES_AS_DECLARED = "complies_as_declared"
    DOES_NOT_COMPLY_AS_DECLARED = "does_not_comply_as_declared"
    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class RequirementDeclarativeAssessment(BaseModel):
    """
    Resultado orientativo de un requisito basado en declaraciones.

    Este modelo no representa una verificación documental,
    auditoría, certificación ni determinación definitiva
    de cumplimiento normativo.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

    status: DeclarativeAssessmentStatus

    explanation: str = Field(min_length=1)

    applicability: RequirementApplicabilityDecision

    supporting_question_ids: list[str] = Field(
        default_factory=list,
    )

    missing_information: list[str] = Field(
        default_factory=list,
    )

    evidence_verified: Literal[False] = False

    requires_expert_validation: bool = True

    @model_validator(mode="after")
    def validate_assessment(self):
        """
        Protege la separación entre aplicabilidad y resultado
        declarativo.
        """

        if (
            self.status
            == DeclarativeAssessmentStatus.NOT_APPLICABLE
            and self.applicability.status
            != RequirementApplicabilityStatus.NOT_APPLICABLE
        ):
            raise ValueError(
                "El resultado 'not_applicable' solo puede utilizarse "
                "cuando la decisión de aplicabilidad del requisito "
                "también sea 'not_applicable'."
            )

        if (
            self.applicability.status
            == RequirementApplicabilityStatus.NOT_APPLICABLE
            and self.status
            != DeclarativeAssessmentStatus.NOT_APPLICABLE
        ):
            raise ValueError(
                "Un requisito determinado como no aplicable debe "
                "producir un resultado declarativo 'not_applicable'."
            )

        if (
            self.applicability.status
            == RequirementApplicabilityStatus.UNDETERMINED
            and self.status
            != DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
        ):
            raise ValueError(
                "Una aplicabilidad no determinada solo puede producir "
                "un resultado de información insuficiente."
            )

        if (
            self.status
            == DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            and not self.missing_information
        ):
            raise ValueError(
                "Un resultado de información insuficiente debe indicar "
                "qué información hace falta."
            )

        return self