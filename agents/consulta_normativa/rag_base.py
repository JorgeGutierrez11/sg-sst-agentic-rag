"""Base child-only RAG flow for SG-SST normative consultation."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agents.consulta_normativa.prompts import build_base_prompt
from pipeline.vectorization.chroma_store import query_top_k


Retriever = Callable[[str, int], dict[str, Any]]
Generator = Callable[[str], str]


# Public result models

@dataclass(frozen=True)
class RagAnswer:
    """Answer produced by the base RAG flow."""

    answer: str
    references: list[str]
    context: str
    prompt: str


@dataclass(frozen=True)
class RecoveredDocument:
    """One document recovered from the vector store."""

    document: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SourceReference:
    """Source fields needed to format a recovered document reference."""

    source: str
    document_type: str
    article: Any = None

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> "SourceReference":
        """Build a source reference from flat Chroma metadata."""

        source = metadata.get("source_stem") or metadata.get("source_document_id") or "fuente desconocida"
        return cls(
            source=str(source),
            document_type=str(metadata.get("document_type", "tipo desconocido")),
            article=metadata.get("article"),
        )

    def format(self) -> str:
        """Return the compact source reference used in prompts and fallback answers."""

        article_text = f", artículo {self.article}" if self.article else ""
        return f"{self.source}{article_text} ({self.document_type})"


# RAG orchestration

def answer_question(question: str, retriever: Retriever, generator: Generator | None = None, top_k: int = 5) -> RagAnswer:
    """Retrieve context and answer a normative question with optional generation."""

    results = retriever(question, top_k)
    documents = recovered_documents(results)
    context = build_context(documents)
    references = build_references(documents)
    prompt = build_base_prompt(question, context)
    answer = generator(prompt) if generator and documents else fallback_answer(context, references)

    return RagAnswer(answer=answer, references=references, context=context, prompt=prompt)


# Retrieval boundary

def chroma_retriever(collection: Any) -> Retriever:
    """Build a retriever callable from a ChromaDB collection-like object."""

    def retrieve(question: str, top_k: int) -> dict[str, Any]:
        return query_top_k(collection, question, top_k)

    return retrieve


# Retrieved document normalization

def recovered_documents(results: dict[str, Any]) -> list[RecoveredDocument]:
    """Normalize ChromaDB query output into one list of recovered documents."""

    documents = first_result_list(results, "documents")
    metadatas = first_result_list(results, "metadatas")

    recovered: list[RecoveredDocument] = []
    for index, document in enumerate(documents):
        recovered.append(
            RecoveredDocument(
                document=str(document),
                metadata=metadata_at(metadatas, index),
            )
        )
    return recovered


def build_context(documents: list[RecoveredDocument]) -> str:
    """Build compact textual context from recovered documents."""

    if not documents:
        return "No se recuperó contexto."
    return "\n\n".join(
        f"[{index}] {reference_from_metadata(item.metadata)}\n{item.document}"
        for index, item in enumerate(documents, start=1)
    )


def build_references(documents: list[RecoveredDocument]) -> list[str]:
    """Return basic source references from recovered metadata."""

    references: list[str] = []
    for item in documents:
        reference = reference_from_metadata(item.metadata)
        if reference not in references:
            references.append(reference)
    return references


def metadata_at(metadatas: list[Any], index: int) -> dict[str, Any]:
    """Return metadata at a Chroma result index when it is a dictionary."""

    return metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else {}


# Answer formatting


def reference_from_metadata(metadata: dict[str, Any]) -> str:
    """Build one compact source reference from flat metadata."""

    return SourceReference.from_metadata(metadata).format()


def fallback_answer(context: str, references: list[str]) -> str:
    """Return deterministic grounded output when no LLM generator is configured."""

    if context == "No se recuperó contexto.":
        return "La evidencia recuperada es insuficiente para responder la pregunta."
    return "\n".join(["Borrador fundamentado solo en el contexto recuperado:", context, "Referencias:", *references])


def first_result_list(results: dict[str, Any], key: str) -> list[Any]:
    """Return the first ChromaDB result list for a query output key."""

    value = results.get(key, [])
    if isinstance(value, list) and value and isinstance(value[0], list):
        return value[0]
    return value if isinstance(value, list) else []
