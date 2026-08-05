"""Ingest normalized SG-SST documents into the base ChromaDB collection."""

from dataclasses import dataclass
from pathlib import Path

from pipeline.chunking.core.config import (
    DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    DEFAULT_TABLE_DOCUMENTS_PATH,
    PROJECT_ROOT,
)
from pipeline.vectorization.chroma_store import DEFAULT_COLLECTION_NAME, open_collection, upsert_records
from pipeline.vectorization.documents import LoadedVectorRecords, load_vector_record_batch


DEFAULT_CHROMA_PATH = PROJECT_ROOT / "data" / "processed" / "chroma"


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
) -> IngestResult:
    """Load vector records and upsert them into a persistent ChromaDB collection."""

    loaded = load_vector_record_batch(chunks_path, tables_path)
    collection = open_collection(persist_path, collection_name)
    upsert_records(collection, loaded.records)
    return build_ingest_result(loaded, persist_path, collection_name)


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
