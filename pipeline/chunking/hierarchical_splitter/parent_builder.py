"""Build legal-boundary parent chunks from cleaned Markdown sources."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pipeline.chunking.core.config import DEFAULT_TABLES_ROOT, is_generated_output_path
from pipeline.chunking.core.io_jsonl import write_parent_chunks
from pipeline.chunking.hierarchical_splitter.models import JsonDict, ParentBuildResult, ParentChunk, SourceDocument
from pipeline.chunking.hierarchical_splitter.tokenization import estimate_token_count
from pipeline.chunking.structural_analysis.boundaries import BoundaryMatch, find_article_boundaries
from pipeline.chunking.structural_analysis.metadata_infer import (
    build_source_document,
    inherited_metadata_for_parent,
    load_source_manifest,
)
from pipeline.tables.table_references import table_references_for_text, validate_table_html_references

# Configuración local

SMALL_PARENT_TOKEN_THRESHOLD = 250
MAX_GROUPED_PARENT_TOKENS = 1500

ParentSpan = tuple[int, int, BoundaryMatch | None]


# Descubrimiento de fuentes

def discover_markdown_sources(input_dir: Path) -> list[Path]:
    """Discover cleaned Markdown files while excluding generated chunk outputs."""

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    return sorted(
        path
        for path in input_dir.rglob("*.md")
        if path.is_file()
        and not is_generated_output_path(path)
        and not _is_hidden_path(path.relative_to(input_dir))
    )


# Orquestación de construcción

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

    boundaries = find_article_boundaries(text)
    spans = group_small_article_spans(text, article_spans(text, boundaries)) or [(0, len(text), None)]
    return [
        create_parent_chunk(source_path, source_document, text, index, span, boundaries)
        for index, span in enumerate(spans)
    ]


def write_parent_chunk_output(
    input_dir: Path,
    output_path: Path,
    manifest_path: Path,
    tables_root: Path = DEFAULT_TABLES_ROOT,
) -> ParentBuildResult:
    """Build and write parent chunks to JSONL."""

    sources = discover_markdown_sources(input_dir)
    manifest = load_source_manifest(manifest_path)
    chunks = build_parent_chunks_from_sources(sources, manifest)
    validate_table_html_references(chunks, tables_root)
    write_parent_chunks(chunks, output_path)
    return ParentBuildResult(source_count=len(sources), chunk_count=len(chunks), output_path=output_path)


# Cálculo de spans por artículo

def article_spans(text: str, boundaries: list[BoundaryMatch]) -> list[ParentSpan]:
    """Return start/end spans split by legal article boundaries."""

    spans: list[ParentSpan] = []
    if boundaries and text[: boundaries[0].start_char].strip():
        spans.append((0, boundaries[0].start_char, None))
    for index, boundary in enumerate(boundaries):
        start_char = boundary.start_char
        end_char = boundaries[index + 1].start_char if index + 1 < len(boundaries) else len(text)
        if end_char <= start_char:
            continue
        spans.append((start_char, end_char, boundary))
    return spans


# Agrupación de artículos pequeños

def group_small_article_spans(text: str, spans: list[ParentSpan]) -> list[ParentSpan]:
    """Group consecutive article spans when the current parent would be too small."""

    grouped_spans: list[ParentSpan] = []
    index = 0
    while index < len(spans):
        group_start, group_end, boundary = spans[index]
        next_index = index + 1
        while next_index < len(spans) and should_continue_small_group(
            text,
            group_start,
            group_end,
            spans[next_index - 1],
            spans[next_index],
        ):
            group_end = spans[next_index][1]
            next_index += 1
        grouped_spans.append((group_start, group_end, boundary))
        index = next_index
    return merge_trailing_small_article_span(text, grouped_spans)


def should_continue_small_group(
    text: str,
    group_start: int,
    group_end: int,
    current_span: ParentSpan,
    next_span: ParentSpan,
) -> bool:
    """Return True when adding the next article keeps a small group within limits."""

    if current_span[2] is None or next_span[2] is None:
        return False

    current_text = text[group_start:group_end].strip()
    if estimate_token_count(current_text) >= SMALL_PARENT_TOKEN_THRESHOLD:
        return False

    candidate_text = text[group_start:next_span[1]].strip()
    return estimate_token_count(candidate_text) <= MAX_GROUPED_PARENT_TOKENS


def merge_trailing_small_article_span(text: str, grouped_spans: list[ParentSpan]) -> list[ParentSpan]:
    """Merge trailing small articles backward, cascading while the tail stays small."""

    spans = list(grouped_spans)
    while len(spans) >= 2:
        previous_span = spans[-2]
        last_span = spans[-1]
        if previous_span[2] is None or last_span[2] is None:
            break

        last_text = text[last_span[0] : last_span[1]].strip()
        if estimate_token_count(last_text) >= SMALL_PARENT_TOKEN_THRESHOLD:
            break

        candidate_text = text[previous_span[0] : last_span[1]].strip()
        if estimate_token_count(candidate_text) > MAX_GROUPED_PARENT_TOKENS:
            break

        merged_span = (previous_span[0], last_span[1], previous_span[2])
        spans = [*spans[:-2], merged_span]

    return spans


# Creación de parent chunks

def create_parent_chunk(
    source_path: Path,
    source_document: SourceDocument,
    full_text: str,
    parent_index: int,
    span: ParentSpan,
    boundaries: list[BoundaryMatch],
) -> ParentChunk:
    """Create one parent chunk from a character span."""

    start_char, end_char, boundary = span
    raw_text = full_text[start_char:end_char]
    text = raw_text.strip()
    adjusted_start = start_char + (len(raw_text) - len(raw_text.lstrip()))
    adjusted_end = adjusted_start + len(text)
    inherited_metadata = inherited_metadata_for_parent(source_document, text)
    add_grouped_article_traceability(inherited_metadata, boundaries, start_char, end_char)
    strategy = chunk_strategy(end_char, boundary, boundaries)
    chunk_metadata = {
        "strategy": strategy,
        "split_reason": chunk_split_reason(end_char, boundary, boundaries),
        "parent_index": parent_index,
    }
    table_refs = table_references_for_text(text, source_document.source_stem)
    if table_refs:
        chunk_metadata["tables"] = table_refs
    if strategy == "parent_document_preamble":
        chunk_metadata["section_type"] = "preamble"
        chunk_metadata["indexable"] = False
    return ParentChunk(
        chunk_id=stable_parent_chunk_id(source_document.document_id, parent_index, text),
        source_document_id=source_document.document_id,
        source_path=str(source_path),
        parent_index=parent_index,
        text=text,
        start_char=adjusted_start,
        end_char=adjusted_end,
        token_count=estimate_token_count(text),
        metadata={"inherited": inherited_metadata, "chunk": chunk_metadata},
    )


# Metadata y trazabilidad

def add_grouped_article_traceability(
    metadata: JsonDict,
    boundaries: list[BoundaryMatch],
    start_char: int,
    end_char: int,
) -> None:
    """Add article-list traceability only when one parent contains multiple articles.

    Filtra los boundaries ya calculados por rango de caracteres en vez de volver a
    correr la regex de detección de artículos sobre el texto del chunk.
    """

    article_values = [b.value for b in boundaries if start_char <= b.start_char < end_char]
    if len(article_values) <= 1:
        return
    hierarchy = metadata.setdefault("hierarchy", {})
    hierarchy["articles"] = article_values


# Estrategias e identificadores

def chunk_strategy(end_char: int, boundary: BoundaryMatch | None, boundaries: list[BoundaryMatch]) -> str:
    """Return the parent chunking strategy label for a span."""

    if boundary:
        return "parent_article_boundary"
    if is_document_preamble(end_char, boundaries):
        return "parent_document_preamble"
    return "parent_whole_document"


def chunk_split_reason(end_char: int, boundary: BoundaryMatch | None, boundaries: list[BoundaryMatch]) -> str:
    """Return the parent chunk split reason for a span."""

    if boundary:
        return "article_boundary"
    if is_document_preamble(end_char, boundaries):
        return "document_preamble_before_first_article"
    return "no_article_boundary_found"


def is_document_preamble(end_char: int, boundaries: list[BoundaryMatch]) -> bool:
    """Return True when a span ends before a later article boundary."""

    return any(boundary.start_char >= end_char for boundary in boundaries)


def stable_parent_chunk_id(source_document_id: str, parent_index: int, text: str) -> str:
    """Return a stable parent chunk id based on source and chunk content."""

    payload = f"{source_document_id}:{text}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"parent-{source_document_id}-{parent_index:04d}-{digest}"


# Helpers internos

def _is_hidden_path(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)
