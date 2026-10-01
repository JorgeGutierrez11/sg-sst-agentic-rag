from agents.diagnostico_cumplimiento.catalog.schemas import (
    CatalogQuestionDefinition,
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


def interpret_text_boolean_answer(
    question: CatalogQuestionDefinition,
    answer: QuestionAnswer,
) -> AnswerInterpretation:
    """
    Interpreta únicamente respuestas textuales simples a preguntas
    de sí/no.

    Las respuestas complejas o ambiguas requieren aclaración.
    Esta función no determina cumplimiento normativo.
    """

    format_status = classify_boolean_answer(question, answer)

    if format_status != AnswerFormatStatus.NEEDS_INTERPRETATION:
        raise ValueError(
            "Se esperaba una respuesta textual a una pregunta de sí/no."
        )

    if not isinstance(answer.raw_answer, str):
        raise ValueError("Se esperaba una respuesta textual.")

    normalized = " ".join(answer.raw_answer.casefold().split())

    if normalized in {"sí", "si", "sí.", "si."}:
        status = InterpretationStatus.AFFIRMATIVE
        interpreted_value = True
        explanation = "El usuario respondió afirmativamente."

    elif normalized in {"no", "no."}:
        status = InterpretationStatus.NEGATIVE
        interpreted_value = False
        explanation = "El usuario respondió negativamente."

    elif normalized in {"no sé", "no se", "no sé.", "no se."}:
        status = InterpretationStatus.INSUFFICIENT_INFORMATION
        interpreted_value = None
        explanation = (
            "El usuario indicó que desconoce la respuesta."
        )

    else:
        status = InterpretationStatus.NEEDS_CLARIFICATION
        interpreted_value = None
        explanation = (
            "La respuesta textual requiere interpretación adicional "
            "o una aclaración del usuario."
        )

    return AnswerInterpretation(
        requirement_id=answer.requirement_id,
        question_id=answer.question_id,
        status=status,
        interpreted_value=interpreted_value,
        explanation=explanation,
    )
