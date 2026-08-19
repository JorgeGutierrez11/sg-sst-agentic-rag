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
Eres un componente de reescritura de consultas para recuperación normativa en un sistema RAG sobre SG-SST
colombiano.

Tu única tarea es convertir la pregunta natural del usuario en una consulta breve y más útil para recuperación
semántica normativa.

Reglas:
- Conserva la intención original del usuario.
- No respondas la pregunta.
- No inventes normas, leyes, decretos, resoluciones, artículos, obligaciones, cifras ni entidades.
- Conserva cualquier norma, artículo, año u otro identificador normativo mencionado explícitamente.
- Puedes añadir términos generales de SG-SST solo si ayudan a expresar la misma necesidad de búsqueda.
- Devuelve exactamente una consulta en español.
- No incluyas explicaciones, listas, comillas, etiquetas ni formato adicional.
- Si la pregunta original ya es adecuada para recuperación, devuélvela sin cambios.
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
