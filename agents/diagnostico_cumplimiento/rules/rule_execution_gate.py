
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.evaluation_rule import (
    ConditionEvaluationRule,
    RuleReviewStatus,
)
from agents.diagnostico_cumplimiento.rules.evaluation_rule_validation import (
    validate_evaluation_rule_references,
)


class RuleExecutionStatus(StrEnum):
    """Estado de autorización para la evaluación normativa."""

    BLOCKED_DRAFT = "blocked_draft"
    BLOCKED_PENDING_COVERAGE = "blocked_pending_coverage"


class RuleExecutionDecision(BaseModel):
    """Decisión sobre el uso normativo de una regla."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1)
    status: RuleExecutionStatus
    authorized: bool = False
    explanation: str = Field(min_length=1)


def check_rule_execution_readiness(
    rule: ConditionEvaluationRule,
    requirement: RequirementDefinition,
) -> RuleExecutionDecision:
    """
    Comprueba si una regla puede utilizarse para evaluar
    normativamente una condición.

    Valida primero sus referencias.

    Hasta que exista un mecanismo de validación experta
    y cobertura normativa, ninguna regla queda autorizada.
    """

    validate_evaluation_rule_references(rule, requirement)

    if rule.review_status == RuleReviewStatus.DRAFT:
        return RuleExecutionDecision(
            rule_id=rule.id,
            status=RuleExecutionStatus.BLOCKED_DRAFT,
            authorized=False,
            explanation=(
                "La regla está en borrador y requiere revisión "
                "antes de utilizarse para una evaluación normativa."
            ),
        )

    return RuleExecutionDecision(
        rule_id=rule.id,
        status=RuleExecutionStatus.BLOCKED_PENDING_COVERAGE,
        authorized=False,
        explanation=(
            "La regla tiene el estado de revisión VALIDATED, "
            "pero todavía no se ha verificado que sus preguntas "
            "representen suficientemente el criterio normativo "
            "ni se ha registrado la autorización de ejecución."
        ),
    )
