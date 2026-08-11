"""Command line interface for SG-SST table processing operations."""

import argparse
import sys
from pathlib import Path

from pipeline.chunking.core.config import (
    DEFAULT_PARENT_CHUNKS_PATH,
    DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    DEFAULT_TABLE_DOCUMENTS_PATH,
    DEFAULT_TABLE_MARKDOWN_ROOT,
    DEFAULT_TABLES_ROOT,
)
from pipeline.chunking.core.io_jsonl import read_jsonl
from pipeline.tables.table_documents import write_table_documents
from pipeline.tables.table_markdown import convert_table_html_batch
from pipeline.tables.table_references import audit_table_references


TABLE_COMMANDS = {"audit-table-references", "build-table-markdown", "build-table-documents"}


def main(argv: list[str] | None = None) -> int:
    """Run the table processing CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run_table_command(args)
    except (FileNotFoundError, ImportError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    """Create the table processing CLI parser."""

    parser = argparse.ArgumentParser(description="SG-SST table processing utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_table_command_parsers(subparsers)
    return parser


def add_table_command_parsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register all table processing subcommands."""

    add_audit_table_references_parser(subparsers)
    add_build_table_markdown_parser(subparsers)
    add_build_table_documents_parser(subparsers)


def is_table_command(command: str | None) -> bool:
    """Return whether a parsed command belongs to table processing."""

    return command in TABLE_COMMANDS


def run_table_command(
    args: argparse.Namespace,
    *,
    parent_chunks_path: Path = DEFAULT_PARENT_CHUNKS_PATH,
    regex_constrained_semantic_chunks_path: Path = DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    tables_root: Path = DEFAULT_TABLES_ROOT,
    table_markdown_root: Path = DEFAULT_TABLE_MARKDOWN_ROOT,
    table_documents_path: Path = DEFAULT_TABLE_DOCUMENTS_PATH,
) -> int:
    """Run a parsed table processing subcommand."""

    if args.command == "audit-table-references":
        return run_audit_table_references(
            args,
            parent_chunks_path=parent_chunks_path,
            regex_constrained_semantic_chunks_path=regex_constrained_semantic_chunks_path,
            tables_root=tables_root,
        )
    if args.command == "build-table-markdown":
        return run_build_table_markdown(args, tables_root=tables_root, table_markdown_root=table_markdown_root)
    if args.command == "build-table-documents":
        return run_build_table_documents(
            args,
            table_markdown_root=table_markdown_root,
            table_documents_path=table_documents_path,
        )
    raise ValueError(f"Unsupported table command: {args.command}")


def add_audit_table_references_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the audit-table-references subcommand."""

    subparsers.add_parser(
        "audit-table-references",
        help="Audit chunk table references against extracted HTML tables.",
    )


def run_audit_table_references(
    _args: argparse.Namespace,
    *,
    parent_chunks_path: Path = DEFAULT_PARENT_CHUNKS_PATH,
    regex_constrained_semantic_chunks_path: Path = DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    tables_root: Path = DEFAULT_TABLES_ROOT,
) -> int:
    """Execute inverse table reference audit and print review findings."""

    chunks = []
    chunk_paths = [parent_chunks_path, regex_constrained_semantic_chunks_path]
    for chunk_path in chunk_paths:
        chunks.extend(read_jsonl(chunk_path))

    missing_files, orphaned_tables = audit_table_references(chunks, tables_root)

    print(f"Audited {len(chunks)} chunks from {len(chunk_paths)} JSONL file(s).")
    if missing_files:
        print("Missing referenced table files:", file=sys.stderr)
        for missing_file in missing_files:
            print(f"- {missing_file}", file=sys.stderr)
    if orphaned_tables:
        print("Warning: extracted table files not referenced by provided chunks:", file=sys.stderr)
        for orphaned_table in orphaned_tables:
            print(f"- {orphaned_table}", file=sys.stderr)
    if not missing_files and not orphaned_tables:
        print("No missing referenced table files or orphaned extracted tables found.")

    return 2 if missing_files else 0


def add_build_table_markdown_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-table-markdown subcommand."""

    subparsers.add_parser(
        "build-table-markdown",
        help="Convert extracted HTML tables to derived Markdown files.",
    )


def run_build_table_markdown(
    _args: argparse.Namespace,
    *,
    tables_root: Path = DEFAULT_TABLES_ROOT,
    table_markdown_root: Path = DEFAULT_TABLE_MARKDOWN_ROOT,
) -> int:
    """Convert extracted HTML tables and print a compact summary."""

    converted_paths = convert_table_html_batch(
        tables_root,
        table_markdown_root,
    )
    print(
        f"Converted {len(converted_paths)} table HTML file(s) to Markdown: "
        f"{table_markdown_root}"
    )
    return 0


def add_build_table_documents_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-table-documents subcommand."""

    subparsers.add_parser(
        "build-table-documents",
        help="Build vector-ready JSONL documents from derived Markdown tables.",
    )


def run_build_table_documents(
    _args: argparse.Namespace,
    *,
    table_markdown_root: Path = DEFAULT_TABLE_MARKDOWN_ROOT,
    table_documents_path: Path = DEFAULT_TABLE_DOCUMENTS_PATH,
) -> int:
    """Build vector-ready table documents and print a compact summary."""

    document_count = write_table_documents(
        table_markdown_root,
        table_documents_path,
    )
    print(f"Built {document_count} table document(s): {table_documents_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
