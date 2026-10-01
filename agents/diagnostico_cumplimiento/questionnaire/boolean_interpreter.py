
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


def interpret_structured_boolean_answer(
    question: CatalogQuestionDefinition,
    answer: QuestionAnswer,
) -> AnswerInterpretation:
    """
    Interpreta únicamente respuestas booleanas directas.

    No interpreta texto libre ni evalúa cumplimiento normativo.
    """

    format_status = classify_boolean_answer(question, answer)

    if format_status != AnswerFormatStatus.STRUCTURED:
        raise ValueError(
            "La respuesta no es un booleano directo. "
            "Debe procesarse mediante el intérprete correspondiente."
        )

    # classify_boolean_answer ya comprobó el formato.
    # Esta verificación explícita mantiene el tipo correcto.
    if not isinstance(answer.raw_answer, bool):
        raise ValueError("Se esperaba una respuesta booleana.")

    if answer.raw_answer:
        status = InterpretationStatus.AFFIRMATIVE
        explanation = "El usuario seleccionó una respuesta afirmativa."
    else:
        status = InterpretationStatus.NEGATIVE
        explanation = "El usuario seleccionó una respuesta negativa."

    return AnswerInterpretation(
        requirement_id=answer.requirement_id,
        question_id=answer.question_id,
        status=status,
        interpreted_value=answer.raw_answer,
        explanation=explanation,
    )
