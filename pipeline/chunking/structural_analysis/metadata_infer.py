"""Deterministic source and structural metadata extraction."""

import hashlib
import json
import re
from json import JSONDecodeError
from pathlib import Path

from pipeline.chunking.hierarchical_splitter.models import JsonDict, SourceDocument
from pipeline.chunking.structural_analysis.boundaries import extract_first_boundary_value


MANIFEST_DOCUMENTS_KEY = "documents"


def load_source_manifest(path: Path) -> dict[str, JsonDict]:
    """Load source metadata from a JSON manifest."""

    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as error:
        message = f"Source manifest is not valid JSON: {path} ({error.msg} at line {error.lineno})"
        raise ValueError(message) from error
    if not isinstance(data, dict):
        raise ValueError(f"Source manifest must contain a JSON object: {path}")
    documents = data.get(MANIFEST_DOCUMENTS_KEY, data)
    if not isinstance(documents, dict):
        raise ValueError(f"Source manifest documents must be a JSON object: {path}")
    return {str(key): value for key, value in documents.items() if isinstance(value, dict)}


def infer_document_id(path: Path) -> str:
    """Create a stable document id from the Markdown source stem."""

    slug = slugify(path.stem)
    digest = hashlib.sha1(path.stem.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}"


def build_source_document(path: Path, text: str, manifest: dict[str, JsonDict]) -> SourceDocument:
    """Build source-level metadata from manifest, filename, and Markdown text."""

    document_id = infer_document_id(path)
    source_stem = path.stem
    manifest_metadata = manifest.get(document_id, manifest.get(source_stem, {}))
    inferred_metadata = infer_source_metadata(path, text)
    metadata = merge_metadata(inferred_metadata, manifest_metadata)
    return SourceDocument(
        document_id=document_id,
        source_stem=source_stem,
        source_path=str(path),
        source_name=str(metadata.get("source_name", source_stem)),
        metadata=metadata,
    )


def infer_source_metadata(path: Path, text: str) -> JsonDict:
    """Infer source metadata without external services or LLM calls."""

    return without_empty_values(
        {
            "source_stem": path.stem,
            "source_name": path.stem,
            "document_type": infer_document_type(path.stem),
            "year": infer_year(path.stem),
            "title": extract_first_boundary_value(text, "title"),
            "chapter": extract_first_boundary_value(text, "chapter"),
            "section": extract_first_boundary_value(text, "section"),
            "legal_source": "official_candidate",
        }
    )


def extract_structural_metadata(text: str) -> JsonDict:
    """Extract structural legal metadata from a text span."""

    hierarchy = without_empty_values(
        {
            "title": extract_first_boundary_value(text, "title"),
            "chapter": extract_first_boundary_value(text, "chapter"),
            "section": extract_first_boundary_value(text, "section"),
            "article": extract_first_boundary_value(text, "article"),
            "paragraph": extract_first_boundary_value(text, "paragraph"),
            "numeral": extract_first_boundary_value(text, "numeral"),
            "literal": extract_first_boundary_value(text, "literal"),
        }
    )
    return {"hierarchy": hierarchy} if hierarchy else {"hierarchy": {}}


def inherited_metadata_for_parent(source_document: SourceDocument, parent_text: str) -> JsonDict:
    """Merge source metadata with parent-specific structural metadata."""

    structural_metadata = extract_structural_metadata(parent_text)
    return merge_metadata(source_document.metadata, structural_metadata)


def merge_metadata(*metadata_items: JsonDict) -> JsonDict:
    """Merge metadata dictionaries recursively from left to right."""

    merged: JsonDict = {}
    for metadata in metadata_items:
        merged = _deep_merge(merged, metadata)
    return without_empty_values(merged)


def slugify(value: str) -> str:
    """Convert a source name into an ASCII-safe stable slug."""

    normalized = value.lower()
    replacements = str.maketrans("áéíóúüñ", "aeiouun")
    normalized = normalized.translate(replacements)
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "document"


def infer_document_type(source_stem: str) -> str | None:
    """Infer normative document type from the source filename."""

    match = re.match(r"\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)", source_stem)
    return match.group(1).lower() if match else None


def infer_year(source_stem: str) -> int | None:
    """Infer a four-digit year from the source filename."""

    match = re.search(r"\b(19|20)\d{2}\b", source_stem)
    return int(match.group(0)) if match else None


def without_empty_values(metadata: JsonDict) -> JsonDict:
    """Return metadata without None values or empty strings."""

    return {key: value for key, value in metadata.items() if value not in (None, "")}


def _deep_merge(left: JsonDict, right: JsonDict) -> JsonDict:
    merged = dict(left)
    for key, value in right.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
