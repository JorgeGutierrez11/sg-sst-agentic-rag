"""Query-only lookup and graph node for linked table first parts."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.models import RetrievedDocument
from pipeline.chunking.io_jsonl import read_jsonl


DEFAULT_TABLE_DOCUMENTS_PATH = Path("data/processed/table_documents.jsonl")


def load_first_table_parts(path: Path = DEFAULT_TABLE_DOCUMENTS_PATH) -> dict[str, RetrievedDocument]:
    """Load the first stored part of each logical table, keyed by table key."""

    lookup: dict[str, RetrievedDocument] = {}
    for record in read_jsonl(path):
        document = first_table_part_from_record(record)
        if document is None:
            continue
        table_key = str(document.metadata["table_key"])
        lookup.setdefault(table_key, document)
    return lookup


def complement_linked_tables(
    documents: list[RetrievedDocument],
    first_table_parts: dict[str, RetrievedDocument],
) -> list[RetrievedDocument]:
    """Append linked first table parts once, in source relation order."""

    if not documents or not first_table_parts:
        return documents

    complemented = list(documents)
    known_document_ids = {
        document_id
        for document in documents
        for document_id in document_ids(document)
    }
    known_relations = {
        relation
        for document in documents
        if (relation := table_relation_identity(document)) is not None
    }

    for table_key in linked_table_keys(documents):
        table_document = first_table_parts.get(table_key)
        if table_document is None:
            continue
        candidate_ids = document_ids(table_document)
        relation = table_relation_identity(table_document)
        if known_document_ids.intersection(candidate_ids) or relation in known_relations:
            continue

        complemented.append(table_document)
        known_document_ids.update(candidate_ids)
        if relation is not None:
            known_relations.add(relation)

    return complemented


def complement_linked_tables_node(
    first_table_parts: dict[str, RetrievedDocument],
) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that complements final relevant evidence with linked tables."""

    def run(state: RagGraphState) -> RagGraphState:
        return {
            "documents": complement_linked_tables(
                state.get("documents", []),
                first_table_parts,
            )
        }

    return run


def first_table_part_from_record(record: dict[str, object]) -> RetrievedDocument | None:
    """Convert one valid parsed part-zero record to a retrieved document."""

    if not isinstance(record.get("metadata"), dict):
        return None

    metadata = dict(record["metadata"])
    if integer_value(metadata.get("table_part_index")) != 0:
        return None

    document_id = str(record.get("id") or "").strip()
    document_text = record.get("text")
    table_key = str(metadata.get("table_key") or "").strip()
    required_metadata = ("table_part_count", "source_stem", "table_index")
    if not document_id or not isinstance(document_text, str) or not document_text.strip() or not table_key:
        return None
    if any(metadata.get(key) in (None, "") for key in required_metadata):
        return None

    metadata.update(
        {
            "document_id": document_id,
            "document_type": "table",
            "table_key": table_key,
            "table_part_index": 0,
        }
    )
    return RetrievedDocument(document=document_text, metadata=metadata)


def linked_table_keys(documents: Iterable[RetrievedDocument]) -> list[str]:
    """Return unique linked table keys in document and metadata order."""

    keys: list[str] = []
    seen: set[str] = set()
    for document in documents:
        for key in normalized_table_keys(document.metadata.get("table_keys")):
            if key not in seen:
                seen.add(key)
                keys.append(key)
    return keys


def normalized_table_keys(value: object) -> list[str]:
    """Normalize Chroma strings and in-memory lists to ordered table keys."""

    raw_keys = value if isinstance(value, (list, tuple)) else str(value or "").split(",")
    return [str(key).strip() for key in raw_keys if str(key).strip()]


def document_ids(document: RetrievedDocument) -> set[str]:
    """Return every available stable document identifier."""

    return {
        str(document.metadata[key])
        for key in ("_document_id", "document_id", "id", "chunk_id")
        if document.metadata.get(key) not in (None, "")
    }


def table_relation_identity(document: RetrievedDocument) -> tuple[str, int] | None:
    """Return the stable logical identity of a table part when available."""

    table_key = str(document.metadata.get("table_key") or "").strip()
    part_index = integer_value(document.metadata.get("table_part_index"))
    if document.metadata.get("document_type") != "table" or not table_key or part_index is None:
        return None
    return table_key, part_index


def integer_value(value: object) -> int | None:
    """Return an integer representation when one is available."""

    if not isinstance(value, (int, str)) or isinstance(value, bool):
        return None
    try:
        return int(value)
    except ValueError:
        return None
