"""Small BM25S boundary used by the sparse indexing flow."""

from pathlib import Path
from typing import Any

from pipeline.vectorization.documents import ChromaRecord

Bm25CorpusRecord = dict[str, Any]
BM25_METADATA_FIELDS = (
    ("Fuente", "source_stem"),
    ("Tipo normativo", "normative_document_type"),
    ("Año", "year"),
    ("Título", "title"),
    ("Capítulo", "chapter"),
    ("Artículo", "article"),
    ("Parágrafo", "paragraph"),
    ("Numeral", "numeral"),
    ("Literal", "literal"),
    ("Tipo de fragmento", "document_type"),
    ("Tabla", "table_key"),
    ("Tablas relacionadas", "table_keys"),
)


def build_bm25_index(records: list[ChromaRecord]) -> tuple[Any, list[Bm25CorpusRecord]]:
    """Build a BM25S retriever and return it with the ordered corpus records."""
    
    # Convierte los documentos de Chroma en un formato compatible con BM25S, manteniendo el orden original y los metadatos.
    corpus = bm25_corpus(records)
    
    texts = [bm25_text_for_indexing(record) for record in records]

    #  Crea el modelo de BM25S.
    bm25s = bm25s_module()

    # Tokeniza todo el corpus de textos. BM25S descompone el texto en tokens individuales (palabras o subpalabras). 
    tokens = bm25s.tokenize(texts, stopwords="es")
    
    # Inicializa el modelo BM25.
    retriever = bm25s.BM25()

    # Construye el índice BM25 a partir de los tokens.
    retriever.index(tokens)
    
    return retriever, corpus


def bm25_corpus(records: list[ChromaRecord]) -> list[Bm25CorpusRecord]:
    """Return BM25 corpus records preserving vector record order and metadata."""

    return [
        {
            "id": record.id,
            "document": record.document,
            "metadata": record.metadata,
        }
        for record in records
    ]


def bm25_text_for_indexing(record: ChromaRecord) -> str:
    """Return compact metadata plus document text used only for BM25 indexing."""

    metadata_text = compact_normative_metadata_text(record.metadata, BM25_METADATA_FIELDS)
    if not metadata_text:
        return record.document
    return f"Metadata normativa:\n{metadata_text}\n\nContenido:\n{record.document}"


def compact_normative_metadata_text(
    metadata: dict[str, Any],
    fields: tuple[tuple[str, str], ...],
) -> str:
    """Return only compact legal locator metadata; never trace/debug metadata."""

    lines: list[str] = []
    for label, key in fields:
        value = metadata.get(key)
        formatted = format_metadata_value(value)
        if formatted:
            lines.append(f"{label}: {formatted}")
    return "\n".join(lines)


def format_metadata_value(value: object) -> str:
    """Format scalar or list metadata values for retrieval scoring text."""

    if value in (None, ""):
        return ""
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(items)
    return str(value).strip()


def save_bm25_index(retriever: Any, persist_path: Path, corpus: list[Bm25CorpusRecord]) -> None:
    """Persist a BM25S retriever with the retrievable corpus attached."""

    persist_path.mkdir(parents=True, exist_ok=True)
    retriever.save(str(persist_path), corpus=corpus)


def bm25s_module() -> Any:
    """Import BM25S lazily so tests can patch this boundary without the dependency."""

    # pyrefly: ignore [missing-import]
    import bm25s

    return bm25s
