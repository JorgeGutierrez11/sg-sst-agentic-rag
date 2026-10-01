import json
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from agents.consulta_normativa.langchain_rag.core.llm import (
    build_deepseek_llm,
    invoke_llm_text,
)
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


class LLMBooleanInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: InterpretationStatus
    interpreted_value: bool | None
    explanation: str


def interpret_boolean_answer_with_llm(
    question: CatalogQuestionDefinition,
    answer: QuestionAnswer,
    *,
    llm: Any | None = None,
) -> AnswerInterpretation:
    """
    Interpreta una respuesta textual compleja mediante LLM.

    El LLM únicamente interpreta lo declarado por el usuario.
    No determina cumplimiento normativo, aplicabilidad ni puntajes.
    """

    if not isinstance(answer.raw_answer, str):
        raise ValueError(
            "El intérprete LLM únicamente acepta respuestas textuales."
        )

    model = llm or build_deepseek_llm()

    messages = [
        (
            "system",
            """
Eres un componente de interpretación de respuestas dentro de un
cuestionario de Seguridad y Salud en el Trabajo.

Tu única tarea es interpretar la respuesta del usuario respecto de
la pregunta formulada.

NO debes:
- determinar cumplimiento normativo;
- interpretar leyes;
- añadir información no declarada;
- asumir hechos;
- recomendar acciones.

Estados permitidos:

affirmative:
La respuesta permite concluir claramente que la respuesta a la
pregunta es sí.


negative:
La respuesta permite concluir que la respuesta a la pregunta es no.
También corresponde a negative cuando el usuario declara explícitamente
una excepción que hace falsa la afirmación preguntada.

Ejemplo:
Pregunta: "¿Todas las personas trabajadoras están afiliadas?"
Respuesta: "4 de 5 están afiliadas; falta una."
Resultado: negative.

needs_clarification:
La respuesta es realmente ambigua, contradictoria o no permite
establecer si la afirmación preguntada es verdadera o falsa.
También usa needs_clarification cuando la respuesta dependa de una
condición temporal o de aplicabilidad que no esté suficientemente resuelta.

Ejemplo:
Pregunta: "¿Dispone de comprobantes de los pagos correspondientes,
cuando corresponda?"
Respuesta: "No tengo el de este mes porque todavía no es fecha de pago."
Resultado: needs_clarification.

En este caso no concluyas negative únicamente por la ausencia del
documento del periodo aún no exigible. Debe aclararse si existen los
comprobantes correspondientes a los periodos cuyo pago ya debía haberse
realizado.

No uses needs_clarification solo porque la situación sea parcial.
Si la información parcial ya demuestra que la afirmación preguntada
es falsa, usa negative.

insufficient_information:
El usuario declara que no sabe, no recuerda, no dispone de la
información o no puede confirmar el hecho.

needs_clarification:
La respuesta es ambigua, contradictoria, parcial, condicional o
requiere una pregunta adicional antes de poder convertirla en sí/no.

Interpreta la respuesta respecto de la semántica exacta de la pregunta.

Si la pregunta exige que una condición se cumpla para todas las personas
o para todos los elementos correspondientes, una excepción explícita
es suficiente para interpretar la respuesta como negative.

No solicites aclaración cuando el propio usuario ya proporcionó
información suficiente para resolver sí/no.

Devuelve EXCLUSIVAMENTE JSON válido con esta estructura:

{
  "status": "affirmative | negative | insufficient_information | needs_clarification",
  "interpreted_value": true | false | null,
  "explanation": "explicación breve"
}

Reglas obligatorias:
- affirmative -> interpreted_value=true
- negative -> interpreted_value=false
- insufficient_information -> interpreted_value=null
- needs_clarification -> interpreted_value=null
""".strip(),
        ),
        (
            "human",
            (
                f"Pregunta:\n{question.text}\n\n"
                f"Respuesta del usuario:\n{answer.raw_answer}"
            ),
        ),
    ]

    raw_response = invoke_llm_text(
        model,
        messages,
    )

    parsed = _parse_llm_response(raw_response)

    return AnswerInterpretation(
        requirement_id=answer.requirement_id,
        question_id=answer.question_id,
        status=parsed.status,
        interpreted_value=parsed.interpreted_value,
        explanation=parsed.explanation,
    )


def _parse_llm_response(
    raw_response: str,
) -> LLMBooleanInterpretation:
    """
    Valida estrictamente la respuesta estructurada del LLM.
    """

    text = raw_response.strip()

    if text.startswith("```"):
        text = _remove_markdown_fence(text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "DeepSeek no devolvió JSON válido."
        ) from error

    try:
        result = LLMBooleanInterpretation.model_validate(data)
    except ValidationError as error:
        raise ValueError(
            "La respuesta estructurada de DeepSeek "
            "no cumple el esquema esperado."
        ) from error

    _validate_interpretation_consistency(result)

    return result


def _remove_markdown_fence(text: str) -> str:
    lines = text.splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _validate_interpretation_consistency(
    result: LLMBooleanInterpretation,
) -> None:
    if (
        result.status == InterpretationStatus.AFFIRMATIVE
        and result.interpreted_value is not True
    ):
        raise ValueError(
            "Interpretación inconsistente: affirmative requiere True."
        )

    if (
        result.status == InterpretationStatus.NEGATIVE
        and result.interpreted_value is not False
    ):
        raise ValueError(
            "Interpretación inconsistente: negative requiere False."
        )

    if (
        result.status
        in {
            InterpretationStatus.NEEDS_CLARIFICATION,
            InterpretationStatus.INSUFFICIENT_INFORMATION,
        }
        and result.interpreted_value is not None
    ):
        raise ValueError(
            "La interpretación no resolutiva debe tener valor None."
        )