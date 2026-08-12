"""Base child-only RAG flow for SG-SST normative consultation."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agents.consulta_normativa.manual_implementation.config import DEFAULT_TOP_K
from agents.consulta_normativa.manual_implementation.prompts import build_base_prompt
from agents.shared.chroma_retrieval import query_top_k


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


# RAG orchestration

def answer_question(
    question: str,
    retriever: Retriever,
    generator: Generator | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> RagAnswer:
    """Retrieve context and answer a normative question with optional generation."""

    results = retriever(question, top_k)                # Llama al retriever
    documents = recovered_documents(results)            # Normaliza los documentos recuperados
    context = build_context(documents)                  # Construye el contexto
    references = build_references(documents)            # Construye las referencias
    prompt = build_base_prompt(question, context)       # Construye el prompt
    answer = generator(prompt) if generator and documents else fallback_answer(context, references)       # Genera la respuesta

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

    context_blocks: list[str] = []
    for index, item in enumerate(documents, start=1):
        metadata_block = metadata_context(item.metadata)
        metadata_text = f"\n{metadata_block}" if metadata_block else ""
        context_blocks.append(
            f"[{index}] {reference_from_metadata(item.metadata)}{metadata_text}\nContenido:\n{item.document}"
        )
    return "\n\n".join(context_blocks)


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

    source = metadata.get("source_stem") or metadata.get("source_document_id") or "fuente desconocida"
    document_type = str(metadata.get("document_type") or "tipo desconocido")
    if document_type == "child_chunk":
        document_type = str(metadata.get("normative_document_type") or document_type)

    if document_type == "table":
        table_parts = [str(source)]
        if metadata.get("table_index") is not None and metadata.get("table_index") != "":
            try:
                table_index = int(metadata["table_index"]) + 1
            except (TypeError, ValueError):
                table_index = metadata["table_index"]
            table_parts.append(f"tabla {table_index}")
        if metadata.get("table_part_index") is not None and metadata.get("table_part_index") != "":
            try:
                part = int(metadata["table_part_index"]) + 1
            except (TypeError, ValueError):
                part = metadata["table_part_index"]
            part_count = metadata.get("table_part_count")
            part_text = f"parte {part} de {part_count}" if part_count is not None and part_count != "" else f"parte {part}"
            table_parts.append(part_text)
        return f"{', '.join(table_parts)} ({document_type})"

    location_parts = [str(source)]
    if metadata.get("article") is not None and metadata.get("article") != "":
        location_parts.append(f"artículo {metadata['article']}")
    if metadata.get("paragraph") is not None and metadata.get("paragraph") != "":
        location_parts.append(f"parágrafo {metadata['paragraph']}")
    if metadata.get("numeral") is not None and metadata.get("numeral") != "":
        location_parts.append(f"numeral {metadata['numeral']}")
    if metadata.get("literal") is not None and metadata.get("literal") != "":
        location_parts.append(f"literal {metadata['literal']}")
    return f"{', '.join(location_parts)} ({document_type})"


def metadata_context(metadata: dict[str, Any]) -> str:
    """Return structured Spanish context from useful flat Chroma metadata."""

    def has_metadata_value(value: Any) -> bool:
        return value is not None and value != ""

    def render_metadata_value(value: Any) -> str:
        if isinstance(value, bool):
            return "sí" if value else "no"
        return str(value)

    def human_table_part() -> str:
        try:
            part = int(metadata["table_part_index"]) + 1
        except (TypeError, ValueError):
            part = metadata["table_part_index"]

        part_count = metadata.get("table_part_count")
        return f"{part} de {part_count}" if has_metadata_value(part_count) else str(part)

    sections = [
        (
            "Información general",
            [
                ("Tipo de registro", "document_type"),
                ("Documento fuente", "source_document_id"),
                ("Fuente", "source_stem"),
                ("Tipo normativo", "normative_document_type"),
                ("Año", "year"),
                ("Título", "title"),
            ],
        ),
        (
            "Jerarquía normativa",
            [
                ("Capítulo", "chapter"),
                ("Artículo", "article"),
                ("Artículos", "articles"),
                ("Parágrafo", "paragraph"),
                ("Numeral", "numeral"),
                ("Literal", "literal"),
            ],
        ),
        (
            "Tablas",
            [
                ("Contiene tablas", "has_tables"),
                ("Claves de tabla", "table_keys"),
            ],
        ),
        (
            "Tabla",
            [
                ("Índice", "table_index"),
                ("Clave lógica", "table_key"),
                ("Marcador vinculado", "linked_placeholder"),
                ("Fila sobredimensionada", "oversized_row"),
            ],
        ),
        (
            "Trazabilidad técnica",
            [
                ("ID padre", "parent_id"),
                ("Inicio", "start_char"),
                ("Fin", "end_char"),
            ],
        ),
    ]

    rendered_sections: list[str] = []
    for title, fields in sections:
        lines = [
            f"- {label}: {render_metadata_value(metadata[key])}"
            for label, key in fields
            if has_metadata_value(metadata.get(key))
        ]
        if title == "Tabla" and has_metadata_value(metadata.get("table_part_index")):
            lines.insert(1 if lines else 0, f"- Parte: {human_table_part()}")
        if lines:
            rendered_sections.append("\n".join([f"{title}:", *lines]))
    return "\n".join(rendered_sections)


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
