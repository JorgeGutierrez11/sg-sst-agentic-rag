"""Build vector-ready documents from derived Markdown tables."""

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from pipeline.chunking.core.io_jsonl import write_jsonl
from pipeline.chunking.hierarchical_splitter.models import JsonDict
from pipeline.chunking.structural_analysis.metadata_infer import slugify


# Identificación de archivos de tablas derivadas
TABLE_MARKDOWN_FILENAME = re.compile(r"^table_(\d+)\.md$")
ROWSPAN_ATTRIBUTE = re.compile(r"\browspan\s*=", re.IGNORECASE)
MAX_TABLE_DOCUMENT_CHARS = 6000


@dataclass(frozen=True)
class ParsedTableRow:
    """One extracted HTML table row plus minimal structural hints."""

    cells: list[str]
    has_header_cell: bool = False


@dataclass(frozen=True)
class TableDocumentPart:
    """Text and controlled flags for one vector-ready table part."""

    text: str
    oversized_row: bool = False


class TableHTMLParser(HTMLParser):
    """Small HTML table row/cell parser for Pandoc-derived table files."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[ParsedTableRow] = []
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None
        self.current_colspan = 1
        self.current_row_has_header = False
        self.in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.current_row = []
            self.current_row_has_header = False
        elif tag in {"td", "th"} and self.current_row is not None:
            self.current_cell = []
            self.current_colspan = colspan_from_attrs(attrs)
            self.current_row_has_header = self.current_row_has_header or tag == "th"
            self.in_cell = True

    def handle_data(self, data: str) -> None:
        if self.in_cell and self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.current_row is not None and self.current_cell is not None:
            cell_text = normalize_cell_text("".join(self.current_cell))
            self.current_row.extend([cell_text] * self.current_colspan)
            self.current_cell = None
            self.current_colspan = 1
            self.in_cell = False
        elif tag == "tr" and self.current_row is not None:
            if any(cell for cell in self.current_row):
                self.rows.append(ParsedTableRow(self.current_row, self.current_row_has_header))
            self.current_row = None
            self.current_cell = None
            self.current_colspan = 1
            self.current_row_has_header = False
            self.in_cell = False


# Construcción de documentos de tabla
def build_table_documents(markdown_root: Path) -> list[JsonDict]:
    """Return vector-ready table documents from derived Markdown table files."""

    table_paths = sorted(markdown_root.glob("*/table_*.md")) if markdown_root.exists() else []
    return [document for path in table_paths for document in table_documents_from_table_path(path)]


def table_documents_from_table_path(markdown_path: Path) -> list[JsonDict]:
    """Build vector-ready table document parts for one derived Markdown table file."""

    table_index = table_index_from_markdown_path(markdown_path)
    source_stem = markdown_path.parent.name
    html_path = html_path_from_markdown_path(markdown_path)
    parts = table_parts_from_sources(markdown_path, html_path)

    documents = []
    for part_index, part in enumerate(parts):
        documents.append(
            {
                "id": table_document_id(source_stem, table_index, part_index),
                "text": part.text,
                "metadata": table_document_metadata(
                    source_stem,
                    table_index,
                    part_index,
                    len(parts),
                    part.oversized_row,
                ),
            }
        )
    return documents


def table_parts_from_sources(markdown_path: Path, html_path: Path) -> list[TableDocumentPart]:
    """Return table document parts, preferring HTML rows with Markdown fallback."""

    html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    rows = parsed_table_rows_from_html(html) if html else []
    if rows:
        if html_contains_rowspan(html):
            return single_table_document_part(rows)
        return table_document_parts_with_flags(rows)
    return fallback_table_document_parts(markdown_path.read_text(encoding="utf-8"))


def table_rows_from_html(html: str) -> list[list[str]]:
    """Extract ordered table rows and cells from HTML."""

    return [row.cells for row in parsed_table_rows_from_html(html)]


def parsed_table_rows_from_html_path(html_path: Path) -> list[ParsedTableRow]:
    """Extract parsed rows from an HTML file if it exists."""

    if not html_path.exists():
        return []
    return parsed_table_rows_from_html(html_path.read_text(encoding="utf-8"))


def parsed_table_rows_from_html(html: str) -> list[ParsedTableRow]:
    """Extract ordered table rows and cells with minimal header information."""

    parser = TableHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.rows


def html_contains_rowspan(html: str) -> bool:
    """Return True when the source table uses vertical cell spans."""

    return bool(ROWSPAN_ATTRIBUTE.search(html))


def single_table_document_part(rows: list[ParsedTableRow]) -> list[TableDocumentPart]:
    """Return one unsplit table part from all parsed rows."""

    non_empty_rows = [row for row in rows if any(cell.strip() for cell in row.cells)]
    if not non_empty_rows:
        return []
    context_rows, data_rows = split_context_and_data_rows(non_empty_rows)
    return [TableDocumentPart(markdown_table_text(context_rows, data_rows))]


def normalize_cell_text(text: str) -> str:
    """Collapse internal whitespace in a table cell."""

    return " ".join(text.split())


def colspan_from_attrs(attrs: list[tuple[str, str | None]]) -> int:
    """Return a safe positive colspan value from HTML cell attributes."""

    attrs_dict = dict(attrs)
    try:
        colspan = int(attrs_dict.get("colspan") or 1)
    except ValueError:
        return 1
    return max(colspan, 1)


def table_document_parts(rows: list[list[str]], max_chars: int = MAX_TABLE_DOCUMENT_CHARS) -> list[str]:
    """Return Markdown-like table document texts split by row groups."""

    parsed_rows = [ParsedTableRow(cells) for cells in rows if any(cell.strip() for cell in cells)]
    return [part.text for part in table_document_parts_with_flags(parsed_rows, max_chars)]


def table_document_parts_with_flags(
    rows: list[ParsedTableRow],
    max_chars: int = MAX_TABLE_DOCUMENT_CHARS,
) -> list[TableDocumentPart]:
    """Return Markdown-like table parts and flag any individually oversized row."""

    non_empty_rows = [row for row in rows if any(cell.strip() for cell in row.cells)]
    if not non_empty_rows:
        return []

    context_rows, data_rows = split_context_and_data_rows(non_empty_rows)
    parts: list[TableDocumentPart] = []
    current_rows: list[ParsedTableRow] = []

    for row in data_rows:
        candidate_rows = [*current_rows, row]
        candidate_text = markdown_table_text(context_rows, candidate_rows)
        row_text = markdown_table_text(context_rows, [row])
        if len(row_text) > max_chars:
            if current_rows:
                parts.append(TableDocumentPart(markdown_table_text(context_rows, current_rows)))
                current_rows = []
            parts.append(TableDocumentPart(row_text, oversized_row=True))
        elif current_rows and len(candidate_text) > max_chars:
            parts.append(TableDocumentPart(markdown_table_text(context_rows, current_rows)))
            current_rows = [row]
        else:
            current_rows = candidate_rows

    if current_rows or not data_rows:
        parts.append(TableDocumentPart(markdown_table_text(context_rows, current_rows)))
    return parts


def split_context_and_data_rows(rows: list[ParsedTableRow]) -> tuple[list[ParsedTableRow], list[ParsedTableRow]]:
    """Split header/context rows from data rows using simple table-shape heuristics."""

    if rows[0].has_header_cell:
        return [rows[0]], rows[1:]

    max_cell_count = max(len(row.cells) for row in rows)
    header_index = next(index for index, row in enumerate(rows) if len(row.cells) == max_cell_count)
    return rows[: header_index + 1], rows[header_index + 1 :]


def markdown_table_text(context_rows: list[ParsedTableRow], data_rows: list[ParsedTableRow]) -> str:
    """Render table context plus rows as simple Markdown-like text."""

    all_rows = [*context_rows, *data_rows]
    column_count = max((len(row.cells) for row in all_rows), default=1)
    rendered_context = [markdown_row(row.cells, column_count) for row in context_rows]
    rendered_data = [markdown_row(row.cells, column_count) for row in data_rows]
    return "\n".join([*rendered_context, markdown_separator(column_count), *rendered_data])


def markdown_row(cells: list[str], column_count: int) -> str:
    """Render one row with padded cells for stable separators."""

    padded_cells = [*cells, *([""] * max(0, column_count - len(cells)))]
    return "| " + " | ".join(padded_cells[:column_count]) + " |"


def markdown_separator(column_count: int) -> str:
    """Render a Markdown table separator for the selected column count."""

    return "|" + "|".join("---" for _ in range(column_count)) + "|"


def fallback_table_document_parts(markdown: str, max_chars: int = MAX_TABLE_DOCUMENT_CHARS) -> list[TableDocumentPart]:
    """Split existing Markdown into bounded text blocks when HTML rows are unavailable."""

    lines = [line.rstrip() for line in markdown.splitlines() if line.strip()]
    if not lines:
        return [TableDocumentPart(markdown.strip())] if markdown.strip() else []

    parts: list[TableDocumentPart] = []
    current_lines: list[str] = []
    for line in lines:
        candidate = "\n".join([*current_lines, line]) if current_lines else line
        if len(line) > max_chars:
            if current_lines:
                parts.append(TableDocumentPart("\n".join(current_lines)))
                current_lines = []
            parts.append(TableDocumentPart(line, oversized_row=True))
        elif current_lines and len(candidate) > max_chars:
            parts.append(TableDocumentPart("\n".join(current_lines)))
            current_lines = [line]
        else:
            current_lines = [*current_lines, line]
    if current_lines:
        parts.append(TableDocumentPart("\n".join(current_lines)))
    return parts


def html_path_from_markdown_path(markdown_path: Path) -> Path:
    """Resolve the extracted HTML table path corresponding to a derived Markdown table."""

    markdown_root = markdown_path.parents[1]
    if markdown_root.parent.name == "processed":
        tables_root = markdown_root.parent.parent / "interim" / "tables"
    else:
        tables_root = markdown_root.parent / "tables"
    return tables_root / markdown_path.parent.name / markdown_path.with_suffix(".html").name


def table_document_metadata(
    source_stem: str,
    table_index: int,
    part_index: int,
    part_count: int,
    oversized_row: bool,
) -> JsonDict:
    """Return logical metadata for one table document part."""

    return {
        "type": "table",
        "source_stem": source_stem,
        "table_index": table_index,
        "table_part_index": part_index,
        "table_part_count": part_count,
        "table_key": f"{source_stem}:{table_index}",
        "linked_placeholder": f"<!-- TABLE_{table_index} -->",
        "oversized_row": oversized_row,
    }


# Identificadores e índices de documentos
def table_document_id(source_stem: str, table_index: int, part_index: int = 0) -> str:
    """Return a stable ASCII-safe document id for a table part."""

    return f"table-{slugify(source_stem)}-{table_index}-part-{part_index:04d}"


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
