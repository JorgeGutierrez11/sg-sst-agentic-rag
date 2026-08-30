"""LLM-based retrieval relevance grading for normative RAG documents."""

import logging
from collections.abc import Callable
from typing import Any

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.models import RetrievedDocument

logger = logging.getLogger(__name__)


class RelevanceGrade(BaseModel):
    """Structured relevance decision for one retrieved document."""

    relevant: bool = Field(
        description=(
            "True when the retrieved document contains information that "
            "contributes directly to answering at least part of the user's question."
        )
    )

    reason: str = Field(
        description=(
            "Brief explanation of why the document is relevant or irrelevant, "
            "based only on the user's question and the retrieved document."
        )
    )


RETRIEVAL_RELEVANCE_SYSTEM_PROMPT = """
Eres un evaluador de relevancia documental para un sistema RAG de consulta normativa
sobre el Sistema de Gestión de Seguridad y Salud en el Trabajo (SG-SST) en Colombia.

Tu única tarea es determinar si UN documento recuperado aporta información útil para
responder la pregunta original del usuario.

DEFINICIÓN DE RELEVANCIA

Un documento es RELEVANTE cuando contiene información normativa que contribuye
directamente a responder al menos una parte de la pregunta.

Un documento puede ser relevante aunque:
- no responda completamente la pregunta;
- solo responda uno de varios aspectos solicitados;
- necesite complementarse con otros documentos;
- sea un fragmento parcial de una disposición normativa.

Un documento es NO RELEVANTE cuando:
- solamente comparte términos generales del dominio SG-SST;
- menciona conceptos de la pregunta pero no aporta información útil sobre ellos;
- trata sobre una obligación, sujeto, procedimiento o situación diferente;
- pertenece al mismo documento normativo pero el fragmento recuperado no contribuye
  realmente a responder la pregunta;
- su relación con la pregunta depende de una inferencia que no está respaldada por
  su contenido.

REGLAS IMPORTANTES

- Evalúa relevancia, NO suficiencia.
- NO determines si el documento permite responder completamente la pregunta.
- NO evalúes la calidad de una respuesta generada.
- NO inventes información que no aparezca en el documento.
- NO uses conocimiento externo para completar o reinterpretar el contenido.
- La pertenencia al dominio SG-SST por sí sola NO hace relevante un documento.
- La coincidencia de palabras por sí sola NO hace relevante un documento.
- Si el documento aporta evidencia clara para una parte de una pregunta compuesta,
  considéralo relevante.
- Cuando exista una relación plausible y directa pero el fragmento sea parcial,
  prioriza conservar la evidencia y considéralo relevante.

FORMATO DE SALIDA

Devuelve exclusivamente un objeto JSON válido con esta estructura:

{
    "relevant": true,
    "reason": "Explicación breve de la decisión."
}

El campo "relevant" debe ser booleano:
- true si el documento es relevante;
- false si el documento no es relevante.

No agregues texto, Markdown ni explicaciones fuera del JSON.
""".strip()


def retrieval_relevance_grading_node(
    llm: Any,
) -> Callable[[RagGraphState], RagGraphState]:
    """Build a node that filters retrieved documents by LLM-assessed relevance."""

    def run(state: RagGraphState) -> RagGraphState:
        question = state["question"]
        documents = state.get("documents", [])

        # temporal logging
        log_documents_before_relevance_grading(documents, max_chars=1200)

        if not documents:
            return {
                "documents": [],
                "relevance_grading_trace": {
                    "input_count": 0,
                    "relevant_count": 0,
                    "rejected_count": 0,
                    "fallback_count": 0,
                    "documents": [],
                },
            }

        try:
            grader = llm.with_structured_output(
                RelevanceGrade,
                method="json_mode",
            )
        except Exception as error:
            logger.error(
                "Could not configure structured relevance grader: %s",
                error,
            )
            return relevance_grading_fallback(documents, error)

        relevant_documents: list[RetrievedDocument] = []
        document_traces: list[dict[str, Any]] = []
        fallback_count = 0
        grader_relevant_count = 0

        for index, document in enumerate(documents):
            try:
                grade = grade_document_relevance(
                    grader=grader,
                    question=question,
                    document=document,
                )

                logger.info(
                    "Relevance grading | doc=%s | source=%s | article=%s | relevant=%s | reason=%s",
                    index + 1,
                    document.metadata.get("source_stem"),
                    document.metadata.get("article"),
                    grade.relevant,
                    grade.reason,
                )

                if grade.relevant:
                    relevant_documents.append(document)
                    grader_relevant_count += 1

                document_traces.append(
                    build_document_trace(
                        index=index,
                        document=document,
                        relevant=grade.relevant,
                        reason=grade.reason,
                        fallback=False,
                        error=None,
                    )
                )

            except Exception as error:
                # Fail-open: a grader failure must not silently discard
                # potentially valid normative evidence.
                logger.error(
                    "Relevance grading failed for document %s: %s",
                    index,
                    error,
                )

                relevant_documents.append(document)
                fallback_count += 1

                document_traces.append(
                    build_document_trace(
                        index=index,
                        document=document,
                        relevant=True,
                        reason="Documento conservado por política fail-open debido a un error del grader.",
                        fallback=True,
                        error=type(error).__name__,
                    )
                )


        return {
            "documents": relevant_documents,
            "relevance_grading_trace": {
                "input_count": len(documents),
                "relevant_count": grader_relevant_count,
                "rejected_count": len(documents) - grader_relevant_count,
                "fallback_count": fallback_count,
                "documents": document_traces,
            },
        }

    return run


def grade_document_relevance(
    grader: Any,
    question: str,
    document: RetrievedDocument,
) -> RelevanceGrade:
    """Grade one retrieved document against the original user question."""

    response = grader.invoke(
        build_relevance_grading_messages(
            question=question,
            document=document,
        )
    )

    return RelevanceGrade.model_validate(response)


def build_relevance_grading_messages(
    question: str,
    document: RetrievedDocument,
) -> list[Any]:
    """Build messages used to grade one retrieved document."""

    # pyrefly: ignore [missing-import]
    from langchain_core.messages import HumanMessage, SystemMessage

    metadata = format_relevance_metadata(document.metadata)

    metadata_section = (
        f"\nInformación normativa del documento:\n{metadata}\n"
        if metadata
        else ""
    )

    human_content = (
        f"Pregunta original del usuario:\n"
        f"{question}\n"
        f"{metadata_section}\n"
        f"Documento recuperado:\n"
        f"{document.document}"
    )

    return [
        SystemMessage(content=RETRIEVAL_RELEVANCE_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]


def format_relevance_metadata(metadata: dict[str, Any]) -> str:
    """Return only metadata useful for judging normative relevance."""

    fields = (
        ("Fuente", "source_stem"),
        ("Tipo normativo", "normative_document_type"),
        ("Año", "year"),
        ("Título", "title"),
        ("Capítulo", "chapter"),
        ("Artículo", "article"),
        ("Parágrafo", "paragraph"), 
        ("Numeral", "numeral"),
        ("Literal", "literal"),
    )

    lines = [
        f"- {label}: {metadata[key]}"
        for label, key in fields
        if metadata.get(key) not in (None, "")
    ]

    return "\n".join(lines)


def build_document_trace(
    index: int,
    document: RetrievedDocument,
    relevant: bool,
    reason: str | None,
    fallback: bool,
    error: str | None,
) -> dict[str, Any]:
    """Build compact trace information for one relevance decision."""

    return {
        "index": index,
        "chroma_id": document.metadata.get("_chroma_id"),
        "source": document.metadata.get("source_stem"),
        "article": document.metadata.get("article"),
        "relevant": relevant,
        "reason": reason,
        "fallback": fallback,
        "error": error,
    }


def relevance_grading_fallback(
    documents: list[RetrievedDocument],
    error: Exception,
) -> RagGraphState:
    """Preserve all documents when the relevance grader cannot be initialized."""

    document_traces = [
        build_document_trace(
            index=index,
            document=document,
            relevant=True,
            reason="Documento conservado por política fail-open porque el grader no pudo configurarse.",
            fallback=True,
            error=type(error).__name__,
        )
        for index, document in enumerate(documents)
    ]

    return {
        "documents": documents,
        "relevance_grading_trace": {
            "input_count": len(documents),
            "relevant_count": len(documents),
            "rejected_count": 0,
            "fallback_count": len(documents),
            "fallback": True,
            "error": type(error).__name__,
            "documents": document_traces,
        },
    }


# Is a temporal Logger
def log_documents_before_relevance_grading(
    documents: list[RetrievedDocument],
    max_chars: int = 1200,
) -> None:
    """Log documents before relevance grading with bounded text previews."""

    logger.info("Documents before relevance grading: %s", len(documents))

    for index, document in enumerate(documents, start=1):
        metadata = document.metadata
        preview = document.document[:max_chars].replace("\n", " ")

        logger.info(
            "Before relevance grading | doc=%s | type=%s | source=%s | article=%s | "
            "parent_expanded=%s | retrieval_sources=%s | child_ids=%s | chars=%s | preview=%s",
            index,
            metadata.get("document_type"),
            metadata.get("source_stem"),
            metadata.get("article"),
            metadata.get("parent_expansion_applied"),
            metadata.get("_retrieval_sources") or metadata.get("expanded_from_child_retrieval_sources"),
            metadata.get("expanded_from_child_ids"),
            len(document.document),
            preview,
        )