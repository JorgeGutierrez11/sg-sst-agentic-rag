"""Deterministic metadata extraction for SG-SST legal sources."""

import json
from pathlib import Path
from typing import Any

from pipeline.chunking.legal_boundaries import extract_hierarchy, merge_hierarchy


JsonDict = dict[str, Any]


def load_source_manifest(path: Path | None) -> dict[str, JsonDict]:
    """Load optional source metadata keyed by document id or source stem."""

    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Source manifest must be a JSON object: {path}")
    return {str(key): dict(value) for key, value in data.items() if isinstance(value, dict)}


def infer_document_id(source_path: Path) -> str:
    """Infer a stable document id from a source path stem."""

    return source_path.stem.lower().replace(" ", "_").replace(",", "").replace("__", "_")


def extract_parent_metadata(
    text: str,
    source_path: Path,
    manifest: dict[str, JsonDict] | None = None,
) -> tuple[str, JsonDict, JsonDict]:
    """Extract document id, metadata, and hierarchy without using LLMs."""

    document_id = infer_document_id(source_path)
    manifest_metadata = _manifest_metadata(document_id, source_path.stem, manifest or {})
    document_id = str(manifest_metadata.get("document_id", document_id))
    hierarchy = merge_hierarchy(extract_hierarchy(source_path.stem), extract_hierarchy(text[:4000]))
    metadata = {
        **manifest_metadata,
        "document_id": document_id,
        "source_stem": source_path.stem,
        "source_name": source_path.name,
        "metadata_extraction": "deterministic_manifest_and_regex",
    }
    return document_id, metadata, hierarchy


def _manifest_metadata(document_id: str, source_stem: str, manifest: dict[str, JsonDict]) -> JsonDict:
    return dict(manifest.get(document_id) or manifest.get(source_stem) or manifest.get(source_stem.lower()) or {})
