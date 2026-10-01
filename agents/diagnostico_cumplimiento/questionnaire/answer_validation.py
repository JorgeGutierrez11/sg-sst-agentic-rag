from agents.diagnostico_cumplimiento.catalog.schemas import (
    CatalogRequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)


class AnswerReferenceError(ValueError):
    """La respuesta no corresponde al requisito o a sus preguntas."""


def validate_answer_reference(
    answer: QuestionAnswer,
    requirement: CatalogRequirementDefinition,
) -> None:
    """
    Comprueba que la respuesta corresponda a una pregunta
    existente dentro del requisito seleccionado.

    No interpreta raw_answer ni determina cumplimiento.
    """

    if answer.requirement_id != requirement.id:
        raise AnswerReferenceError(
            f"La respuesta corresponde al requisito "
            f"'{answer.requirement_id}', pero se está evaluando "
            f"'{requirement.id}'."
        )

    question_ids = {
        question.id
        for question in requirement.questions
    }

    if answer.question_id not in question_ids:
        raise AnswerReferenceError(
            f"La pregunta '{answer.question_id}' no existe "
            f"en el requisito '{requirement.id}'."
        )