"""Normalize chunk and table JSONL records for ChromaDB ingestion."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline.chunking.core.io_jsonl import read_jsonl


ScalarMetadata = str | int | float | bool
ChromaMetadata = dict[str, ScalarMetadata]
JsonDict = dict[str, Any]

@dataclass(frozen=True)
class ChromaRecord:
    """Document, identifier, and flat metadata ready for ChromaDB upsert."""

    id: str
    document: str
    metadata: ChromaMetadata


@dataclass(frozen=True)
class LoadedVectorRecords:
    """Bulk-loaded Chroma records plus source-specific invalid-record counts."""

    records: list[ChromaRecord]
    skipped_child_chunk_count: int = 0
    skipped_table_count: int = 0

    @property
    def skipped_count(self) -> int:
        """Return the total number of source records skipped during loading."""

        return self.skipped_child_chunk_count + self.skipped_table_count


# Corpus readers

def load_vector_record_batch(chunks_path: Path, tables_path: Path) -> LoadedVectorRecords:
    """Load child chunks and table documents into one Chroma-ready batch with skip counts."""

    child_chunks = load_child_chunk_record_batch(chunks_path)
    tables = load_table_document_record_batch(tables_path)
    return LoadedVectorRecords(
        records=child_chunks.records + tables.records,
        skipped_child_chunk_count=child_chunks.skipped_child_chunk_count,
        skipped_table_count=tables.skipped_table_count,
    )

def load_child_chunk_record_batch(path: Path) -> LoadedVectorRecords:
    """Read child chunk JSONL records and skip records that cannot be converted."""

    source_records = read_jsonl(path)
    records = valid_chroma_records(source_records, child_chunk_to_chroma)
    return LoadedVectorRecords(records=records, skipped_child_chunk_count=len(source_records) - len(records))


def load_table_document_record_batch(path: Path) -> LoadedVectorRecords:
    """Read vector-ready table JSONL records and skip records that cannot be converted."""

    source_records = read_jsonl(path)
    records = valid_chroma_records(source_records, table_document_to_chroma)
    return LoadedVectorRecords(records=records, skipped_table_count=len(source_records) - len(records))


def valid_chroma_records(
    source_records: list[JsonDict],
    converter: Callable[[JsonDict], ChromaRecord],
) -> list[ChromaRecord]:
    """Convert source records and preserve only records accepted by the converter."""

    records: list[ChromaRecord] = []
    for source_record in source_records:
        try:
            records.append(converter(source_record))
        except ValueError:
            continue
    return records


# Record normalization

def child_chunk_to_chroma(record: JsonDict) -> ChromaRecord:
    """Convert one child chunk JSON object into a flat ChromaDB record."""

    record_id = required_text(record, "chunk_id")
    document = required_document_text(record, record_id)
    metadata = record_metadata(record)
    inherited = mapping(metadata.get("inherited"))
    hierarchy = mapping(inherited.get("hierarchy"))
    table_keys = table_keys_from_chunk_metadata(metadata)

    return ChromaRecord(
        id=record_id,
        document=document,
        metadata=flat_metadata(
            {
                "document_type": "child_chunk",
                "source_document_id": record.get("source_document_id", ""),
                "source_stem": inherited.get("source_stem", ""),
                "normative_document_type": inherited.get("document_type", ""),
                "year": inherited.get("year", ""),
                "parent_id": record.get("parent_id", ""),
                "title": hierarchy.get("title", ""),
                "chapter": hierarchy.get("chapter", ""),
                "article": hierarchy.get("article", ""),
                "articles": hierarchy.get("articles", ""),
                "paragraph": hierarchy.get("paragraph", ""),
                "numeral": hierarchy.get("numeral", ""),
                "literal": hierarchy.get("literal", ""),
                "start_char": record.get("start_char", 0),
                "end_char": record.get("end_char", 0),
                "has_tables": bool(table_keys),
                "table_keys": ",".join(table_keys),
            }
        ),
    )


def table_document_to_chroma(record: JsonDict) -> ChromaRecord:
    """Convert one vector-ready table JSON object into a flat ChromaDB record."""

    record_id = required_text(record, "id")
    document = required_document_text(record, record_id)
    metadata = required_mapping(record.get("metadata"), "metadata")
    source_stem = required_metadata_text(metadata, "source_stem", record_id)
    table_index = required_metadata_int(metadata, "table_index", record_id)

    return ChromaRecord(
        id=record_id,
        document=document,
        metadata=flat_metadata(
            {
                "document_type": "table",
                "source_stem": source_stem,
                "table_index": table_index,
                "table_key": table_key(source_stem, table_index),
                "linked_placeholder": metadata.get("linked_placeholder", ""),
            }
        ),
    )


def table_keys_from_chunk_metadata(metadata: JsonDict) -> list[str]:
    """Return logical table keys referenced by a child chunk."""

    chunk_metadata = mapping(metadata.get("chunk"))
    tables = chunk_metadata.get("tables", [])
    if not isinstance(tables, list):
        return []

    keys: list[str] = []
    for table in tables:
        table_metadata = mapping(table)
        source_stem = str(table_metadata.get("source_stem", ""))
        if source_stem and "table_index" in table_metadata:
            keys.append(table_key(source_stem, required_metadata_int(table_metadata, "table_index", "child chunk")))
    return keys


def table_key(source_stem: str, table_index: int) -> str:
    """Return the logical table relation key used by chunks and table documents."""

    return f"{source_stem}:{table_index}"


# Validation and metadata helpers

def required_document_text(record: JsonDict, record_id: str) -> str:
    """Return non-empty document text or raise a controlled error."""

    text = str(record.get("text", "")).strip()
    if not text:
        raise ValueError(f"Vector document {record_id!r} has empty text")
    return text


def required_text(record: JsonDict, key: str) -> str:
    """Return a required non-empty string field."""

    value = str(record.get(key, "")).strip()
    if not value:
        raise ValueError(f"Vector source record is missing required field {key!r}")
    return value


def record_metadata(record: JsonDict) -> JsonDict:
    """Return record metadata as a dictionary."""

    return mapping(record.get("metadata"))


def required_mapping(value: Any, field_name: str) -> JsonDict:
    """Return a required object field as a dictionary."""

    if not isinstance(value, dict):
        raise ValueError(f"Vector source record has malformed {field_name!r}")
    return dict(value)


def required_metadata_text(metadata: JsonDict, key: str, record_id: str) -> str:
    """Return a required non-empty text value from metadata."""

    value = str(metadata.get(key, "")).strip()
    if not value:
        raise ValueError(f"Vector document {record_id!r} has empty metadata field {key!r}")
    return value


def required_metadata_int(metadata: JsonDict, key: str, record_id: str) -> int:
    """Return a required integer metadata value or raise a controlled conversion error."""

    try:
        return int(metadata[key])
    except KeyError as error:
        raise ValueError(f"Vector document {record_id!r} is missing metadata field {key!r}") from error
    except (TypeError, ValueError) as error:
        raise ValueError(f"Vector document {record_id!r} has invalid integer metadata field {key!r}") from error


def mapping(value: Any) -> JsonDict:
    """Return mapping values as plain dictionaries and all other values as empty dictionaries."""

    return dict(value) if isinstance(value, dict) else {}


def flat_metadata(metadata: JsonDict) -> ChromaMetadata:
    """Flatten metadata to scalar values compatible with ChromaDB."""

    return {key: scalar_metadata_value(value) for key, value in metadata.items()}


def scalar_metadata_value(value: Any) -> ScalarMetadata:
    """Normalize one metadata value to a scalar Chroma-compatible type."""

    if isinstance(value, bool | int | float | str):
        return value
    if value is None:
        return ""
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)
