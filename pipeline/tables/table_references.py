"""Helpers for detecting and validating table placeholders in chunk text."""

import re
from pathlib import Path
from typing import Any

from pipeline.chunking.hierarchical_splitter.models import JsonDict


# Detección de placeholders
TABLE_PLACEHOLDER = re.compile(r"<!--\s*TABLE_(\d+)\s*-->")


def table_references_for_text(text: str, source_stem: str) -> list[JsonDict]:
    """Return minimal table metadata for placeholders found in text."""
    return [
        {
            "placeholder": match.group(0),
            "table_index": int(match.group(1)),
            "source_stem": source_stem,
        }
        for match in TABLE_PLACEHOLDER.finditer(text)
    ]


def table_html_path(tables_root: Path, source_stem: str, table_index: int) -> Path:
    """Return the conventional HTML path for one extracted table."""

    validate_source_stem(source_stem)
    return tables_root / source_stem / f"table_{table_index}.html"


# Validación de rutas de origen
def validate_source_stem(source_stem: str) -> None:
    """Reject source stems that could escape the tables root."""

    if not source_stem or source_stem in {".", ".."}:
        raise ValueError(f"Unsafe table source stem: {source_stem!r}")
    if Path(source_stem).is_absolute() or "/" in source_stem or "\\" in source_stem:
        raise ValueError(f"Unsafe table source stem: {source_stem!r}")


# Auditoría de referencias a tablas
def missing_table_html_paths(chunks: list[Any], tables_root: Path) -> list[Path]:
    """Return referenced table HTML paths that do not exist on disk."""

    missing_paths: list[Path] = []
    for chunk in chunks:
        metadata = chunk_metadata(chunk)
        for table_ref in metadata.get("chunk", {}).get("tables", []):
            table_path = table_html_path(tables_root, str(table_ref["source_stem"]), int(table_ref["table_index"]))
            if not table_path.exists():
                missing_paths.append(table_path)
    return missing_paths


def audit_table_references(chunks: list[Any], tables_root: Path) -> tuple[list[str], list[str]]:
    """Return missing referenced tables and existing tables without chunk references."""

    referenced_paths = referenced_table_html_paths(chunks, tables_root)
    existing_paths = set(tables_root.rglob("table_*.html")) if tables_root.exists() else set()

    missing_files = sorted(str(path) for path in referenced_paths if not path.exists())
    orphaned_tables = sorted(str(path) for path in existing_paths - referenced_paths)
    return missing_files, orphaned_tables


def validate_table_html_references(chunks: list[Any], tables_root: Path) -> None:
    """Raise a controlled error when chunks reference missing table HTML files."""

    missing_paths = missing_table_html_paths(chunks, tables_root)
    if missing_paths:
        raise ValueError(f"Chunk references missing table file: {missing_paths[0]}")


def referenced_table_html_paths(chunks: list[Any], tables_root: Path) -> set[Path]:
    """Return conventional HTML paths referenced by chunk table metadata."""

    referenced_paths: set[Path] = set()
    for chunk in chunks:
        metadata = chunk_metadata(chunk)
        for table_ref in metadata.get("chunk", {}).get("tables", []):
            referenced_paths.add(table_html_path(tables_root, str(table_ref["source_stem"]), int(table_ref["table_index"])))
    return referenced_paths


# Acceso uniforme a metadatos de chunks
def chunk_metadata(chunk: Any) -> JsonDict:
    """Return metadata from a chunk dataclass or chunk record."""

    if isinstance(chunk, dict):
        metadata = chunk.get("metadata", {})
    else:
        metadata = getattr(chunk, "metadata", {})
    return metadata if isinstance(metadata, dict) else {}
