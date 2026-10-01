
from agents.diagnostico_cumplimiento.domain.condition_evaluation import (
    ConditionEvaluation,
    ConditionEvaluationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.condition_answer_summary import (
    ConditionAnswerSummary,
)
from agents.diagnostico_cumplimiento.questionnaire.condition_progress import (
    ConditionCollectionStatus,
    determine_condition_collection_status,
)


def prepare_condition_evaluation(
    summary: ConditionAnswerSummary,
) -> ConditionEvaluation:
    """
    Determina si la recopilación de información permite
    avanzar hacia la evaluación de una condición.

    No aplica criterios normativos ni determina cumplimiento.

    Una condición con todas sus respuestas interpretadas
    permanece NOT_EVALUATED hasta que se implemente y
    valide una regla de evaluación específica.
    """

    collection_status = determine_condition_collection_status(
        summary,
    )

    if (
        collection_status
        == ConditionCollectionStatus.ANSWERS_INTERPRETED
    ):
        return ConditionEvaluation(
            requirement_id=summary.requirement_id,
            condition_id=summary.condition_id,
            status=ConditionEvaluationStatus.NOT_EVALUATED,
            explanation=(
                "Todas las respuestas registradas para la condición "
                "han sido interpretadas. Está pendiente aplicar "
                "un criterio de evaluación explícito y validado."
            ),
        )

    return ConditionEvaluation(
        requirement_id=summary.requirement_id,
        condition_id=summary.condition_id,
        status=ConditionEvaluationStatus.PENDING_INFORMATION,
        explanation=(
            "La condición tiene preguntas sin responder o respuestas "
            "que requieren aclaración antes de continuar "
            "con su evaluación."
        ),
    )
