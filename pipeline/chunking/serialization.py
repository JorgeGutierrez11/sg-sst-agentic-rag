"""JSONL serialization helpers for chunking models."""

import json
from collections.abc import Iterable
from pathlib import Path

from pipeline.chunking.models import ChildChunk, ParentChunk


def read_parent_chunks(path: Path) -> list[ParentChunk]:
    """Read parent chunks from JSONL."""

    return [ParentChunk.from_dict(item) for item in _read_jsonl(path)]


def write_parent_chunks(path: Path, chunks: Iterable[ParentChunk]) -> None:
    """Write parent chunks to JSONL."""

    _write_jsonl(path, (chunk.to_dict() for chunk in chunks))


def read_child_chunks(path: Path) -> list[ChildChunk]:
    """Read child chunks from JSONL."""

    return [ChildChunk.from_dict(item) for item in _read_jsonl(path)]


def write_child_chunks(path: Path, chunks: Iterable[ChildChunk]) -> None:
    """Write child chunks to JSONL."""

    _write_jsonl(path, (chunk.to_dict() for chunk in chunks))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
