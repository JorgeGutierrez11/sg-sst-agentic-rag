
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConditionEvaluationStatus(StrEnum):
    """Resultado de la evaluación de una condición."""

    NOT_EVALUATED = "not_evaluated"
    PENDING_INFORMATION = "pending_information"
    SATISFIED_AS_DECLARED = "satisfied_as_declared"
    NOT_SATISFIED_AS_DECLARED = "not_satisfied_as_declared"


class ConditionEvaluation(BaseModel):
    """
    Resultado de evaluar una condición con información declarada.

    Los resultados favorables o desfavorables requieren un
    criterio explícito y referencias a las preguntas utilizadas.

    Este modelo no representa una certificación de cumplimiento.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)
    condition_id: str = Field(min_length=1)

    status: ConditionEvaluationStatus

    explanation: str = Field(min_length=1)

    criterion_reference: str | None = None

    evaluated_question_ids: list[str] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_evaluation(self):
        evaluated_statuses = {
            ConditionEvaluationStatus.SATISFIED_AS_DECLARED,
            ConditionEvaluationStatus.NOT_SATISFIED_AS_DECLARED,
        }

        if len(self.evaluated_question_ids) != len(
            set(self.evaluated_question_ids)
        ):
            raise ValueError(
                "Una pregunta no puede repetirse en las referencias "
                "de la evaluación."
            )

        if self.status in evaluated_statuses:
            if (
                self.criterion_reference is None
                or not self.criterion_reference.strip()
            ):
                raise ValueError(
                    "Una condición evaluada requiere una referencia "
                    "al criterio aplicado."
                )

            if not self.evaluated_question_ids:
                raise ValueError(
                    "Una condición evaluada debe identificar "
                    "las preguntas utilizadas."
                )

        else:
            if self.criterion_reference is not None:
                raise ValueError(
                    "Una condición no evaluada no debe registrar "
                    "un criterio como si ya se hubiera aplicado."
                )

            if self.evaluated_question_ids:
                raise ValueError(
                    "Una condición no evaluada no debe registrar "
                    "preguntas como evaluadas."
                )

        return self
