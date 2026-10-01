
from enum import StrEnum

from agents.diagnostico_cumplimiento.questionnaire.condition_answer_summary import (
    ConditionAnswerSummary,
)


class ConditionCollectionStatus(StrEnum):
    """Estado de recopilación de respuestas de una condición."""

    NOT_STARTED = "not_started"
    PARTIAL = "partial"
    NEEDS_RESOLUTION = "needs_resolution"
    ANSWERS_INTERPRETED = "answers_interpreted"


def determine_condition_collection_status(
    summary: ConditionAnswerSummary,
) -> ConditionCollectionStatus:
    """
    Determina el avance de la recopilación de información.

    No evalúa el cumplimiento de la condición normativa
    ni determina si la evidencia es suficiente.
    """

    if not (
        summary.interpretations
        or summary.unanswered_question_ids
        or summary.unresolved_question_ids
    ):
        raise ValueError(
            f"La condición '{summary.condition_id}' no tiene "
            "preguntas registradas en el resumen."
        )

    if summary.unresolved_question_ids:
        return ConditionCollectionStatus.NEEDS_RESOLUTION

    if summary.unanswered_question_ids:
        if summary.interpretations:
            return ConditionCollectionStatus.PARTIAL

        return ConditionCollectionStatus.NOT_STARTED

    return ConditionCollectionStatus.ANSWERS_INTERPRETED
