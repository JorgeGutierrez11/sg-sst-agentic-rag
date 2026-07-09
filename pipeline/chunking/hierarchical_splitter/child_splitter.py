"""Build sliding-window child chunks from parent chunks."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pipeline.chunking.core.io_jsonl import read_parent_chunks, write_child_chunks
from pipeline.chunking.hierarchical_splitter.models import ChildChunk, ParentChunk
from pipeline.chunking.hierarchical_splitter.tokenization import estimate_token_count

# pyrefly: ignore [missing-import]
from langchain_text_splitters import RecursiveCharacterTextSplitter


SLIDING_WINDOW_BACKEND = "langchain_recursive_character_text_splitter"
SLIDING_WINDOW_SPLIT_REASON = "recursive_token_window"


# Build result model


@dataclass(frozen=True)
class ChildBuildResult:
    """Summary of a child chunk build run."""

    parent_count: int   # cantidad de parent chunks
    chunk_count: int    # cantidad de child chunks
    output_path: Path   # ruta donde se guardan los child chunks


# Pipeline orchestration


def write_sliding_window_child_output(
    input_path: Path,
    output_path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> ChildBuildResult:
    """Read parent chunks, write sliding-window child chunks, and return a summary."""

    validate_sliding_window_options(chunk_size, chunk_overlap)
    if not input_path.exists():
        raise FileNotFoundError(f"Parent chunks input does not exist: {input_path}")

    parents = read_parent_chunks(input_path)
    children = build_sliding_window_child_chunks(parents, chunk_size, chunk_overlap)
    write_child_chunks(children, output_path)
    return ChildBuildResult(
        parent_count=len(parents),
        chunk_count=len(children),
        output_path=output_path
    )


def build_sliding_window_child_chunks(
    parents: list[ParentChunk],
    chunk_size: int,
    chunk_overlap: int,
) -> list[ChildChunk]:
    """Split parent chunks using LangChain's recursive token-aware window."""

    validate_sliding_window_options(chunk_size, chunk_overlap)
    splitter = create_sliding_window_splitter(chunk_size, chunk_overlap)
    children: list[ChildChunk] = []
    for parent in parents:
        documents = splitter.create_documents([parent.text])
        for chunk_index, document in enumerate(documents):
            text = document.page_content
            if text:
                relative_start = int(document.metadata.get("start_index", 0))
                children.append(
                    create_child_chunk(parent, text, chunk_index, relative_start, chunk_size, chunk_overlap)
                )
    return children


# Sliding-window configuration


def validate_sliding_window_options(chunk_size: int, chunk_overlap: int) -> None:
    """Reject invalid sliding-window sizes before splitting starts."""

    if chunk_size <= 0:
        raise ValueError("--chunk-size must be greater than 0.")
    if chunk_overlap < 0:
        raise ValueError("--chunk-overlap must be greater than or equal to 0.")
    if chunk_overlap >= chunk_size:
        raise ValueError("--chunk-overlap must be lower than --chunk-size.")


def create_sliding_window_splitter(chunk_size: int, chunk_overlap: int):
    """Create the LangChain splitter lazily so CLI help stays dependency-light."""

    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )


# Child chunk construction


def create_child_chunk(
    parent: ParentChunk,
    text: str,
    chunk_index: int,
    relative_start: int,
    chunk_size: int,
    chunk_overlap: int,
) -> ChildChunk:
    """Create one child chunk with parent traceability and inherited metadata."""

    start_char, end_char = child_offsets(parent, text, relative_start)
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
            "chunk": {
                "strategy": "sliding_window",
                "backend": SLIDING_WINDOW_BACKEND,
                "chunk_index": chunk_index,
                "parent_chunk_id": parent.chunk_id,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "split_reason": SLIDING_WINDOW_SPLIT_REASON,
            },
        },
    )


def child_offsets(parent: ParentChunk, child_text: str, relative_start: int) -> tuple[int, int]:
    """Return source-document offsets for a child text inside its parent."""

    matched_start = parent.text.find(child_text, relative_start)
    if matched_start < 0:
        matched_start = relative_start
    start_char = parent.start_char + matched_start
    end_char = start_char + len(child_text)
    return start_char, end_char


def stable_child_chunk_id(parent_id: str, chunk_index: int, start_char: int, end_char: int) -> str:
    """Return a stable child chunk id based on parent, index, and offsets."""

    payload = f"{parent_id}:{chunk_index}:{start_char}:{end_char}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"child-{parent_id}-{chunk_index:04d}-{digest}"
