"""Ingest normalized SG-SST documents into a local BM25S sparse index."""

import sys
from dataclasses import dataclass
from pathlib import Path

from pipeline.chunking.config import (
    DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    DEFAULT_TABLE_DOCUMENTS_PATH,
    PROJECT_ROOT,
)
from pipeline.sparse_indexing.bm25_store import build_bm25_index, save_bm25_index
from pipeline.vectorization.documents import LoadedVectorRecords, load_vector_record_batch

DEFAULT_BM25_PATH = PROJECT_ROOT / "data" / "processed" / "bm25"


@dataclass(frozen=True)
class SparseIndexResult:
    """Summary of one sparse BM25 indexing run."""

    total_count: int
    child_chunk_count: int
    table_count: int
    skipped_child_chunk_count: int
    skipped_table_count: int
    persist_path: Path

    @property
    def skipped_count(self) -> int:
        """Return total skipped records from the source JSONL files."""

        return self.skipped_child_chunk_count + self.skipped_table_count


def ingest_sparse_bm25_documents(
    chunks_path: Path = DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    tables_path: Path = DEFAULT_TABLE_DOCUMENTS_PATH,
    persist_path: Path = DEFAULT_BM25_PATH,
) -> SparseIndexResult:
    """Load vector records and persist them as a BM25S sparse index."""

    ensure_source_files_exist(chunks_path, tables_path)
    loaded = load_vector_record_batch(chunks_path, tables_path)
    print_indexing_start(len(loaded.records), persist_path)
    retriever, corpus = build_bm25_index(loaded.records)
    save_bm25_index(retriever, persist_path, corpus)
    return build_sparse_index_result(loaded, persist_path)


def ensure_source_files_exist(chunks_path: Path, tables_path: Path) -> None:
    """Fail before opening BM25S when required source JSONL files are missing."""

    missing_paths = [path for path in (chunks_path, tables_path) if not path.exists()]
    if missing_paths:
        missing = ", ".join(str(path) for path in missing_paths)
        raise ValueError(f"Missing sparse indexing source JSONL file(s): {missing}")


def print_indexing_start(record_count: int, persist_path: Path) -> None:
    """Report the number of records that will be indexed before BM25S starts."""

    print(f"Indexing {record_count} document(s) into BM25: {persist_path}", file=sys.stderr, flush=True)


def build_sparse_index_result(loaded: LoadedVectorRecords, persist_path: Path) -> SparseIndexResult:
    """Build count summary for indexed sparse records."""

    records = loaded.records
    child_chunk_count = sum(1 for record in records if record.metadata["document_type"] == "child_chunk")
    table_count = sum(1 for record in records if record.metadata["document_type"] == "table")
    return SparseIndexResult(
        total_count=len(records),
        child_chunk_count=child_chunk_count,
        table_count=table_count,
        skipped_child_chunk_count=loaded.skipped_child_chunk_count,
        skipped_table_count=loaded.skipped_table_count,
        persist_path=persist_path,
    )
