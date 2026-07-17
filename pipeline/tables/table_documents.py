"""Build vector-ready documents from derived Markdown tables."""

import re
from pathlib import Path

from pipeline.chunking.core.io_jsonl import write_jsonl
from pipeline.chunking.hierarchical_splitter.models import JsonDict
from pipeline.chunking.structural_analysis.metadata_infer import slugify


# Identificación de archivos de tablas derivadas
TABLE_MARKDOWN_FILENAME = re.compile(r"^table_(\d+)\.md$")


# Construcción de documentos de tabla
def build_table_documents(markdown_root: Path) -> list[JsonDict]:
    """Return vector-ready table documents from derived Markdown table files."""

    table_paths = sorted(markdown_root.glob("*/table_*.md")) if markdown_root.exists() else []
    return [table_document_from_markdown_path(path) for path in table_paths]


def table_document_from_markdown_path(markdown_path: Path) -> JsonDict:
    """Build one logical table document from a derived Markdown table file."""

    table_index = table_index_from_markdown_path(markdown_path)
    source_stem = markdown_path.parent.name
    return {
        "id": table_document_id(source_stem, table_index),
        "text": markdown_path.read_text(encoding="utf-8"),
        "metadata": {
            "type": "table",
            "source_stem": source_stem,
            "table_index": table_index,
            "linked_placeholder": f"<!-- TABLE_{table_index} -->",
        },
    }


# Identificadores e índices de documentos
def table_document_id(source_stem: str, table_index: int) -> str:
    """Return a stable ASCII-safe document id for a table."""

    return f"table-{slugify(source_stem)}-{table_index}"


def table_index_from_markdown_path(markdown_path: Path) -> int:
    """Extract the table index from a derived table Markdown filename."""

    match = TABLE_MARKDOWN_FILENAME.match(markdown_path.name)
    if not match:
        raise ValueError(f"Expected derived table Markdown filename like table_0.md: {markdown_path}")
    return int(match.group(1))


# Persistencia de documentos vectorizables
def write_table_documents(markdown_root: Path, output_path: Path) -> int:
    """Write vector-ready table documents to JSONL and return the document count."""

    return write_jsonl(build_table_documents(markdown_root), output_path)
