"""Small BM25S boundary used by the sparse indexing flow."""

from pathlib import Path
from typing import Any

from pipeline.vectorization.documents import ChromaRecord

Bm25CorpusRecord = dict[str, Any]


def build_bm25_index(records: list[ChromaRecord]) -> tuple[Any, list[Bm25CorpusRecord]]:
    """Build a BM25S retriever and return it with the ordered corpus records."""
    
    # Convierte los documentos de Chroma en un formato compatible con BM25S, manteniendo el orden original y los metadatos.
    corpus = bm25_corpus(records)
    
    texts = [record["document"] for record in corpus]

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


def save_bm25_index(retriever: Any, persist_path: Path, corpus: list[Bm25CorpusRecord]) -> None:
    """Persist a BM25S retriever with the retrievable corpus attached."""

    persist_path.mkdir(parents=True, exist_ok=True)
    retriever.save(str(persist_path), corpus=corpus)


def bm25s_module() -> Any:
    """Import BM25S lazily so tests can patch this boundary without the dependency."""

    # pyrefly: ignore [missing-import]
    import bm25s

    return bm25s
