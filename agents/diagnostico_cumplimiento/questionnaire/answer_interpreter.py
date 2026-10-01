from agents.diagnostico_cumplimiento.catalog.schemas import (
    CatalogRequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.interpretation import (
    AnswerInterpretation,
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_format import (
    AnswerFormatStatus,
    classify_boolean_answer,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_validation import (
    validate_answer_reference,
)
from agents.diagnostico_cumplimiento.questionnaire.boolean_interpreter import (
    interpret_structured_boolean_answer,
)
from agents.diagnostico_cumplimiento.questionnaire.text_boolean_interpreter import (
    interpret_text_boolean_answer,
)

from typing import Any

from agents.diagnostico_cumplimiento.questionnaire.llm_boolean_interpreter import (
    interpret_boolean_answer_with_llm,
)


def interpret_boolean_answer(
    requirement: CatalogRequirementDefinition,
    answer: QuestionAnswer,
) -> AnswerInterpretation:
    """
    Interpreta una respuesta a una pregunta de tipo sí/no.

    Comprueba que la respuesta corresponda al requisito y a
    una de sus preguntas. Después selecciona el intérprete
    adecuado según el formato de la respuesta.

    No determina cumplimiento ni asigna puntajes.
    """

    validate_answer_reference(answer, requirement)

    question = next(
        question
        for question in requirement.questions
        if question.id == answer.question_id
    )

    format_status = classify_boolean_answer(question, answer)

    if format_status == AnswerFormatStatus.STRUCTURED:
        return interpret_structured_boolean_answer(
            question,
            answer,
        )

    if format_status == AnswerFormatStatus.NEEDS_INTERPRETATION:
        return interpret_text_boolean_answer(
            question,
            answer,
        )

    return AnswerInterpretation(
        requirement_id=answer.requirement_id,
        question_id=answer.question_id,
        status=InterpretationStatus.INVALID_FORMAT,
        interpreted_value=None,
        explanation=(
            "El formato de la respuesta no corresponde "
            "a una pregunta de tipo sí/no."
        ),
    )

def interpret_boolean_answer_hybrid(
    requirement: CatalogRequirementDefinition,
    answer: QuestionAnswer,
    *,
    llm: Any | None = None,
) -> AnswerInterpretation:
    """
    Interpreta respuestas booleanas usando primero reglas
    determinísticas y recurriendo al LLM solo cuando sea necesario.

    El LLM interpreta la declaración del usuario.
    No determina cumplimiento normativo.
    """

    deterministic_result = interpret_boolean_answer(
        requirement,
        answer,
    )

    if (
        deterministic_result.status
        != InterpretationStatus.NEEDS_CLARIFICATION
    ):
        return deterministic_result

    question = next(
        question
        for question in requirement.questions
        if question.id == answer.question_id
    )

    try:
        return interpret_boolean_answer_with_llm(
            question,
            answer,
            llm=llm,
        )
    except Exception:
        # El LLM es auxiliar. Si no está disponible,
        # se conserva el resultado determinístico para
        # solicitar aclaración al usuario.
        return deterministic_result
