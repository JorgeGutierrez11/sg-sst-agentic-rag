"""Formatting helpers for experimental RAG context and references."""

from typing import Any

from agents.consulta_normativa.langchain_rag.models import RetrievedDocument

def recovered_documents(results: dict[str, Any]) -> list[RetrievedDocument]:
    """Normalize ChromaDB query output into one list of retrieved documents."""

    documents = first_result_list(results, "documents")
    metadatas = first_result_list(results, "metadatas")

    recovered: list[RetrievedDocument] = []
    for index, document in enumerate(documents):
        recovered.append(
            RetrievedDocument(
                document=str(document),
                metadata=metadata_at(metadatas, index),
            )
        )
    return recovered


def build_context(documents: list[RetrievedDocument]) -> str:
    """Build compact textual context from retrieved documents."""

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


def build_references(documents: list[RetrievedDocument]) -> list[str]:
    """Return unique source references from retrieved metadata."""

    references: list[str] = []
    for item in documents:
        reference = reference_from_metadata(item.metadata)
        if reference not in references:
            references.append(reference)
    return references


def reference_from_metadata(metadata: dict[str, Any]) -> str:
    """Build one compact source reference from flat metadata."""

    source = metadata.get("source_stem") or metadata.get("source_document_id") or "fuente desconocida"
    document_type = str(metadata.get("document_type") or "tipo desconocido")
    if document_type == "child_chunk":
        document_type = str(metadata.get("normative_document_type") or document_type)

    if document_type == "table":
        return table_reference(metadata, str(source), document_type)

    location_parts = [str(source)]
    for label, key in (("artículo", "article"), ("parágrafo", "paragraph"), ("numeral", "numeral"), ("literal", "literal")):
        if has_metadata_value(metadata.get(key)):
            location_parts.append(f"{label} {metadata[key]}")
    return f"{', '.join(location_parts)} ({document_type})"


def metadata_context(metadata: dict[str, Any]) -> str:
    """Return structured Spanish context from useful flat Chroma metadata."""

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
        ("Tablas", [("Contiene tablas", "has_tables"), ("Claves de tabla", "table_keys")]),
        (
            "Tabla",
            [
                ("Índice", "table_index"),
                ("Clave lógica", "table_key"),
                ("Marcador vinculado", "linked_placeholder"),
                ("Fila sobredimensionada", "oversized_row"),
            ],
        ),
        ("Trazabilidad técnica", [("ID padre", "parent_id"), ("Inicio", "start_char"), ("Fin", "end_char")]),
    ]

    rendered_sections: list[str] = []
    for title, fields in sections:
        lines = [
            f"- {label}: {render_metadata_value(metadata[key])}"
            for label, key in fields
            if has_metadata_value(metadata.get(key))
        ]
        if title == "Tabla" and has_metadata_value(metadata.get("table_part_index")):
            lines.insert(1 if lines else 0, f"- Parte: {human_table_part(metadata)}")
        if lines:
            rendered_sections.append("\n".join([f"{title}:", *lines]))
    return "\n".join(rendered_sections)

def metadata_at(metadatas: list[Any], index: int) -> dict[str, Any]:
    """Return metadata at a result index when it is a dictionary."""

    return metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else {}


def first_result_list(results: dict[str, Any], key: str) -> list[Any]:
    """Return the first ChromaDB result list for a query output key."""

    value = results.get(key, [])
    if isinstance(value, list) and value and isinstance(value[0], list):
        return value[0]
    return value if isinstance(value, list) else []


def table_reference(metadata: dict[str, Any], source: str, document_type: str) -> str:
    """Build a compact table reference from table metadata."""

    table_parts = [source]
    if has_metadata_value(metadata.get("table_index")):
        table_parts.append(f"tabla {one_based_value(metadata['table_index'])}")
    if has_metadata_value(metadata.get("table_part_index")):
        part = one_based_value(metadata["table_part_index"])
        part_count = metadata.get("table_part_count")
        part_text = f"parte {part} de {part_count}" if has_metadata_value(part_count) else f"parte {part}"
        table_parts.append(part_text)
    return f"{', '.join(table_parts)} ({document_type})"


def human_table_part(metadata: dict[str, Any]) -> str:
    """Return a human-readable one-based table part label."""

    part = one_based_value(metadata["table_part_index"])
    part_count = metadata.get("table_part_count")
    return f"{part} de {part_count}" if has_metadata_value(part_count) else str(part)


def one_based_value(value: Any) -> Any:
    """Return an integer-like value converted from zero-based to one-based."""

    try:
        return int(value) + 1
    except (TypeError, ValueError):
        return value


def has_metadata_value(value: Any) -> bool:
    """Return whether a metadata value should be rendered."""

    return value is not None and value != ""


def render_metadata_value(value: Any) -> str:
    """Render primitive metadata values for the context block."""

    if isinstance(value, bool):
        return "sí" if value else "no"
    return str(value)
