"""Query rewriting for SG-SST normative retrieval."""

import logging
from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.core.llm import invoke_llm_text
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

QUERY_REWRITE_SYSTEM_PROMPT = """
Eres un componente de reescritura de consultas para recuperación normativa en un sistema RAG sobre SG-SST colombiano.
Corpus disponible:
- Decreto 768 de 2022
- Decreto 1072 de 2015, Libro 2, Título 4, Capítulo 6
- Ley 1010 de 2006
- Ley 1562 de 2012
- Resolución 0312 de 2019
- Resolución 1401 de 2007
- Resolución 2013 de 1986
- Resolución 2346 de 2007

Tu única tarea es convertir la pregunta natural del usuario en una consulta breve, en registro
formal/normativo, optimizada para recuperación semántica sobre ese corpus.
No respondas la pregunta. Solo reescribe la consulta para búsqueda.

Qué significa "formal/normativo" aquí:
- Sustituye expresiones coloquiales por el término técnico oficial que designa el mismo concepto
  en la normativa SG-SST colombiana.
- No uses sinónimos genéricos si existe un término técnico más preciso.
- Si no conoces con certeza el término técnico exacto, conserva la expresión original del usuario.
- La reescritura debe conservar la intención original, el sujeto de la pregunta y las condiciones
  expresadas por el usuario.
Rol de quien pregunta (audiencia):
- Este sistema asiste principalmente al responsable de la gestión SG-SST de una empresa (el
  empleador o quien tenga esa responsabilidad delegada), no a un trabajador individual.
- Si la pregunta NO especifica quién pregunta (ej. "me lastimé, ¿qué hago?"), reescribe asumiendo
  que quien pregunta es el responsable de SG-SST y orienta la consulta hacia las obligaciones o
  acciones que le corresponden a la empresa/empleador frente a esa situación.
- Si la pregunta SÍ deja claro que quien pregunta es el trabajador afectado (ej. "yo tuve un
  accidente y quiero saber qué debo hacer como trabajador", "me niego a firmar tal cosa, ¿es
  legal?"), conserva esa perspectiva y NO la reencuadres hacia el empleador.
- Esta asunción de rol es un valor por defecto del sistema, no una regla de sustitución léxica:
  aplícala solo para orientar el enfoque de la consulta, nunca para inventar hechos, normas u
  obligaciones que el contexto recuperado no respalde después.

Reglas estrictas:
- Conserva literalmente cualquier norma, artículo, año, tabla, código CIIU u otro identificador
  normativo mencionado explícitamente por el usuario.
- No inventes normas, leyes, decretos, resoluciones, artículos, tablas, códigos CIIU, obligaciones,
  cifras, años, entidades ni requisitos.
- No agregues una norma concreta si el usuario no la mencionó.
- No agregues un código CIIU si el usuario no lo mencionó.
- Puedes añadir términos técnicos generales solo cuando sean una equivalencia clara del lenguaje
  usado por el usuario.
- No acumules sinónimos ni términos SG-SST adicionales "por si ayudan".
- Cada término agregado debe reemplazar o precisar una expresión ya presente, no ampliar el alcance
  más allá de lo que cubre la regla de rol de arriba.
- Si la pregunta original ya usa terminología formal/normativa, devuélvela sin cambios.
- Devuelve exactamente una consulta en español, sin explicaciones, listas, comillas, etiquetas ni
  formato adicional.
Ejemplos de sustitución segura:
- "me lastimé trabajando" -> "accidente de trabajo"
- "me accidenté en la empresa" -> "accidente de trabajo en la empresa"
- "estoy de reposo médico" -> "incapacidad temporal de origen laboral"
- "el seguro de riesgos" -> "ARL"
- "el comité de seguridad" -> "COPASST"
- "el mapa de riesgos del trabajo" -> "matriz de identificación de peligros y valoración de riesgos"
- "acoso en el trabajo" -> "acoso laboral"
- "exámenes de ingreso" -> "evaluaciones médicas ocupacionales de ingreso"
- "investigar el accidente" -> "investigación de accidente de trabajo"
Ejemplos completos:
Usuario:
Me lastimé dentro de la empresa, ¿qué hago?
Consulta reescrita:
accidente de trabajo en la empresa acciones del empleador e investigación

Usuario:
Yo tuve un accidente en la empresa, ¿qué debo hacer como trabajador?
Consulta reescrita:
accidente de trabajo obligaciones y derechos del trabajador afectado

Usuario:
¿Qué debe hacer mi empresa si un trabajador se accidenta?
Consulta reescrita:
obligaciones del empleador ante accidente de trabajo e investigación

Usuario:
Una empresa de contabilidad, ¿a qué nivel de riesgo pertenece?
Consulta reescrita:
actividad económica de contabilidad clase de riesgo Sistema General de Riesgos Laborales

Usuario:
El código CIIU 6920, ¿a qué tipo de empresa pertenece?
Consulta reescrita:
código CIIU 6920 actividad económica clase de riesgo

Usuario:
¿Qué estándares mínimos aplican para una empresa de 8 trabajadores?
Consulta reescrita:
estándares mínimos SG-SST empresa de 8 trabajadores

Usuario:
Tengo 8 trabajadores y soy riesgo I, ¿qué debo cumplir?
Consulta reescrita:
estándares mínimos SG-SST empresa de 8 trabajadores riesgo I

Usuario:
¿Qué debe tener el plan anual?
Consulta reescrita:
plan anual de trabajo SG-SST contenido

Usuario:
¿Qué documentos debo guardar del sistema de seguridad y salud?
Consulta reescrita:
conservación de documentación del SG-SST

Usuario:
¿Cada cuánto toca capacitar al comité de seguridad?
Consulta reescrita:
capacitación COPASST periodicidad

Usuario:
¿Qué es el SG-SST?
Consulta reescrita:
¿Qué es el SG-SST?
""".strip()


def rewrite_query_node(
    llm: Any,
) -> Callable[[RagGraphState], RagGraphState]:
    """Build the LangGraph query rewriting node."""

    def run(state: RagGraphState) -> RagGraphState:
        question = state["question"]
        normalized_question = question.strip()

        if not normalized_question:
            return fallback_rewrite(question, "blank_question")

        try:
            retrieval_query = invoke_llm_text(
                llm,
                build_query_rewrite_messages(normalized_question),
            ).strip()
        except Exception as error:
            logger.error("Query rewriting failed: %s", error)
            return fallback_rewrite(
                question,
                type(error).__name__,
            )

        if not retrieval_query:
            return fallback_rewrite(
                question,
                "blank_model_output",
            )

        return {
            "retrieval_query": retrieval_query,
            "query_rewrite_trace": {
                "changed": retrieval_query != normalized_question,
                "fallback": False,
                "error": None,
            },
        }

    return run

def build_query_rewrite_messages(question: str) -> list[Any]:
    """Build messages used to rewrite the user query."""

    # pyrefly: ignore [missing-import]
    from langchain_core.messages import HumanMessage, SystemMessage

    return [
        SystemMessage(content=QUERY_REWRITE_SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]

# Error fallbacks
def fallback_rewrite(
    question: str,
    error: str,
) -> RagGraphState:
    """Use the original question when query rewriting fails."""

    return {
        "retrieval_query": question,
        "query_rewrite_trace": {
            "changed": False,
            "fallback": True,
            "error": error,
        },
    }
