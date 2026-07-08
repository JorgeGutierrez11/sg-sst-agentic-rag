"""Typed data contracts used by the chunking pipeline."""

from dataclasses import dataclass, field
from typing import Any

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class SourceDocument:
    """Metadata describing one cleaned Markdown source document."""

    document_id: str
    source_stem: str
    source_path: str
    source_name: str
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class ParentChunk:
    """A legal-boundary parent chunk built before child chunking strategies run."""

    chunk_id: str
    source_document_id: str
    source_path: str
    parent_index: int
    text: str
    start_char: int
    end_char: int
    token_count: int
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class ChildChunk:
    """Shared data contract for child chunking strategy outputs."""

    chunk_id: str
    parent_id: str
    source_document_id: str
    text: str
    start_char: int
    end_char: int
    token_count: int
    metadata: JsonDict = field(default_factory=dict)
