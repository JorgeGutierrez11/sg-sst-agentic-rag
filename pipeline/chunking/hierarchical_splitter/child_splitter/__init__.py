"""Public child chunking API."""

from pipeline.chunking.hierarchical_splitter.child_splitter.regex_constrained_semantic import (
    build_regex_constrained_semantic_child_chunks,
    extract_text_units,
    write_regex_constrained_semantic_child_output,
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


def _semantic_export(name: str):
    from pipeline.chunking.hierarchical_splitter.child_splitter import semantic

    return getattr(semantic, name)


def _sliding_window_export(name: str):
    from pipeline.chunking.hierarchical_splitter.child_splitter import sliding_window

    return getattr(sliding_window, name)


def write_semantic_child_output(*args, **kwargs):
    """Lazy public wrapper for semantic child output generation."""

    return _semantic_export("write_semantic_child_output")(*args, **kwargs)


def build_semantic_child_chunks(*args, **kwargs):
    """Lazy public wrapper for semantic child chunk building."""

    return _semantic_export("build_semantic_child_chunks")(*args, **kwargs)


def create_semantic_child_chunk(*args, **kwargs):
    """Lazy public wrapper for semantic child chunk construction."""

    return _semantic_export("create_semantic_child_chunk")(*args, **kwargs)


def create_semantic_splitter(*args, **kwargs):
    """Lazy public wrapper for semantic splitter creation."""

    return _semantic_export("create_semantic_splitter")(*args, **kwargs)


def validate_semantic_options(*args, **kwargs):
    """Lazy public wrapper for semantic option validation."""

    return _semantic_export("validate_semantic_options")(*args, **kwargs)


def write_sliding_window_child_output(*args, **kwargs):
    """Lazy public wrapper for sliding-window child output generation."""

    return _sliding_window_export("write_sliding_window_child_output")(*args, **kwargs)


def build_sliding_window_child_chunks(*args, **kwargs):
    """Lazy public wrapper for sliding-window child chunk building."""

    return _sliding_window_export("build_sliding_window_child_chunks")(*args, **kwargs)


def create_child_chunk(*args, **kwargs):
    """Lazy public wrapper for sliding-window child chunk construction."""

    return _sliding_window_export("create_child_chunk")(*args, **kwargs)


def create_sliding_window_splitter(*args, **kwargs):
    """Lazy public wrapper for sliding-window splitter creation."""

    return _sliding_window_export("create_sliding_window_splitter")(*args, **kwargs)


def validate_sliding_window_options(*args, **kwargs):
    """Lazy public wrapper for sliding-window option validation."""

    return _sliding_window_export("validate_sliding_window_options")(*args, **kwargs)

__all__ = [
    "ChildBuildResult",
    "SEMANTIC_BACKEND",
    "SEMANTIC_SPLIT_REASON",
    "SLIDING_WINDOW_BACKEND",
    "SLIDING_WINDOW_SPLIT_REASON",
    "build_semantic_child_chunks",
    "build_regex_constrained_semantic_child_chunks",
    "build_sliding_window_child_chunks",
    "child_offsets",
    "create_child_chunk",
    "create_semantic_child_chunk",
    "create_semantic_splitter",
    "create_sliding_window_splitter",
    "extract_text_units",
    "next_child_start",
    "stable_child_chunk_id",
    "validate_semantic_options",
    "validate_sliding_window_options",
    "write_semantic_child_output",
    "write_regex_constrained_semantic_child_output",
    "write_sliding_window_child_output",
]
