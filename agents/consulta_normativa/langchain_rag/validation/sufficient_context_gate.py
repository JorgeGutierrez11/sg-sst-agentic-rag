"""LLM-based sufficient-context gate for normative RAG."""

import logging
from collections.abc import Callable
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState

logger = logging.getLogger(__name__)


class ContextSufficiency(str, Enum):
    """Possible sufficiency levels for the retrieved context."""

    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"


class SufficientContextGrade(BaseModel):
    """Structured assessment of whether the context can answer the question."""

    level: ContextSufficiency = Field(
        description=(
            "Whether the retrieved context is sufficient, partially sufficient, "
            "or insufficient to answer the user's original question."
        )
    )

    reason: str = Field(
        description=(
            "Brief explanation of the sufficiency decision based only on "
            "the user's question and the retrieved context."
        )
    )

    missing_information: list[str] = Field(
        default_factory=list,
        description=(
            "Specific information requested by the user that is not supported "
            "by the retrieved context. Empty when the context is sufficient."
        ),
    )


SUFFICIENT_CONTEXT_SYSTEM_PROMPT = """
Eres un evaluador de suficiencia de contexto para un sistema RAG de consulta
normativa sobre el Sistema de Gestión de Seguridad y Salud en el Trabajo
(SG-SST) en Colombia.

Tu única tarea es determinar si el CONTEXTO RECUPERADO contiene evidencia
suficiente para responder la PREGUNTA ORIGINAL DEL USUARIO.

Debes evaluar el contexto completo como un conjunto. La información necesaria
puede estar distribuida entre varios fragmentos.

CLASIFICACIÓN

SUFFICIENT:
El contexto contiene evidencia que permite responder todos los componentes
sustantivos solicitados en la pregunta.

PARTIAL:
El contexto permite responder al menos una parte sustantiva de la pregunta,
pero falta evidencia para responder uno o más componentes solicitados.

INSUFFICIENT:
El contexto no contiene evidencia suficiente para responder de forma útil
ningún componente sustantivo de la pregunta, o los fragmentos recuperados
solo guardan una relación temática general con ella.

REGLAS IMPORTANTES

- Evalúa suficiencia del CONTEXTO COMPLETO, no relevancia de cada fragmento
  individual.
- NO respondas la pregunta del usuario.
- NO agregues información basada en conocimiento externo.
- NO supongas hechos que no estén explícitamente respaldados por el contexto.
- NO consideres suficiente un contexto únicamente porque pertenece al dominio
  SG-SST.
- Si una pregunta contiene varios componentes, verifica cada uno de ellos.
- Si algunos componentes pueden responderse y otros no, clasifica como PARTIAL.
- Un contexto puede ser suficiente aunque la información esté distribuida en
  varios fragmentos.
- Diferencia información faltante de información simplemente expresada con
  vocabulario distinto.
- En PARTIAL e INSUFFICIENT, identifica de forma concreta qué información falta.
- En SUFFICIENT, missing_information debe quedar vacío.
""".strip()


def sufficient_context_gate_node(
    llm: Any,
) -> Callable[[RagGraphState], RagGraphState]:
    """Build a node that evaluates whether retrieved context is sufficient."""

    def run(state: RagGraphState) -> RagGraphState:
        question = state["question"]
        context = state.get("context", "").strip()

        if not context:
            return {
                "context_sufficiency": ContextSufficiency.INSUFFICIENT.value,
                "sufficient_context_trace": {
                    "level": ContextSufficiency.INSUFFICIENT.value,
                    "reason": "No existe contexto recuperado para evaluar.",
                    "missing_information": [
                        "Evidencia normativa que permita responder la pregunta."
                    ],
                    "fallback": False,
                    "error": None,
                },
            }

        try:
            grader = llm.with_structured_output(SufficientContextGrade)
        except Exception as error:
            logger.error(
                "Could not configure structured sufficient-context grader: %s",
                error,
            )
            return sufficient_context_fallback(error)

        try:
            grade = grade_context_sufficiency(
                grader=grader,
                question=question,
                context=context,
            )

            logger.info(
                "Sufficient-context gate | level=%s | reason=%s | missing=%s",
                grade.level.value,
                grade.reason,
                grade.missing_information,
            )

            return {
                "context_sufficiency": grade.level.value,
                "sufficient_context_trace": {
                    "level": grade.level.value,
                    "reason": grade.reason,
                    "missing_information": grade.missing_information,
                    "fallback": False,
                    "error": None,
                },
            }

        except Exception as error:
            logger.error(
                "Sufficient-context grading failed: %s",
                error,
            )
            return sufficient_context_fallback(error)

    return run


def grade_context_sufficiency(
    grader: Any,
    question: str,
    context: str,
) -> SufficientContextGrade:
    """Assess the complete retrieved context against the original question."""

    response = grader.invoke(
        build_sufficient_context_messages(
            question=question,
            context=context,
        )
    )

    return SufficientContextGrade.model_validate(response)


def build_sufficient_context_messages(
    question: str,
    context: str,
) -> list[Any]:
    """Build messages used by the sufficient-context grader."""

    # pyrefly: ignore [missing-import]
    from langchain_core.messages import HumanMessage, SystemMessage

    human_content = (
        "Pregunta original del usuario:\n"
        f"{question}\n\n"
        "Contexto recuperado:\n"
        f"{context}"
    )

    return [
        SystemMessage(content=SUFFICIENT_CONTEXT_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]


def sufficient_context_fallback(
    error: Exception,
) -> RagGraphState:
    """Allow generation when the gate fails for technical reasons."""

    return {
        # Fail-open: a technical failure does not prove that the context
        # is insufficient.
        "context_sufficiency": ContextSufficiency.SUFFICIENT.value,
        "sufficient_context_trace": {
            "level": None,
            "reason": (
                "La suficiencia del contexto no pudo evaluarse. "
                "Se permite continuar por política fail-open."
            ),
            "missing_information": [],
            "fallback": True,
            "error": type(error).__name__,
        },
    }