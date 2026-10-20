"""Read-only validation for published or staged corpus artifacts."""

import json
import shutil
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline.chunking.io_jsonl import read_jsonl
from pipeline.vectorization.documents import load_vector_record_batch


class ArtifactValidationError(Exception):
    """Raised when corpus artifacts do not describe one consistent build."""


@dataclass(frozen=True)
class ArtifactValidationResult:
    """Counts verified across corpus sources and retrieval indexes."""

    parent_count: int
    source_record_count: int


ChromaIdsReader = Callable[[Path], set[str]]
Bm25RecordsReader = Callable[[Path], list[Mapping[str, Any]]]


def validate_corpus_artifacts(
    parents_path: Path,
    children_path: Path,
    table_documents_path: Path,
    chroma_path: Path,
    bm25_path: Path,
    *,
    chroma_ids_reader: ChromaIdsReader | None = None,
    bm25_records_reader: Bm25RecordsReader | None = None,
) -> ArtifactValidationResult:
    """Validate parent links plus Chroma and BM25 source identities."""

    _require_non_empty_file(parents_path, "parent chunks")
    _require_non_empty_file(children_path, "child chunks")
    _require_file(table_documents_path, "table documents")
    _require_directory(chroma_path, "Chroma database")
    _require_directory(bm25_path, "BM25 index")

    parents = read_jsonl(parents_path)
    children = read_jsonl(children_path)
    parent_ids = {_required_id(record, "chunk_id", "parent chunk") for record in parents}
    _validate_parent_links(children, parent_ids)

    source_records = load_vector_record_batch(children_path, table_documents_path)
    if source_records.skipped_count:
        raise ArtifactValidationError(
            f"Skipped source records: {source_records.skipped_count}"
        )
    source_ids = {record.id for record in source_records.records}
    if len(source_ids) != len(source_records.records):
        raise ArtifactValidationError("Duplicate source record IDs")

    chroma_ids = (chroma_ids_reader or read_chroma_ids)(chroma_path)
    bm25_records = (bm25_records_reader or read_bm25_records)(bm25_path)
    bm25_ids = {_required_id(record, "id", "BM25 record") for record in bm25_records}
    if len(bm25_ids) != len(bm25_records):
        raise ArtifactValidationError("Duplicate BM25 record IDs")
    _validate_index_ids(source_ids, chroma_ids, bm25_ids)
    return ArtifactValidationResult(
        parent_count=len(parent_ids),
        source_record_count=len(source_ids),
    )


def validate_index_consistency(
    collection: Any,
    bm25_index: Any,
    parent_lookup: Mapping[str, Any],
) -> None:
    """Validate loaded runtime indexes without initializing online services."""

    corpus = list(getattr(bm25_index, "corpus", None) or [])
    chroma_ids = {str(record_id) for record_id in collection.get(include=[])["ids"]}
    bm25_ids = {_required_id(record, "id", "BM25 record") for record in corpus}
    problems: list[str] = []
    if collection.count() != len(corpus):
        problems.append(
            f"Index record count mismatch: Chroma has {collection.count()} records, "
            f"BM25 has {len(corpus)}"
        )
    if chroma_ids != bm25_ids:
        problems.append(
            "Index ID mismatch: "
            f"{describe_ids(chroma_ids - bm25_ids, 'Chroma')}; "
            f"{describe_ids(bm25_ids - chroma_ids, 'BM25')}"
        )
    # parent_id está en metadata; las tablas no tienen padre
    parent_ids = [
        parent_id
        for record in corpus
        if (parent_id := str(dict(record.get("metadata") or {}).get("parent_id") or "").strip())
    ]
    missing_parents = sum(1 for parent_id in parent_ids if parent_id not in parent_lookup)
    if missing_parents:
        problems.append(
            f"Missing parent chunks: {missing_parents} of {len(parent_ids)} child chunks "
            "reference a parent not found in parent chunks"
        )
    if problems:
        raise ArtifactValidationError("; ".join(problems))


def read_chroma_ids(chroma_path: Path) -> set[str]:
    """Read Chroma identifiers from an isolated temporary database copy."""

    from pipeline.vectorization.chroma_store import DEFAULT_COLLECTION_NAME

    with tempfile.TemporaryDirectory(prefix="sg-sst-chroma-validation-") as directory:
        copied_path = Path(directory) / "chroma"
        shutil.copytree(chroma_path, copied_path)
        # pyrefly: ignore [missing-import]
        import chromadb

        collection = chromadb.PersistentClient(path=str(copied_path)).get_collection(DEFAULT_COLLECTION_NAME)
        return {str(record_id) for record_id in collection.get(include=[])["ids"]}


def read_bm25_records(bm25_path: Path) -> list[Mapping[str, Any]]:
    """Read the persisted BM25 corpus records without loading the retrieval model."""

    corpus_path = bm25_path / "corpus.jsonl"
    _require_non_empty_file(corpus_path, "BM25 corpus")
    records: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(corpus_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ArtifactValidationError(
                f"Invalid BM25 corpus JSONL at line {line_number}: {error.msg}"
            ) from error
        if not isinstance(record, dict):
            raise ArtifactValidationError(f"Invalid BM25 corpus record at line {line_number}")
        records.append(record)
    return records


def describe_ids(ids: set[str], index_name: str, sample_size: int = 5) -> str:
    """Describe identifier differences with a bounded sorted sample."""

    description = f"{len(ids)} only in {index_name}"
    if not ids:
        return description
    sample = sorted(ids)[:sample_size]
    if len(ids) > sample_size:
        sample.append("...")
    return f"{description} ({', '.join(sample)})"


def _validate_parent_links(children: list[dict[str, Any]], parent_ids: set[str]) -> None:
    missing_parent_ids = {
        _required_id(child, "parent_id", "child chunk")
        for child in children
        if _required_id(child, "parent_id", "child chunk") not in parent_ids
    }
    if missing_parent_ids:
        raise ArtifactValidationError(
            f"Missing parent chunks: {len(missing_parent_ids)} unresolved parent IDs"
        )


def _validate_index_ids(source_ids: set[str], chroma_ids: set[str], bm25_ids: set[str]) -> None:
    problems: list[str] = []
    if len(chroma_ids) != len(source_ids) or len(bm25_ids) != len(source_ids):
        problems.append(
            f"Index record count mismatch: source has {len(source_ids)} records, "
            f"Chroma has {len(chroma_ids)}, BM25 has {len(bm25_ids)}"
        )
    if chroma_ids != source_ids or bm25_ids != source_ids:
        problems.append(
            "Index ID mismatch: "
            f"{describe_ids(chroma_ids - source_ids, 'Chroma')}; "
            f"{describe_ids(bm25_ids - source_ids, 'BM25')}"
        )
    if problems:
        raise ArtifactValidationError("; ".join(problems))


def _required_id(record: Mapping[str, Any], key: str, label: str) -> str:
    value = str(record.get(key, "")).strip()
    if not value:
        raise ArtifactValidationError(f"{label} is missing required ID {key!r}")
    return value


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ArtifactValidationError(f"Missing corpus artifact: {label} ({path})")


def _require_non_empty_file(path: Path, label: str) -> None:
    _require_file(path, label)
    if path.stat().st_size == 0:
        raise ArtifactValidationError(f"Empty corpus artifact: {label} ({path})")


def _require_directory(path: Path, label: str) -> None:
    if not path.is_dir():
        raise ArtifactValidationError(f"Missing corpus artifact: {label} ({path})")
