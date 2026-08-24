"""LLM-based query expansion for SG-SST normative retrieval."""

import logging
import re
from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState

try:
    # pyrefly: ignore [missing-import]
    from pydantic import BaseModel, Field
except ModuleNotFoundError:
    BaseModel = object

    def Field(default_factory: object = None, **_: object) -> object:
        return default_factory() if callable(default_factory) else default_factory


logger = logging.getLogger(__name__)

MAX_EXPANSION_TERMS = 6
NORMATIVE_IDENTIFIER_PATTERNS = (
    r"\b(?:decreto|ley|resoluci[oó]n)\s+\d+(?:\s+de\s+\d{4})?\b",
    r"\b(?:decreto|ley|resoluci[oó]n)\s+\d+\b",
    r"\b(?:19|20)\d{2}\b",
    r"\bcii?u\s*\d+\b",
    r"\bart[íi]culo\s+\d+(?:\.\d+)*\b",
    r"\bnumeral\s+\d+(?:\.\d+)*\b",
    r"\bliteral\s+[a-z]\b",
    r"\bpar[áa]grafo\s+\d+\b",
    r"\btabla\s+\d+(?:\.\d+)*\b",
    r"\briesgo\s+(?:i|ii|iii|iv|v|1|2|3|4|5)\b",
)


QUERY_EXPANSION_SYSTEM_PROMPT = f"""
Eres un componente de expansión de consultas para recuperación normativa
en un sistema RAG sobre SG-SST colombiano.

Corpus disponible:

- Decreto 768 de 2022
- Decreto 1072 de 2015, Libro 2, Título 4, Capítulo 6
- Ley 1010 de 2006
- Ley 1562 de 2012
- Resolución 0312 de 2019
- Resolución 1401 de 2007
- Resolución 2013 de 1986
- Resolución 2346 de 2007

Tu única tarea es generar términos o expresiones adicionales que puedan mejorar
la recuperación de documentos para la consulta original.

IMPORTANTE:

- NO reescribas la consulta original.
- NO reformules la consulta original.
- NO sustituyas palabras de la consulta original.
- NO elimines información de la consulta original.
- NO respondas la pregunta.
- Devuelve únicamente términos o expresiones de expansión.

Los términos generados serán añadidos posteriormente por el sistema a la consulta
original. Tú no debes construir la consulta final.

OBJETIVO DE LA EXPANSIÓN

Genera términos técnicos, denominaciones formales o expresiones normativas
estrechamente relacionadas con la misma necesidad de información.

Los términos deben ayudar a reducir diferencias entre el vocabulario utilizado
por el usuario y el vocabulario que puede aparecer en el corpus normativo.

Puedes generar:

- denominaciones técnicas equivalentes;
- siglas y sus denominaciones completas;
- categorías normativas relacionadas directamente con la consulta;
- terminología formal utilizada en SG-SST;
- denominaciones de actividades o conceptos que puedan aparecer en normas,
  tablas o disposiciones del corpus.

NO debes generar:

- nuevas preguntas;
- paráfrasis completas de la consulta;
- explicaciones;
- respuestas;
- procedimientos no solicitados;
- obligaciones específicas;
- conclusiones jurídicas.

RESTRICCIONES NORMATIVAS

- No inventes leyes, decretos o resoluciones.
- No inventes artículos, numerales, literales o tablas.
- No inventes códigos CIIU.
- No inventes años.
- No inventes clases o niveles de riesgo.
- No inventes obligaciones, sanciones, cifras, entidades ni requisitos.
- No agregues una norma concreta si el usuario no la mencionó.
- No agregues un código CIIU si el usuario no lo mencionó.
- Si no existe un término adicional suficientemente relacionado, devuelve una lista vacía.

DIVERSIDAD

Los términos deben aportar vocabulario adicional útil.

ESPECIFICIDAD MÍNIMA

Cada término debe discriminar mejor los documentos relevantes para la consulta concreta.
No basta con que el término pertenezca al dominio SG-SST: debe aportar vocabulario específico
para recuperar evidencia más precisa.

No generes términos amplios como:

- SG-SST;
- Sistema de Gestión de Seguridad y Salud en el Trabajo;
- normativa;
- requisito;
- empresa;
- empleador;
- trabajador;
- seguridad y salud en el trabajo.

Solo puedes usar esos términos si la pregunta trata directamente sobre la definición,
estructura general o alcance de ese concepto.

Evita:

- términos duplicados;
- variantes que solo cambien plural por singular;
- palabras o expresiones genéricas del dominio si no aportan capacidad real de recuperación;
- repetir literalmente expresiones que ya aparecen en la consulta.

Genera como máximo {MAX_EXPANSION_TERMS} términos o expresiones.

EJEMPLOS

Usuario:
¿Cada cuánto toca capacitar al comité de seguridad?

Expansión:
COPASST
Comité Paritario de Seguridad y Salud en el Trabajo
periodicidad de capacitación

Usuario:
¿Qué documentos debo guardar del sistema de seguridad y salud?

Expansión:
SG-SST
conservación documental
custodia de documentación

Usuario:
Una empresa de contabilidad, ¿a qué nivel de riesgo pertenece?

Expansión:
actividad económica
servicios contables
clasificación de actividades económicas
clase de riesgo
Sistema General de Riesgos Laborales

Usuario:
¿Qué nivel de riesgo es una textilería?

Expansión inválida:
SG-SST
Sistema de Gestión de Seguridad y Salud en el Trabajo

Expansión válida:
actividad económica
clase de riesgo
clasificación de actividades económicas
Sistema General de Riesgos Laborales

Usuario:
¿Qué debe tener el plan anual?

Expansión:
plan anual de trabajo
SG-SST
contenido del plan anual

Usuario:
¿Qué es el SG-SST?

Expansión:
Sistema de Gestión de Seguridad y Salud en el Trabajo
""".strip()


class QueryExpansionOutput(BaseModel):
    """Represent the expansion terms generated for the original retrieval query."""

    expansion_terms: list[str] = Field(
        default_factory=list,
        max_length=MAX_EXPANSION_TERMS,
        description=(
            "Technical or normative terms that expand the original query "
            "without rewriting or replacing it."
        ),
    )

    if BaseModel is object:

        def __init__(self, expansion_terms: list[str] | None = None) -> None:
            self.expansion_terms = expansion_terms or []


def query_expansion_node(
    llm: Any,
) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that expands the original query with LLM-generated terms."""

    def run(state: RagGraphState) -> RagGraphState:
        question = state["question"]
        normalized_question = question.strip()

        if not normalized_question:
            return fallback_expansion(question, "blank_question")

        try:
            expander = llm.with_structured_output(
                QueryExpansionOutput,
                method="function_calling",
            )
            result = expander.invoke(
                build_query_expansion_messages(normalized_question)
            )
        except Exception as error:
            logger.error("Query expansion failed: %s", error)
            return fallback_expansion(
                question,
                type(error).__name__,
            )

        expansion_terms = clean_expansion_terms(
            normalized_question,
            getattr(result, "expansion_terms", []),
        )

        retrieval_query = build_expanded_query(
            normalized_question,
            expansion_terms,
        )

        return {
            "retrieval_query": retrieval_query,
            "query_expansion_trace": {
                "technique": "llm_query_expansion",
                "expansion_terms": expansion_terms,
                "changed": bool(expansion_terms),
                "fallback": False,
                "error": None,
            },
        }

    return run


def build_query_expansion_messages(
    question: str,
) -> list[Any]:
    """Build the messages that instruct the LLM to generate expansion terms."""

    # pyrefly: ignore [missing-import]
    from langchain_core.messages import HumanMessage, SystemMessage

    return [
        SystemMessage(content=QUERY_EXPANSION_SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]


def clean_expansion_terms(
    question: str,
    terms: list[Any],
) -> list[str]:
    """Remove empty, duplicated, already-present, and unsafe expansion terms."""

    normalized_question = question.casefold()
    cleaned_terms: list[str] = []
    seen: set[str] = set()

    for term in terms:
        if not isinstance(term, str):
            continue

        cleaned = " ".join(term.split())
        normalized = cleaned.casefold()

        if not cleaned:
            continue

        if normalized in seen:
            continue

        if normalized in normalized_question:
            continue

        if not is_safe_expansion_term(question, cleaned):
            continue

        seen.add(normalized)
        cleaned_terms.append(cleaned)

    return cleaned_terms[:MAX_EXPANSION_TERMS]


def build_expanded_query(
    question: str,
    expansion_terms: list[str],
) -> str:
    """Append expansion terms to the unchanged original query."""

    if not expansion_terms:
        return question

    return " ".join(
        [
            question,
            *expansion_terms,
        ]
    )


def is_safe_expansion_term(
    question: str,
    term: str,
) -> bool:
    """Reject expansion terms that introduce legal or normative identifiers."""

    original_identifiers = extract_normative_identifiers(question)
    term_identifiers = extract_normative_identifiers(term)

    return term_identifiers.issubset(original_identifiers)


def extract_normative_identifiers(text: str) -> set[str]:
    """Extract concrete legal, numeric, and SG-SST classification identifiers."""

    normalized_text = text.casefold()
    identifiers: set[str] = set()

    for pattern in NORMATIVE_IDENTIFIER_PATTERNS:
        identifiers.update(
            " ".join(match.group(0).split())
            for match in re.finditer(pattern, normalized_text)
        )

    return identifiers


def fallback_expansion(
    question: str,
    error: str,
) -> RagGraphState:
    """Return the original query when query expansion cannot be completed."""

    return {
        "retrieval_query": question,
        "query_expansion_trace": {
            "technique": "llm_query_expansion",
            "expansion_terms": [],
            "changed": False,
            "fallback": True,
            "error": error,
        },
    }
