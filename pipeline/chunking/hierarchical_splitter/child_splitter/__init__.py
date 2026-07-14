"""Public child chunking API."""

from pipeline.chunking.hierarchical_splitter.child_splitter.semantic import (
    build_semantic_child_chunks,
    create_semantic_child_chunk,
    create_semantic_splitter,
    validate_semantic_options,
    write_semantic_child_output,
)
from pipeline.chunking.hierarchical_splitter.child_splitter.shared import (
    SEMANTIC_BACKEND,
    SEMANTIC_SPLIT_REASON,
    SLIDING_WINDOW_BACKEND,
    SLIDING_WINDOW_SPLIT_REASON,
    ChildBuildResult,
    child_offsets,
    next_child_start,
    stable_child_chunk_id,
)
from pipeline.chunking.hierarchical_splitter.child_splitter.sliding_window import (
    build_sliding_window_child_chunks,
    create_child_chunk,
    create_sliding_window_splitter,
    validate_sliding_window_options,
    write_sliding_window_child_output,
)

__all__ = [
    "ChildBuildResult",
    "SEMANTIC_BACKEND",
    "SEMANTIC_SPLIT_REASON",
    "SLIDING_WINDOW_BACKEND",
    "SLIDING_WINDOW_SPLIT_REASON",
    "build_semantic_child_chunks",
    "build_sliding_window_child_chunks",
    "child_offsets",
    "create_child_chunk",
    "create_semantic_child_chunk",
    "create_semantic_splitter",
    "create_sliding_window_splitter",
    "next_child_start",
    "stable_child_chunk_id",
    "validate_semantic_options",
    "validate_sliding_window_options",
    "write_semantic_child_output",
    "write_sliding_window_child_output",
]
