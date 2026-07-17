"""Convert extracted HTML tables into indexable Markdown files."""

from pathlib import Path


# Conversión de tablas HTML a Markdown
def convert_table_html_to_markdown(html_path: Path, markdown_path: Path) -> Path:
    """Convert one extracted table HTML file to Markdown using Pandoc."""

    try:
        # pyrefly: ignore [missing-import]
        import pypandoc

        markdown = pypandoc.convert_file(str(html_path), "markdown")
    except Exception as error:
        raise RuntimeError(f"Failed to convert table HTML to Markdown: {html_path}") from error

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    return markdown_path


# Conversión por lotes
def convert_table_html_batch(tables_root: Path, output_root: Path) -> list[Path]:
    """Convert table_*.html files under a tables root into derived Markdown files."""

    converted_paths: list[Path] = []
    table_paths = sorted(tables_root.glob("*/table_*.html")) if tables_root.exists() else []
    for html_path in table_paths:
        markdown_path = table_markdown_path(output_root, html_path.parent.name, html_path.stem)
        converted_paths.append(convert_table_html_to_markdown(html_path, markdown_path))
    return converted_paths


# Rutas de salida derivadas
def table_markdown_path(output_root: Path, source_stem: str, table_stem: str) -> Path:
    """Return the derived Markdown output path for one table."""

    return output_root / source_stem / f"{table_stem}.md"
