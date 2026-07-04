"""Common interface and helpers for child chunking strategies."""

from abc import ABC, abstractmethod
from typing import Any

from pipeline.chunking.models import ChildChunk, ParentChunk
from pipeline.chunking.tokenization import count_tokens


JsonDict = dict[str, Any]


class ChunkingStrategy(ABC):
    """Base interface for deterministic child chunking strategies."""

    name: str

    def __init__(self, max_tokens: int, overlap_tokens: int = 0, min_tokens: int = 0) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens

    @abstractmethod
    def chunk_parent(self, parent: ParentChunk) -> list[ChildChunk]:
        """Create child chunks for one parent chunk."""

    def build_child(
        self,
        parent: ParentChunk,
        text: str,
        chunk_index: int,
        start_char: int,
        end_char: int,
        chunk_metadata: JsonDict,
    ) -> ChildChunk:
        """Create a child chunk with inherited parent metadata and local metadata."""

        inherited = {**parent.metadata, "hierarchy": parent.hierarchy, "source_name": parent.source_name}
        metadata = {"inherited": inherited, "chunk": chunk_metadata}
        return ChildChunk(
            chunk_id=f"{parent.parent_id}:{self.name}:c{chunk_index:04d}",
            parent_id=parent.parent_id,
            document_id=parent.document_id,
            strategy=self.name,
            text=text,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=end_char,
            token_count=count_tokens(text),
            metadata=metadata,
        )
