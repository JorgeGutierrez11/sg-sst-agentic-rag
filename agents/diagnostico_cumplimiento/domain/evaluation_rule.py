
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluationOperator(StrEnum):
    """Operador lógico utilizado para combinar respuestas."""

    ALL_AFFIRMATIVE = "all_affirmative"


class RuleReviewStatus(StrEnum):
    """Estado de revisión de una regla de evaluación."""

    DRAFT = "draft"
    VALIDATED = "validated"


class ConditionEvaluationRule(BaseModel):
    """
    Define una regla de evaluación asociada a una condición.

    La regla identifica las preguntas utilizadas, el operador
    lógico y el criterio que deberá respaldar su aplicación.

    Su existencia no demuestra que el criterio normativo
    esté suficientemente representado por el cuestionario.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)

    requirement_id: str = Field(min_length=1)
    condition_id: str = Field(min_length=1)

    criterion_reference: str = Field(min_length=1)

    question_ids: list[str] = Field(min_length=1)

    operator: EvaluationOperator

    review_status: RuleReviewStatus = RuleReviewStatus.DRAFT

    @model_validator(mode="after")
    def validate_rule(self):
        if len(self.question_ids) != len(set(self.question_ids)):
            raise ValueError(
                "Una regla no puede utilizar la misma pregunta "
                "más de una vez."
            )

        if any(not question_id.strip() for question_id in self.question_ids):
            raise ValueError(
                "Las referencias a preguntas no pueden estar vacías."
            )

        return self
