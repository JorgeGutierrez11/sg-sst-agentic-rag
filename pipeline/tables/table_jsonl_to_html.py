"""Convert table JSONL documents into standalone HTML previews."""

import argparse
import html
import json
from pathlib import Path
from typing import Any


DEFAULT_INPUT_PATH = Path("data/processed/table_documents.jsonl")
DEFAULT_OUTPUT_DIR = Path("data/processed/tables_htlm")


# CLI

def main(argv: list[str] | None = None) -> int:
    """Run the table JSONL to HTML preview converter."""

    args = parse_args(argv)
    records = read_jsonl(args.input_path)
    output_count = write_table_html_files(records, args.output_dir)
    write_index_file(records, args.output_dir)
    print(f"Wrote {output_count} table HTML preview(s) to {args.output_dir}")
    print(f"Index: {args.output_dir / 'index.html'}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="Convert data/processed/table_documents.jsonl into readable HTML previews."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Input table JSONL path. Default: {DEFAULT_INPUT_PATH}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for HTML previews. Default: {DEFAULT_OUTPUT_DIR}",
    )
    return parser.parse_args(argv)


# JSONL loading

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSONL records from disk with line-specific errors."""

    if not path.exists():
        raise FileNotFoundError(f"Input JSONL not found: {path}")

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSONL in {path} at line {line_number}: {error.msg}") from error
        if not isinstance(record, dict):
            raise ValueError(f"Invalid JSONL in {path} at line {line_number}: expected an object")
        records.append(record)
    return records


# HTML generation

def write_table_html_files(records: list[dict[str, Any]], output_dir: Path) -> int:
    """Write one HTML preview file per table JSONL record."""

    output_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        file_path = output_dir / f"{safe_filename(record_id(record))}.html"
        file_path.write_text(table_preview_html(record), encoding="utf-8")
    return len(records)


def write_index_file(records: list[dict[str, Any]], output_dir: Path) -> None:
    """Write a navigable index for generated table previews."""

    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in records:
        metadata = metadata_dict(record)
        doc_id = record_id(record)
        file_name = f"{safe_filename(doc_id)}.html"
        rows.append(
            "<tr>"
            f"<td><a href=\"{html.escape(file_name)}\">{html.escape(doc_id)}</a></td>"
            f"<td>{html.escape(str(metadata.get('table_key', '')))}</td>"
            f"<td>{html.escape(str(metadata.get('table_part_index', '')))}</td>"
            f"<td>{html.escape(str(metadata.get('table_part_count', '')))}</td>"
            f"<td>{len(record_text(record))}</td>"
            "</tr>"
        )

    index_html = html_page(
        title="Table chunk previews",
        body=(
            "<h1>Table chunk previews</h1>"
            "<table>"
            "<thead><tr>"
            "<th>ID</th><th>Table key</th><th>Part</th><th>Total parts</th><th>Chars</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        ),
    )
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")


def table_preview_html(record: dict[str, Any]) -> str:
    """Build one complete HTML preview page for a table document."""

    metadata = metadata_dict(record)
    doc_id = record_id(record)
    text = record_text(record)
    metadata_items = "".join(
        f"<dt>{html.escape(str(key))}</dt><dd>{html.escape(str(value))}</dd>"
        for key, value in sorted(metadata.items())
    )
    body = (
        f"<h1>{html.escape(doc_id)}</h1>"
        "<p><a href=\"index.html\">Back to index</a></p>"
        "<section>"
        "<h2>Metadata</h2>"
        f"<dl>{metadata_items}</dl>"
        "</section>"
        "<section>"
        "<h2>Rendered table chunk</h2>"
        f"{markdown_table_to_html(text)}"
        "</section>"
        "<section>"
        "<h2>Raw chunk text</h2>"
        f"<pre>{html.escape(text)}</pre>"
        "</section>"
    )
    return html_page(doc_id, body)


def markdown_table_to_html(text: str) -> str:
    """Render the table chunk text as an HTML table when it uses pipe rows."""

    rows = [parse_pipe_row(line) for line in text.splitlines() if parse_pipe_row(line)]
    rows = [row for row in rows if not is_separator_row(row)]
    if not rows:
        return f"<pre>{html.escape(text)}</pre>"

    html_rows = []
    for index, row in enumerate(rows):
        cell_tag = "th" if index == 0 else "td"
        cells = "".join(f"<{cell_tag}>{html.escape(cell)}</{cell_tag}>" for cell in row)
        html_rows.append(f"<tr>{cells}</tr>")
    return f"<table><tbody>{''.join(html_rows)}</tbody></table>"


def parse_pipe_row(line: str) -> list[str]:
    """Parse one simple Markdown pipe-table row."""

    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def is_separator_row(row: list[str]) -> bool:
    """Return whether a parsed Markdown row is only a separator."""

    return all(cell and set(cell) <= {"-", ":"} for cell in row)


def html_page(title: str, body: str) -> str:
    """Wrap body content in a readable standalone HTML document."""

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.45; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ccc; padding: 0.45rem; vertical-align: top; }}
    th {{ background: #f3f4f6; text-align: left; }}
    pre {{ background: #f7f7f7; border: 1px solid #ddd; overflow: auto; padding: 1rem; white-space: pre-wrap; }}
    dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 0.35rem 1rem; }}
    dt {{ font-weight: 700; }}
    dd {{ margin: 0; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


# Record helpers

def record_id(record: dict[str, Any]) -> str:
    """Return the table document id."""

    value = record.get("id")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Table JSONL record is missing a non-empty string id")
    return value


def record_text(record: dict[str, Any]) -> str:
    """Return the table document text."""

    value = record.get("text")
    if not isinstance(value, str):
        raise ValueError(f"Table JSONL record {record_id(record)!r} is missing string text")
    return value


def metadata_dict(record: dict[str, Any]) -> dict[str, Any]:
    """Return metadata as a dictionary."""

    metadata = record.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def safe_filename(value: str) -> str:
    """Return a filesystem-safe HTML filename stem."""

    safe_value = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in value)
    return safe_value.strip("-") or "table"


if __name__ == "__main__":
    raise SystemExit(main())
