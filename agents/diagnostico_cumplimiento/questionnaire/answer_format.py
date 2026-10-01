
from enum import StrEnum

from agents.diagnostico_cumplimiento.catalog.schemas import (
    CatalogQuestionDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.enums import QuestionType


class AnswerFormatStatus(StrEnum):
    STRUCTURED = "structured"
    NEEDS_INTERPRETATION = "needs_interpretation"
    INVALID_FORMAT = "invalid_format"


def classify_boolean_answer(
    question: CatalogQuestionDefinition,
    answer: QuestionAnswer,
) -> AnswerFormatStatus:
    """
    Clasifica el formato de la respuesta a una pregunta de sí/no.

    No interpreta el significado del texto ni determina
    el cumplimiento de ninguna condición normativa.
    """

    if question.type != QuestionType.BOOLEAN:
        raise ValueError(
            "Esta función únicamente admite preguntas de tipo boolean."
        )

    if answer.question_id != question.id:
        raise ValueError(
            "La respuesta no corresponde a la pregunta suministrada."
        )

    raw_answer = answer.raw_answer

    if isinstance(raw_answer, bool):
        return AnswerFormatStatus.STRUCTURED

    if isinstance(raw_answer, str):
        return AnswerFormatStatus.NEEDS_INTERPRETATION

    return AnswerFormatStatus.INVALID_FORMAT
