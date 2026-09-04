"""Ingest normalized SG-SST documents into the base ChromaDB collection."""

import sys
from dataclasses import dataclass
from pathlib import Path

from pipeline.chunking.config import (
    DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    DEFAULT_TABLE_DOCUMENTS_PATH,
    PROJECT_ROOT,
)
from pipeline.vectorization.chroma_store import DEFAULT_COLLECTION_NAME, open_or_create_collection, upsert_records
from pipeline.vectorization.documents import LoadedVectorRecords, load_vector_record_batch


DEFAULT_CHROMA_PATH = PROJECT_ROOT / "data" / "processed" / "chroma"
DEFAULT_INGEST_BATCH_SIZE = 8


@dataclass(frozen=True)
class IngestResult:
    """Summary of one vectorization ingest run."""

    total_count: int
    child_chunk_count: int
    table_count: int
    skipped_child_chunk_count: int
    skipped_table_count: int
    persist_path: Path
    collection_name: str

    @property
    def skipped_count(self) -> int:
        """Return total skipped records from the source JSONL files."""

        return self.skipped_child_chunk_count + self.skipped_table_count


def ingest_base_rag_documents(
    chunks_path: Path = DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    tables_path: Path = DEFAULT_TABLE_DOCUMENTS_PATH,
    persist_path: Path = DEFAULT_CHROMA_PATH,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    batch_size: int = DEFAULT_INGEST_BATCH_SIZE,
) -> IngestResult:
    """Load vector records and upsert them into ChromaDB using memory-safe batches."""

    ensure_source_files_exist(chunks_path, tables_path)
    ensure_batch_size(batch_size)
    loaded = load_vector_record_batch(chunks_path, tables_path)
    print_ingest_start(len(loaded.records), batch_size)
    print_collection_opening(collection_name, persist_path)
    collection = open_or_create_collection(persist_path, collection_name)
    upsert_records(collection, loaded.records, batch_size=batch_size, on_batch_complete=print_batch_progress)
    return build_ingest_result(loaded, persist_path, collection_name)


def print_ingest_start(record_count: int, batch_size: int) -> None:
    """Report the number of records that will be indexed before Chroma embedding starts."""

    print(f"Indexing {record_count} document(s) with batch size {batch_size}...", file=sys.stderr, flush=True)


def print_collection_opening(collection_name: str, persist_path: Path) -> None:
    """Report Chroma collection opening before embedding model initialization can take time."""

    print(f"Opening Chroma collection {collection_name!r}: {persist_path}", file=sys.stderr, flush=True)


def print_batch_progress(batch_index: int, total_batches: int, inserted_count: int) -> None:
    """Report completed Chroma upsert batches so long vectorization runs are visible."""

    percent = (batch_index / total_batches) * 100 if total_batches else 100
    print(
        f"Indexed batch {batch_index}/{total_batches} ({percent:.1f}%) - {inserted_count} document(s)",
        file=sys.stderr,
        flush=True,
    )


def ensure_source_files_exist(chunks_path: Path, tables_path: Path) -> None:
    """Fail before opening ChromaDB when required source JSONL files are missing."""

    missing_paths = [path for path in (chunks_path, tables_path) if not path.exists()]
    if missing_paths:
        missing = ", ".join(str(path) for path in missing_paths)
        raise ValueError(f"Missing vectorization source JSONL file(s): {missing}")


def ensure_batch_size(batch_size: int) -> None:
    """Reject invalid batch sizes before loading the embedding model."""

    if batch_size <= 0:
        raise ValueError("--batch-size must be greater than 0")


def build_ingest_result(loaded: LoadedVectorRecords, persist_path: Path, collection_name: str) -> IngestResult:
    """Build count summary for indexed records."""

    records = loaded.records
    child_chunk_count = sum(1 for record in records if record.metadata["document_type"] == "child_chunk")
    table_count = sum(1 for record in records if record.metadata["document_type"] == "table")
    return IngestResult(
        total_count=len(records),
        child_chunk_count=child_chunk_count,
        table_count=table_count,
        skipped_child_chunk_count=loaded.skipped_child_chunk_count,
        skipped_table_count=loaded.skipped_table_count,
        persist_path=persist_path,
        collection_name=collection_name,
    )
