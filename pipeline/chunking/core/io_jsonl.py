"""Deterministic JSONL serialization for chunking artifacts."""

import json
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from pipeline.chunking.hierarchical_splitter.models import ChildChunk, JsonDict, ParentChunk


# General JSONL helpers

def write_jsonl(records: Iterable[Any], path: Path) -> int:
    """Write records to a deterministic JSONL file and return the record count."""

    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(to_json_dict(record), ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> list[JsonDict]:
    """Read a JSONL file into dictionaries."""

    if not path.exists():
        return []
    records: list[JsonDict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            records.append(parse_jsonl_line(line, path, line_number))
    return records

# Convierte los objetos en diccionarios para que puedan ser guardados en JSONL
def to_json_dict(record: Any) -> JsonDict:
    """Convert dataclasses and mappings to JSON-safe dictionaries."""

    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, dict):
        return dict(record)
    raise TypeError(f"Unsupported JSONL record type: {type(record)!r}")


def parse_jsonl_line(line: str, path: Path, line_number: int) -> JsonDict:
    """Parse one JSONL line with a user-facing error message."""

    try:
        record = json.loads(line)
    except JSONDecodeError as error:
        raise ValueError(f"Invalid JSONL in {path} at line {line_number}: {error.msg}") from error
    if not isinstance(record, dict):
        raise ValueError(f"Invalid JSONL in {path} at line {line_number}: expected an object")
    return record


# Parent chunk helpers

def write_parent_chunks(chunks: Iterable[ParentChunk], path: Path) -> int:
    """Write parent chunks to JSONL."""

    return write_jsonl(chunks, path)


def read_parent_chunks(path: Path) -> list[ParentChunk]:
    """Read parent chunks from JSONL."""

    return [parent_chunk_from_record(record, path, index) for index, record in enumerate(read_jsonl(path), start=1)]


def parent_chunk_from_record(record: JsonDict, path: Path, line_number: int) -> ParentChunk:
    """Build a parent chunk from one JSONL record."""

    try:
        return ParentChunk(**record)
    except TypeError as error:
        raise ValueError(f"Invalid parent chunk record in {path} at line {line_number}: {error}") from error


# Child chunk helpers

def write_child_chunks(chunks: Iterable[ChildChunk], path: Path) -> int:
    """Write child chunks to JSONL."""

    return write_jsonl(chunks, path)


def read_child_chunks(path: Path) -> list[ChildChunk]:
    """Read child chunks from JSONL."""

    return [child_chunk_from_record(record, path, index) for index, record in enumerate(read_jsonl(path), start=1)]


def child_chunk_from_record(record: JsonDict, path: Path, line_number: int) -> ChildChunk:
    """Build a child chunk from one JSONL record."""

    try:
        return ChildChunk(**record)
    except TypeError as error:
        raise ValueError(f"Invalid child chunk record in {path} at line {line_number}: {error}") from error
