"""Shared helpers for child chunk builders."""

import hashlib

from pipeline.chunking.hierarchical_splitter.models import ChildChunk, ParentChunk
from pipeline.chunking.hierarchical_splitter.tokenization import estimate_token_count

SLIDING_WINDOW_BACKEND = "langchain_recursive_character_text_splitter"
SLIDING_WINDOW_SPLIT_REASON = "recursive_token_window"
SEMANTIC_BACKEND = "langchain_semantic_chunker"
SEMANTIC_SPLIT_REASON = "semantic_breakpoint"


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

# Shared child helpers

# saca el offset del child chunk dentro del parent chunk, ejemplo:
# parent: "Hola mundo, este es un texto de prueba" (offset 0, length 35)
# child: "este es un texto de prueba" (offset 0, length 27)
# relative_start: 0
# return: (13, 40)

def child_offsets(parent: ParentChunk, child_text: str, relative_start: int | None) -> tuple[int | None, int | None]:
    """Return source-document offsets for a child text inside its parent."""

    if relative_start is None:
        return None, None
    if relative_start < 0:
        raise ValueError("Child chunk offset cannot be negative.")

    if parent.text[relative_start:relative_start + len(child_text)] != child_text:
        return None, None

    start_char = parent.start_char + relative_start
    end_char = start_char + len(child_text)
    return start_char, end_char


def build_child_chunk(
    parent: ParentChunk,
    text: str,
    chunk_index: int,
    relative_start: int | None,
    chunk_metadata: dict,
    require_resolved_offsets: bool = False,
) -> ChildChunk:
    """Create one child chunk with shared parent traceability and inherited metadata."""

    start_char, end_char = child_offsets(parent, text, relative_start)
    if require_resolved_offsets and (start_char is None or end_char is None):
        raise ValueError(
            "Child chunk text does not match the parent text exactly; "
            "cannot assign reliable offsets."
        )

    return ChildChunk(
        chunk_id=stable_child_chunk_id(parent.chunk_id, chunk_index, start_char, end_char),
        parent_id=parent.chunk_id,
        source_document_id=parent.source_document_id,
        text=text,
        start_char=start_char,
        end_char=end_char,
        token_count=estimate_token_count(text),
        metadata={
            "inherited": dict(parent.metadata.get("inherited", {})),
            "chunk": chunk_metadata,
        },
    )


def next_child_start(parent_text: str, child_text: str, search_from: int) -> int | None:
    """Return the next exact child offset, preserving order when text repeats."""

    matched_start = parent_text.find(child_text, search_from)
    if matched_start >= 0:
        return matched_start

    matched_start = parent_text.find(child_text)
    if matched_start >= 0:
        return matched_start

    return None


def stable_child_chunk_id(parent_id: str, chunk_index: int, start_char: int | None, end_char: int | None) -> str:
    """Return a stable child chunk id based on parent, index, and offsets."""

    payload = f"{parent_id}:{chunk_index}:{start_char}:{end_char}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"child-{parent_id}-{chunk_index:04d}-{digest}"
