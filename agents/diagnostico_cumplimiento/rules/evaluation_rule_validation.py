
from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.evaluation_rule import (
    ConditionEvaluationRule,
)


class EvaluationRuleReferenceError(ValueError):
    """Una regla contiene referencias incompatibles con el requisito."""


def validate_evaluation_rule_references(
    rule: ConditionEvaluationRule,
    requirement: RequirementDefinition,
) -> None:
    """
    Valida las referencias de una regla contra el catálogo.

    Comprueba que el requisito, la condición y las preguntas
    correspondan entre sí.

    No valida el contenido normativo del criterio ni autoriza
    la ejecución de la regla.
    """

    if rule.requirement_id != requirement.id:
        raise EvaluationRuleReferenceError(
            f"La regla '{rule.id}' pertenece al requisito "
            f"'{rule.requirement_id}', no a '{requirement.id}'."
        )

    condition_ids = {
        condition.id
        for condition in requirement.conditions
    }

    if rule.condition_id not in condition_ids:
        raise EvaluationRuleReferenceError(
            f"La condición '{rule.condition_id}' de la regla "
            f"'{rule.id}' no existe en el requisito."
        )

    questions_by_id = {
        question.id: question
        for question in requirement.questions
    }

    for question_id in rule.question_ids:
        question = questions_by_id.get(question_id)

        if question is None:
            raise EvaluationRuleReferenceError(
                f"La pregunta '{question_id}' de la regla "
                f"'{rule.id}' no existe en el requisito."
            )

        if question.condition_id != rule.condition_id:
            raise EvaluationRuleReferenceError(
                f"La pregunta '{question_id}' pertenece a la "
                f"condición '{question.condition_id}', no a "
                f"'{rule.condition_id}'."
            )
