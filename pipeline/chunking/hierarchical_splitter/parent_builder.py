"""Build legal-boundary parent chunks from cleaned Markdown sources."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pipeline.chunking.core.config import is_generated_output_path
from pipeline.chunking.core.io_jsonl import write_parent_chunks
from pipeline.chunking.hierarchical_splitter.models import JsonDict, ParentChunk, SourceDocument
from pipeline.chunking.hierarchical_splitter.tokenization import estimate_token_count
from pipeline.chunking.structural_analysis.boundaries import BoundaryMatch, find_article_boundaries
from pipeline.chunking.structural_analysis.metadata_infer import (
    build_source_document,
    inherited_metadata_for_parent,
    load_source_manifest,
)


@dataclass(frozen=True)
class ParentBuildResult:
    """Summary of a parent chunk build run."""

    source_count: int
    chunk_count: int
    output_path: Path


def discover_markdown_sources(input_dir: Path) -> list[Path]:
    """Discover cleaned Markdown files while excluding generated chunk outputs."""

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    return sorted(
        path
        for path in input_dir.rglob("*.md")
        if path.is_file() and not is_generated_output_path(path) and not _is_hidden_path(path)
    )


def build_parent_chunks(input_dir: Path, manifest_path: Path) -> list[ParentChunk]:
    """Build parent chunks for every discovered Markdown source."""

    sources = discover_markdown_sources(input_dir)
    manifest = load_source_manifest(manifest_path)
    return build_parent_chunks_from_sources(sources, manifest)


def build_parent_chunks_from_sources(sources: list[Path], manifest: dict[str, JsonDict]) -> list[ParentChunk]:
    """Build parent chunks from already discovered sources and loaded manifest metadata."""

    chunks: list[ParentChunk] = []
    for source_path in sources:
        text = source_path.read_text(encoding="utf-8")
        source_document = build_source_document(source_path, text, manifest)
        chunks.extend(build_parent_chunks_for_document(source_path, text, source_document))
    return chunks


def build_parent_chunks_for_document(
    source_path: Path,
    text: str,
    source_document: SourceDocument,
) -> list[ParentChunk]:
    """Build parent chunks from one source document using article boundaries when available."""

    if not text.strip():
        return []
    spans = article_spans(text) or [(0, len(text), None)]
    return [create_parent_chunk(source_path, source_document, text, index, span) for index, span in enumerate(spans)]


def write_parent_chunk_output(input_dir: Path, output_path: Path, manifest_path: Path) -> ParentBuildResult:
    """Build and write parent chunks to JSONL."""

    sources = discover_markdown_sources(input_dir)
    manifest = load_source_manifest(manifest_path)
    chunks = build_parent_chunks_from_sources(sources, manifest)
    write_parent_chunks(chunks, output_path)
    return ParentBuildResult(source_count=len(sources), chunk_count=len(chunks), output_path=output_path)


def article_spans(text: str) -> list[tuple[int, int, BoundaryMatch | None]]:
    """Return start/end spans split by legal article boundaries."""

    boundaries = find_article_boundaries(text)
    spans: list[tuple[int, int, BoundaryMatch | None]] = []
    for index, boundary in enumerate(boundaries):
        start_char = boundary.start_char
        end_char = boundaries[index + 1].start_char if index + 1 < len(boundaries) else len(text)
        spans.append((start_char, end_char, boundary))
    return spans


def create_parent_chunk(
    source_path: Path,
    source_document: SourceDocument,
    full_text: str,
    parent_index: int,
    span: tuple[int, int, BoundaryMatch | None],
) -> ParentChunk:
    """Create one parent chunk from a character span."""

    start_char, end_char, boundary = span
    raw_text = full_text[start_char:end_char]
    text = raw_text.strip()
    adjusted_start = start_char + (len(raw_text) - len(raw_text.lstrip()))
    adjusted_end = adjusted_start + len(text)
    inherited_metadata = inherited_metadata_for_parent(source_document, text)
    chunk_metadata = {
        "strategy": "parent_article_boundary" if boundary else "parent_whole_document",
        "split_reason": "article_boundary" if boundary else "no_article_boundary_found",
        "parent_index": parent_index,
    }
    return ParentChunk(
        chunk_id=stable_parent_chunk_id(source_document.document_id, parent_index, adjusted_start, adjusted_end),
        source_document_id=source_document.document_id,
        source_path=str(source_path),
        parent_index=parent_index,
        text=text,
        start_char=adjusted_start,
        end_char=adjusted_end,
        token_count=estimate_token_count(text),
        metadata={"inherited": inherited_metadata, "chunk": chunk_metadata},
    )


def stable_parent_chunk_id(source_document_id: str, parent_index: int, start_char: int, end_char: int) -> str:
    """Return a stable parent chunk id based on source and offsets."""

    payload = f"{source_document_id}:{parent_index}:{start_char}:{end_char}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"parent-{source_document_id}-{parent_index:04d}-{digest}"


def _is_hidden_path(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)
