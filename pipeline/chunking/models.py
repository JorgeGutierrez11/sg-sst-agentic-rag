"""Typed models used by chunking stages."""

from dataclasses import asdict, dataclass, field
from typing import Any


JsonDict = dict[str, Any]


@dataclass(slots=True)
class ParentChunk:
    """Legal-boundary parent chunk enriched with validated document metadata."""

    parent_id: str
    document_id: str
    source_name: str
    text: str
    hierarchy: JsonDict = field(default_factory=dict)
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        """Return a JSON-serializable representation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ParentChunk":
        """Build a parent chunk from JSON-decoded data."""

        return cls(
            parent_id=str(data["parent_id"]),
            document_id=str(data["document_id"]),
            source_name=str(data.get("source_name", data.get("source", ""))),
            text=str(data.get("text", data.get("content", ""))),
            hierarchy=dict(data.get("hierarchy", {})),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class ChildChunk:
    """Strategy-specific child chunk with inherited and local metadata."""

    chunk_id: str
    parent_id: str
    document_id: str
    strategy: str
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        """Return a JSON-serializable representation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ChildChunk":
        """Build a child chunk from JSON-decoded data."""

        return cls(
            chunk_id=str(data["chunk_id"]),
            parent_id=str(data["parent_id"]),
            document_id=str(data["document_id"]),
            strategy=str(data["strategy"]),
            text=str(data.get("text", "")),
            chunk_index=int(data.get("chunk_index", 0)),
            start_char=int(data.get("start_char", 0)),
            end_char=int(data.get("end_char", 0)),
            token_count=int(data.get("token_count", 0)),
            metadata=dict(data.get("metadata", {})),
        )
