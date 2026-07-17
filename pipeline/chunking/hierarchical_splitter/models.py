"""Typed data contracts used by the chunking pipeline."""

from pathlib import Path
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

    chunk_id: str               # ID unico del chunk
    source_document_id: str     # ID del documento del cual proviene
    source_path: str            # Ruta del documento
    parent_index: int           # Indice del chunk
    text: str                   # Texto del chunk
    start_char: int             # Indice de inicio
    end_char: int               # Indice de fin
    token_count: int            # Cantidad de tokens
    metadata: JsonDict = field(default_factory=dict) # Metadatos adicionales


@dataclass(frozen=True)
class ChildChunk:
    """Shared data contract for child chunking strategy outputs."""

    chunk_id: str               # ID unico del chunk
    parent_id: str              # ID del parent chunk del cual proviene
    source_document_id: str     # ID del documento del cual proviene
    text: str                   # Texto del chunk
    start_char: int | None      # Indice de inicio
    end_char: int | None        # Indice de fin
    token_count: int            # Cantidad de tokens
    metadata: JsonDict = field(default_factory=dict) # Metadatos adicionales

@dataclass(frozen=True)
class ParentBuildResult:
    """Summary of a parent chunk build run."""

    source_count: int
    chunk_count: int
    output_path: Path

@dataclass(frozen=True)
class ChildBuildResult:
    """Summary of a child chunk build run."""

    parent_count: int   # cantidad de parent chunks
    chunk_count: int    # cantidad de child chunks
    output_path: Path   # ruta donde se guardan los child chunks
