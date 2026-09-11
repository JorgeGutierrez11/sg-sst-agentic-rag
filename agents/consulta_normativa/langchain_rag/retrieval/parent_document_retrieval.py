"""Runtime parent-document expansion for small-to-big retrieval."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from agents.consulta_normativa.langchain_rag.models import RetrievedDocument
from pipeline.chunking.io_jsonl import read_parent_chunks


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class ParentChildConsistencyReport:
    """Compact report for child chunks whose parent_id must exist in parents."""

    total_child_chunks: int
    children_with_parent_id: int


    children_with_missing_parent: int # Es muy poco probable que un chunk sin padre exista

    @property
    def missing_parent_ratio(self) -> float:
        """Return the share of parent-linked children whose parent is missing."""

        if self.children_with_parent_id == 0:
            return 0.0
        return self.children_with_missing_parent / self.children_with_parent_id


def load_parent_documents(parents_path: Path) -> dict[str, RetrievedDocument]:
    """Load parent chunks as full-text documents keyed by parent chunk_id."""

    if not parents_path.exists():
        raise FileNotFoundError(f"Parent chunks JSONL not found: {parents_path}")

    return build_parent_lookup(read_parent_chunks(parents_path), parents_path)


def build_parent_lookup(records: list[Any], parents_path: Path | None = None) -> dict[str, RetrievedDocument]:
    """Build a parent chunk lookup keyed by chunk_id from JSONL-like records."""

    lookup: dict[str, RetrievedDocument] = {}
    source = str(parents_path) if parents_path is not None else "parent records"

    for index, record in enumerate(records, start=1):
        parent_record = parent_record_mapping(record)
        chunk_id = required_text(parent_record, "chunk_id", source, index)
        text = required_text(parent_record, "text", source, index)

        lookup[chunk_id] = RetrievedDocument(
            document=text,
            metadata=parent_metadata(parent_record, chunk_id)
        )
    return lookup

# Core
def expand_parent_documents(
    documents: list[RetrievedDocument],
    parent_lookup: dict[str, RetrievedDocument],
) -> list[RetrievedDocument]:
    """Replace final child chunks with full parents while preserving ranking order."""

    expanded: list[RetrievedDocument] = []
    expanded_by_parent_id: dict[str, int] = {}

    for document in documents:
        if not is_expandable_child(document):
            expanded.append(document)
            continue

        parent_id = str(document.metadata.get("parent_id") or "")
        parent = parent_lookup.get(parent_id)
        if parent is None:
            expanded.append(with_missing_parent_fallback(document))
            continue

        child_id = document_id(document)
        if parent_id in expanded_by_parent_id:
            parent_index = expanded_by_parent_id[parent_id]
            expanded[parent_index] = append_child_trace(expanded[parent_index], child_id)
            continue

        expanded_by_parent_id[parent_id] = len(expanded)
        expanded.append(expanded_parent_document(parent, document, parent_id, child_id))

    return expanded


def parent_child_consistency_report(
    child_records: list[JsonDict],
    parent_lookup: dict[str, RetrievedDocument],
) -> ParentChildConsistencyReport:
    """Summarize whether child record parent_id values resolve to loaded parents."""

    children_with_parent_id = 0
    missing_parent_count = 0

    for child in child_records:
        parent_id = str(child.get("parent_id") or "").strip()
        if not parent_id:
            continue
        children_with_parent_id += 1
        if parent_id not in parent_lookup:
            missing_parent_count += 1

    return ParentChildConsistencyReport(
        total_child_chunks=len(child_records),
        children_with_parent_id=children_with_parent_id,
        children_with_missing_parent=missing_parent_count,
    )


def parent_metadata(record: JsonDict, chunk_id: str) -> JsonDict:
    """Return flat parent metadata useful for references and context rendering."""

    metadata = mapping(record.get("metadata"))
    inherited = mapping(metadata.get("inherited"))
    chunk = mapping(metadata.get("chunk"))
    hierarchy = mapping(inherited.get("hierarchy") or metadata.get("hierarchy"))
    table_keys = table_keys_from_parent_metadata(metadata)

    return compact_metadata(
        {
            "document_id": chunk_id,
            "document_type": "parent_chunk",
            "source_document_id": record.get("source_document_id", ""),
            "source_stem": inherited.get("source_stem", metadata.get("source_stem", "")),
            "normative_document_type": inherited.get("document_type", metadata.get("document_type", "")),
            "year": inherited.get("year", metadata.get("year", "")),
            "parent_index": record.get("parent_index", ""),
            "title": hierarchy.get("title", ""),
            "chapter": hierarchy.get("chapter", ""),
            "article": hierarchy.get("article", ""),
            "articles": hierarchy.get("articles", ""),
            "paragraph": hierarchy.get("paragraph", ""),
            "numeral": hierarchy.get("numeral", ""),
            "literal": hierarchy.get("literal", ""),
            "start_char": record.get("start_char", ""),
            "end_char": record.get("end_char", ""),
            "token_count": record.get("token_count", ""),
            "has_tables": bool(table_keys),
            "table_keys": ",".join(table_keys),
            "parent_strategy": chunk.get("strategy", ""),
        }
    )


def expanded_parent_document(
    parent: RetrievedDocument,
    child: RetrievedDocument,
    parent_id: str,
    child_id: str,
) -> RetrievedDocument:
    """Return a parent document annotated with child-level retrieval trace."""

    metadata = dict(parent.metadata)
    retrieval_sources = child.metadata.get("_retrieval_sources")

    metadata.update(
        {
            "parent_expansion_applied": True,
            "expanded_parent_id": parent_id,
            "expanded_from_child_id": child_id,
            "expanded_from_child_ids": [child_id],
            "expanded_from_document_type": child.metadata.get("document_type", ""),
        }
    )

    if retrieval_sources:
        metadata["_retrieval_sources"] = retrieval_sources

    return RetrievedDocument(document=parent.document, metadata=metadata)


def append_child_trace(parent: RetrievedDocument, child_id: str) -> RetrievedDocument:
    """Record an additional child chunk that triggered an already-expanded parent."""

    metadata = dict(parent.metadata)
    child_ids = list(metadata.get("expanded_from_child_ids", []))
    if child_id not in child_ids:
        child_ids.append(child_id)
    metadata["expanded_from_child_ids"] = child_ids
    return RetrievedDocument(document=parent.document, metadata=metadata)


def with_missing_parent_fallback(document: RetrievedDocument) -> RetrievedDocument:
    """Return the original child document annotated with a parent lookup fallback."""

    metadata = dict(document.metadata)
    metadata["parent_expansion_fallback"] = "missing_parent"
    return RetrievedDocument(document=document.document, metadata=metadata)


def is_expandable_child(document: RetrievedDocument) -> bool:
    """Return True when the document is a final child chunk with a usable parent id."""

    return document.metadata.get("document_type") == "child_chunk" and bool(str(document.metadata.get("parent_id") or ""))

def document_id(document: RetrievedDocument) -> str:
    """Return the best available retrieved-document identifier for expansion traceability."""

    for key in ("_document_id", "document_id", "chunk_id"):
        value = document.metadata.get(key)
        if value:
            return str(value)
    return ""


def table_keys_from_parent_metadata(metadata: JsonDict) -> list[str]:
    """Return logical table keys referenced by a parent chunk metadata block."""

    chunk = mapping(metadata.get("chunk"))
    tables = chunk.get("tables", metadata.get("tables", []))
    if not isinstance(tables, list):
        return []

    keys: list[str] = []
    for table in tables:
        table_metadata = mapping(table)
        source_stem = str(table_metadata.get("source_stem", ""))
        if source_stem and "table_index" in table_metadata:
            keys.append(f"{source_stem}:{table_metadata['table_index']}")
    return keys


# sanitation functions
def required_text(record: JsonDict, key: str, source: str, line_number: int) -> str:
    """Return a required non-empty text field from one JSONL record."""

    value = str(record.get(key, "")).strip()
    if not value:
        raise ValueError(f"Invalid parent chunk record in {source} at line {line_number}: missing {key!r}")
    return value


def mapping(value: Any) -> JsonDict:
    """Return a dictionary when value is mapping-like, otherwise an empty mapping."""

    return dict(value) if isinstance(value, dict) else {}


def compact_metadata(metadata: JsonDict) -> JsonDict:
    """Drop empty metadata fields while preserving explicit false and zero values."""

    return {key: value for key, value in metadata.items() if value not in (None, "")}


def parent_record_mapping(record: Any) -> JsonDict:
    """Return a parent chunk record as a plain mapping for lookup construction."""

    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, Mapping):
        return dict(record)
    raise TypeError(f"Unsupported parent chunk record type: {type(record)!r}")
