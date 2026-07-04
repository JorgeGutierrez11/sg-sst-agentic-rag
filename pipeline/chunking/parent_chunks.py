"""Parent chunk construction from processed legal corpus sources."""

import json
from pathlib import Path
from typing import Any

from pipeline.chunking.config import GENERATED_CHUNKING_DIRS
from pipeline.chunking.legal_boundaries import merge_hierarchy, split_legal_blocks
from pipeline.chunking.metadata_extraction import extract_parent_metadata, load_source_manifest
from pipeline.chunking.models import ParentChunk


JsonDict = dict[str, Any]
SUPPORTED_TEXT_SUFFIXES = {".md", ".markdown", ".txt"}


def build_parent_chunks(input_path: Path, manifest_path: Path | None = None) -> list[ParentChunk]:
    """Build deterministic parent chunks from JSONL, Markdown, text, or a directory."""

    manifest = load_source_manifest(manifest_path)
    files = _source_files(input_path)
    parents: list[ParentChunk] = []
    for source_path in files:
        parents.extend(_parents_from_file(source_path, manifest))
    return parents


def _source_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    suffixes = SUPPORTED_TEXT_SUFFIXES | {".jsonl"}
    return sorted(
        path
        for path in input_path.rglob("*")
        if path.is_file()
        and path.suffix.lower() in suffixes
        and not _is_generated_chunking_output(path)
    )


def _is_generated_chunking_output(path: Path) -> bool:
    """Return whether a discovered source is a generated chunking artifact."""

    resolved_path = path.resolve()
    for generated_dir in GENERATED_CHUNKING_DIRS:
        try:
            resolved_path.relative_to(generated_dir.resolve())
        except ValueError:
            continue
        return True
    return False


def _parents_from_file(source_path: Path, manifest: dict[str, JsonDict]) -> list[ParentChunk]:
    if source_path.suffix.lower() == ".jsonl":
        return _parents_from_jsonl(source_path, manifest)
    return _parents_from_text(source_path, source_path.read_text(encoding="utf-8"), manifest)


def _parents_from_jsonl(source_path: Path, manifest: dict[str, JsonDict]) -> list[ParentChunk]:
    parents: list[ParentChunk] = []
    for index, line in enumerate(source_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        data = json.loads(line)
        if _looks_like_parent_chunk(data):
            parents.append(ParentChunk.from_dict(data))
            continue
        text = str(data.get("text", data.get("content", data.get("markdown", ""))))
        if not text.strip():
            continue
        document_id, metadata, hierarchy = extract_parent_metadata(text, source_path, manifest)
        metadata.update({key: value for key, value in data.items() if key not in {"text", "content", "markdown"}})
        parents.extend(_parents_from_text_block(source_path, document_id, metadata, hierarchy, text, index))
    return parents


def _parents_from_text(source_path: Path, text: str, manifest: dict[str, JsonDict]) -> list[ParentChunk]:
    document_id, metadata, hierarchy = extract_parent_metadata(text, source_path, manifest)
    return _parents_from_text_block(source_path, document_id, metadata, hierarchy, text, 0)


def _parents_from_text_block(
    source_path: Path,
    document_id: str,
    metadata: JsonDict,
    base_hierarchy: JsonDict,
    text: str,
    source_index: int,
) -> list[ParentChunk]:
    blocks = split_legal_blocks(text)
    parents: list[ParentChunk] = []
    for block_index, block in enumerate(blocks):
        parent_metadata = {
            **metadata,
            "source_start_char": block.start_char,
            "source_end_char": block.end_char,
            "parent_builder": "legal_boundary_regex",
        }
        parents.append(
            ParentChunk(
                parent_id=f"{document_id}:p{source_index:03d}-{block_index:04d}",
                document_id=document_id,
                source_name=source_path.name,
                text=block.text,
                hierarchy=merge_hierarchy(base_hierarchy, block.hierarchy),
                metadata=parent_metadata,
            )
        )
    return parents


def _looks_like_parent_chunk(data: JsonDict) -> bool:
    required = {"parent_id", "document_id", "text", "hierarchy", "metadata"}
    return required.issubset(data.keys())
