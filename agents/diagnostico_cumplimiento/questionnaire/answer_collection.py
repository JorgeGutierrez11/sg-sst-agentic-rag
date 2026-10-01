
from agents.diagnostico_cumplimiento.catalog.schemas import (
    CatalogRequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_validation import (
    validate_answer_reference,
)


class DuplicateAnswerError(ValueError):
    """Una pregunta tiene más de una respuesta registrada."""


def collect_requirement_answers(
    requirement: CatalogRequirementDefinition,
    answers: list[QuestionAnswer],
) -> dict[str, QuestionAnswer]:
    """
    Organiza las respuestas de un requisito por identificador de pregunta.

    Valida que cada respuesta pertenezca al requisito y que no
    existan respuestas duplicadas.

    Las preguntas sin responder no se agregan al resultado.
    No interpreta respuestas ni determina cumplimiento.
    """

    collected: dict[str, QuestionAnswer] = {}

    for answer in answers:
        validate_answer_reference(answer, requirement)

        if answer.question_id in collected:
            raise DuplicateAnswerError(
                f"La pregunta '{answer.question_id}' tiene "
                "más de una respuesta registrada."
            )

        collected[answer.question_id] = answer

    return collected



def get_unanswered_questions(
    requirement: CatalogRequirementDefinition,
    answers: list[QuestionAnswer],
) -> list:
    """
    Devuelve las preguntas que todavía no tienen una respuesta registrada.

    Conserva el orden definido en el catálogo.
    No interpreta las respuestas ni determina cumplimiento.
    """
    collected = collect_requirement_answers(requirement, answers)

    return [
        question
        for question in requirement.questions
        if question.id not in collected
    ]
