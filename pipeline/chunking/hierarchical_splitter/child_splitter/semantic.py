"""Build semantic child chunks from parent chunks."""

from pathlib import Path
from typing import Any

from pipeline.chunking.core.config import DEFAULT_EMBEDDING_MODEL
from pipeline.chunking.core.io_jsonl import read_parent_chunks, write_child_chunks
from pipeline.chunking.hierarchical_splitter.child_splitter.shared import (
    SEMANTIC_BACKEND,
    SEMANTIC_SPLIT_REASON,
    ChildBuildResult,
    build_child_chunk,
    next_child_start,
)
from pipeline.chunking.hierarchical_splitter.models import ChildChunk, ParentChunk

# pyrefly: ignore [missing-import]
from langchain_experimental.text_splitter import SemanticChunker
# pyrefly: ignore [missing-import]
from langchain_huggingface import HuggingFaceEmbeddings


# Pipeline orchestration


def write_semantic_child_output(
    input_path: Path,                       # Ruta de los archivos de texto original
    output_path: Path,                      # Ruta donde se guardan los child chunks
    breakpoint_threshold_type: str,         # Tipo de umbral de breakpoint
    breakpoint_threshold_amount: float,     # Cantidad de umbral de breakpoint
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> ChildBuildResult:
    """Read parent chunks, write semantic child chunks, and return a summary."""

    validate_semantic_options(breakpoint_threshold_type, breakpoint_threshold_amount, embedding_model)
    if not input_path.exists():
        raise FileNotFoundError(f"Parent chunks input does not exist: {input_path}")

    parents = read_parent_chunks(input_path)
    children = build_semantic_child_chunks(
        parents,
        breakpoint_threshold_type,
        breakpoint_threshold_amount,
        embedding_model,
    )
    write_child_chunks(children, output_path)
    return ChildBuildResult(
        parent_count=len(parents),
        chunk_count=len(children),
        output_path=output_path,
    )


def build_semantic_child_chunks(
    parents: list[ParentChunk],
    breakpoint_threshold_type: str,
    breakpoint_threshold_amount: float,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
) -> list[ChildChunk]:
    """Split parent chunks using LangChain's embedding-based SemanticChunker."""

    validate_semantic_options(breakpoint_threshold_type, breakpoint_threshold_amount, embedding_model)
    if not parents:
        return []
    splitter = create_semantic_splitter(embedding_model, breakpoint_threshold_type, breakpoint_threshold_amount)
    children: list[ChildChunk] = []
    for parent in parents:
        if not parent.text.strip():
            continue
        search_from = 0
        for chunk_index, document in enumerate(splitter.create_documents([parent.text])):
            text = document.page_content
            if text:
                relative_start = next_child_start(parent.text, text, search_from)
                if relative_start is not None:
                    search_from = relative_start + len(text)
                children.append(
                    create_semantic_child_chunk(
                        parent,
                        text,
                        chunk_index,
                        relative_start,
                        embedding_model,
                        breakpoint_threshold_type,
                        breakpoint_threshold_amount,
                    )
                )
    return children


# Semantic configuration


def validate_semantic_options(
    breakpoint_threshold_type: str,
    breakpoint_threshold_amount: float,
    embedding_model: str,
) -> None:
    """Reject invalid semantic chunking options before model loading starts."""

    if not breakpoint_threshold_type.strip():
        raise ValueError("--breakpoint-threshold-type must not be empty.")
    if breakpoint_threshold_amount <= 0:
        raise ValueError("--breakpoint-threshold-amount must be greater than 0.")
    if not embedding_model.strip():
        raise ValueError("Embedding model name must not be empty.")


def create_semantic_splitter(
    embedding_model: str,
    breakpoint_threshold_type: str,
    breakpoint_threshold_amount: float,
) -> Any:
    """Create LangChain's SemanticChunker with multilingual normalized embeddings."""

    try:
        embedding_kwargs = embedding_kwargs_for_model(embedding_model)
        embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            **embedding_kwargs,
        )
        return SemanticChunker(
            embeddings,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )
    except (TypeError, ValueError, RuntimeError, OSError) as error:
        raise RuntimeError(f"Could not initialize semantic chunking backend: {error}") from error


def embedding_kwargs_for_model(embedding_model: str) -> dict[str, dict[str, object]]:
    """Return embedding options required by each supported model family."""

    normalized_model = embedding_model.lower()
    if "e5" in normalized_model:
        return {
            "encode_kwargs": {"normalize_embeddings": True, "prompt": "passage: "},
            "query_encode_kwargs": {"normalize_embeddings": True, "prompt": "query: "},
        }

    return {
        "encode_kwargs": {"normalize_embeddings": True},
        "query_encode_kwargs": {"normalize_embeddings": True},
    }


# Semantic child construction


def create_semantic_child_chunk(
    parent: ParentChunk,                
    text: str,
    chunk_index: int,
    relative_start: int | None,
    embedding_model: str,
    breakpoint_threshold_type: str,
    breakpoint_threshold_amount: float,
) -> ChildChunk:
    """Create one semantic child chunk with parent traceability and inherited metadata."""

    chunk_metadata = {
        "strategy": "semantic_chunking",
        "backend": SEMANTIC_BACKEND,
        "embedding_model": embedding_model,
        "chunk_index": chunk_index,
        "parent_chunk_id": parent.chunk_id,
        "breakpoint_threshold_type": breakpoint_threshold_type,
        "breakpoint_threshold_amount": breakpoint_threshold_amount,
        "split_reason": SEMANTIC_SPLIT_REASON,
        "offset_status": "resolved" if relative_start is not None else "unresolved",
    }
    if relative_start is None:
        chunk_metadata["offset_reason"] = "semantic_chunk_text_not_exact_substring"

    return build_child_chunk(parent, text, chunk_index, relative_start, chunk_metadata)
