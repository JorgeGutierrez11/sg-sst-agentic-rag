from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RequirementApplicabilityStatus(StrEnum):
    """
    Estado de aplicabilidad de un requisito normativo.
    """

    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    UNDETERMINED = "undetermined"


class RequirementApplicabilityDecision(BaseModel):
    """
    Registra si un requisito resulta aplicable al caso empresarial.

    Este modelo es independiente del enrutamiento de preguntas.

    APPLICABLE:
        Existe una regla respaldada que indica que el requisito
        debe evaluarse para el caso analizado.

    NOT_APPLICABLE:
        Existe una regla respaldada que permite excluir el requisito
        para el caso concreto.

    UNDETERMINED:
        La información disponible no permite decidir todavía
        si el requisito aplica.

    Este modelo no determina cumplimiento o incumplimiento.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)
    status: RequirementApplicabilityStatus

    rule_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    normative_basis: str | None = None

    triggered_by: list[str] = Field(
        default_factory=list,
    )

    missing_information: list[str] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_decision(self):
        """
        Exige trazabilidad suficiente según el estado.
        """

        if self.status in {
            RequirementApplicabilityStatus.APPLICABLE,
            RequirementApplicabilityStatus.NOT_APPLICABLE,
        }:
            if not self.normative_basis:
                raise ValueError(
                    "Una decisión definitiva de aplicabilidad "
                    "debe registrar su fundamento normativo."
                )

        if (
            self.status
            == RequirementApplicabilityStatus.UNDETERMINED
            and not self.missing_information
        ):
            raise ValueError(
                "Una aplicabilidad no determinada debe indicar "
                "qué información hace falta."
            )

        return self