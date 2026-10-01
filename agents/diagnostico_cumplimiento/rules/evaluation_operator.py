
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.enums import (
    QuestionType,
)
from agents.diagnostico_cumplimiento.domain.evaluation_rule import (
    ConditionEvaluationRule,
    EvaluationOperator,
)
from agents.diagnostico_cumplimiento.domain.interpretation import (
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.condition_answer_summary import (
    ConditionAnswerSummary,
)
from agents.diagnostico_cumplimiento.rules.evaluation_rule_validation import (
    EvaluationRuleReferenceError,
    validate_evaluation_rule_references,
)


class RuleLogicStatus(StrEnum):
    """Resultado lógico de combinar las respuestas de una regla."""

    ALL_AFFIRMATIVE = "all_affirmative"
    HAS_NEGATIVE = "has_negative"
    PENDING_INFORMATION = "pending_information"


class RuleLogicResult(BaseModel):
    """
    Resultado lógico de una regla.

    No representa una evaluación de cumplimiento normativo.
    """

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1)
    requirement_id: str = Field(min_length=1)
    condition_id: str = Field(min_length=1)

    status: RuleLogicStatus
    question_ids: list[str] = Field(min_length=1)


def evaluate_rule_logic(
    rule: ConditionEvaluationRule,
    requirement: RequirementDefinition,
    summary: ConditionAnswerSummary,
) -> RuleLogicResult:
    """
    Aplica el operador lógico a las respuestas interpretadas.

    Valida las referencias de la regla, comprueba que las
    preguntas sean booleanas y verifica la correspondencia
    entre la regla y el resumen de la condición.

    Las respuestas ausentes o no resueltas producen
    PENDING_INFORMATION.

    No evalúa cumplimiento normativo ni autoriza el uso
    de una regla que todavía esté en borrador.
    """

    validate_evaluation_rule_references(rule, requirement)

    if (
        summary.requirement_id != rule.requirement_id
        or summary.condition_id != rule.condition_id
    ):
        raise EvaluationRuleReferenceError(
            "El resumen no corresponde al requisito y la "
            "condición definidos en la regla."
        )

    questions_by_id = {
        question.id: question
        for question in requirement.questions
    }

    for question_id in rule.question_ids:
        if questions_by_id[question_id].type != QuestionType.BOOLEAN:
            raise ValueError(
                f"La pregunta '{question_id}' no es booleana "
                "y no puede utilizarse con ALL_AFFIRMATIVE."
            )

    if rule.operator != EvaluationOperator.ALL_AFFIRMATIVE:
        raise ValueError(
            f"Operador de evaluación no implementado: "
            f"'{rule.operator}'."
        )

    interpretations_by_id = {
        interpretation.question_id: interpretation
        for interpretation in summary.interpretations
    }

    values: list[bool] = []

    for question_id in rule.question_ids:
        interpretation = interpretations_by_id.get(question_id)

        if interpretation is None:
            status = RuleLogicStatus.PENDING_INFORMATION
            break

        if (
            interpretation.requirement_id != rule.requirement_id
            or interpretation.status
            not in {
                InterpretationStatus.AFFIRMATIVE,
                InterpretationStatus.NEGATIVE,
            }
        ):
            status = RuleLogicStatus.PENDING_INFORMATION
            break

        if interpretation.interpreted_value is None:
            status = RuleLogicStatus.PENDING_INFORMATION
            break

        values.append(interpretation.interpreted_value)

    else:
        if all(values):
            status = RuleLogicStatus.ALL_AFFIRMATIVE
        else:
            status = RuleLogicStatus.HAS_NEGATIVE

    return RuleLogicResult(
        rule_id=rule.id,
        requirement_id=rule.requirement_id,
        condition_id=rule.condition_id,
        status=status,
        question_ids=list(rule.question_ids),
    )
