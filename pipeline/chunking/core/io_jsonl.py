"""Deterministic JSONL serialization for chunking artifacts."""

import json
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from pipeline.chunking.hierarchical_splitter.models import ChildChunk, JsonDict, ParentChunk

# records; is a list of ParentChunk or ChildChunk or any other type of chunk
# path: is a Path object to the output file
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
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_parent_chunks(chunks: Iterable[ParentChunk], path: Path) -> int:
    """Write parent chunks to JSONL."""

    return write_jsonl(chunks, path)


def read_parent_chunks(path: Path) -> list[ParentChunk]:
    """Read parent chunks from JSONL."""

    return [ParentChunk(**record) for record in read_jsonl(path)]


def write_child_chunks(chunks: Iterable[ChildChunk], path: Path) -> int:
    """Write child chunks to JSONL."""

    return write_jsonl(chunks, path)


def read_child_chunks(path: Path) -> list[ChildChunk]:
    """Read child chunks from JSONL."""

    return [ChildChunk(**record) for record in read_jsonl(path)]


def to_json_dict(record: Any) -> JsonDict:
    """Convert dataclasses and mappings to JSON-safe dictionaries."""

    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, dict):
        return dict(record)
    raise TypeError(f"Unsupported JSONL record type: {type(record)!r}")