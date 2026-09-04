"""Build sliding-window child chunks from parent chunks."""

from pathlib import Path

from pipeline.chunking.config import DEFAULT_TABLES_ROOT
from pipeline.chunking.io_jsonl import read_parent_chunks, write_child_chunks
from pipeline.chunking.hierarchical_splitter.child_splitter.shared import (
    SLIDING_WINDOW_BACKEND,
    SLIDING_WINDOW_SPLIT_REASON,
    build_child_chunk,
    next_child_start,
)
from pipeline.chunking.hierarchical_splitter.models import ChildBuildResult, ChildChunk, ParentChunk
from pipeline.tables.table_references import validate_table_html_references

# Pipeline orchestration

def write_sliding_window_child_output(
    input_path: Path,
    output_path: Path,
    chunk_size: int,
    chunk_overlap: int,
    tables_root: Path = DEFAULT_TABLES_ROOT,
) -> ChildBuildResult:
    """Read parent chunks, write sliding-window child chunks, and return a summary."""

    validate_sliding_window_options(chunk_size, chunk_overlap)
    if not input_path.exists():
        raise FileNotFoundError(f"Parent chunks input does not exist: {input_path}")

    parents = read_parent_chunks(input_path)
    children = build_sliding_window_child_chunks(parents, chunk_size, chunk_overlap)
    validate_table_html_references(children, tables_root)
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
        search_from = 0
        documents = splitter.create_documents([parent.text])
        for chunk_index, document in enumerate(documents):
            text = document.page_content
            if text:
                relative_start = next_child_start(parent.text, text, search_from)
                if relative_start is None:
                    raise ValueError(
                        "Sliding-window chunk text does not match the parent text exactly; "
                        "cannot assign reliable offsets."
                    )
                search_from = relative_start + len(text)
                children.append(
                    create_child_chunk(
                        parent,
                        text,
                        chunk_index,
                        relative_start,
                        chunk_size,
                        chunk_overlap
                    )
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

    try:
        # pyrefly: ignore [missing-import]
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
        )
    except (ImportError, TypeError, ValueError, RuntimeError, OSError) as error:
        raise RuntimeError(f"Could not initialize sliding-window backend: {error}") from error


# Sliding child construction

def create_child_chunk(
    parent: ParentChunk,
    text: str,
    chunk_index: int,
    relative_start: int,
    chunk_size: int,
    chunk_overlap: int,
) -> ChildChunk:
    """Create one child chunk with parent traceability and inherited metadata."""

    return build_child_chunk(
        parent,
        text,
        chunk_index,
        relative_start,
        {
            "strategy": "sliding_window",
            "backend": SLIDING_WINDOW_BACKEND,
            "chunk_index": chunk_index,
            "parent_chunk_id": parent.chunk_id,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "split_reason": SLIDING_WINDOW_SPLIT_REASON,
        },
        require_resolved_offsets=True,
    )
