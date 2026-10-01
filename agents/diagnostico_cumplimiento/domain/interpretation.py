
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InterpretationStatus(StrEnum):
    """Resultado de interpretar una respuesta de tipo sí/no."""

    AFFIRMATIVE = "affirmative"
    NEGATIVE = "negative"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    NEEDS_CLARIFICATION = "needs_clarification"
    INVALID_FORMAT = "invalid_format"


class AnswerInterpretation(BaseModel):
    """
    Interpretación estructurada de una respuesta.

    La respuesta original permanece almacenada por separado
    en QuestionAnswer.

    Este modelo no determina cumplimiento normativo.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)

    status: InterpretationStatus

    interpreted_value: bool | None = Field(
        default=None,
        description=(
            "Valor booleano interpretado. Debe ser None cuando "
            "la respuesta no permite establecer un sí o un no."
        ),
    )

    explanation: str = Field(
        min_length=1,
        description="Motivo de la interpretación registrada.",
    )

    @model_validator(mode="after")
    def validate_interpretation(self):
        if self.status == InterpretationStatus.AFFIRMATIVE:
            if self.interpreted_value is not True:
                raise ValueError(
                    "Una interpretación afirmativa requiere "
                    "interpreted_value=True."
                )

        elif self.status == InterpretationStatus.NEGATIVE:
            if self.interpreted_value is not False:
                raise ValueError(
                    "Una interpretación negativa requiere "
                    "interpreted_value=False."
                )

        elif self.interpreted_value is not None:
            raise ValueError(
                "Una respuesta no resuelta o con formato inválido "
                "debe tener interpreted_value=None."
            )

        return self
