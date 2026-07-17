"""Command line interface for chunking operations."""

import argparse
import sys

from pipeline.chunking.core.config import (
    DEFAULT_CLEANED_MARKDOWN_DIR,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MIN_TOKENS,
    DEFAULT_PARENT_CHUNKS_PATH,
    DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT,
    DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE,
    DEFAULT_SEMANTIC_CHUNKS_PATH,
    DEFAULT_SLIDING_WINDOW_CHUNK_OVERLAP,
    DEFAULT_SLIDING_WINDOW_CHUNK_SIZE,
    DEFAULT_SLIDING_WINDOW_CHUNKS_PATH,
    DEFAULT_SOURCE_MANIFEST_PATH,
    DEFAULT_TABLE_DOCUMENTS_PATH,
    DEFAULT_TABLE_MARKDOWN_ROOT,
    DEFAULT_TABLES_ROOT,
    resolve_project_path,
)
from pipeline.chunking.core.io_jsonl import read_jsonl
from pipeline.chunking.hierarchical_splitter.child_splitter import (
    write_regex_constrained_semantic_child_output,
    write_semantic_child_output,
    write_sliding_window_child_output,
)
from pipeline.chunking.hierarchical_splitter.parent_builder import write_parent_chunk_output
from pipeline.tables.table_documents import write_table_documents
from pipeline.tables.table_markdown import convert_table_html_batch
from pipeline.tables.table_references import audit_table_references


# Entrypoint and parser

def main(argv: list[str] | None = None) -> int:
    """Run the chunking CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build-parents":
            return run_build_parents(args)
        if args.command == "build-sliding-window":
            return run_build_sliding_window(args)
        if args.command == "build-semantic":
            return run_build_semantic(args)
        if args.command == "build-regex-constrained-semantic":
            return run_build_regex_constrained_semantic(args)
        if args.command == "audit-table-references":
            return run_audit_table_references(args)
        if args.command == "build-table-markdown":
            return run_build_table_markdown(args)
        if args.command == "build-table-documents":
            return run_build_table_documents(args)
    except (FileNotFoundError, ImportError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    raise ValueError(f"Unsupported command: {args.command}")


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""

    parser = argparse.ArgumentParser(description="SG-SST chunking utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_build_parents_parser(subparsers)
    add_build_sliding_window_parser(subparsers)
    add_build_semantic_parser(subparsers)
    add_build_regex_constrained_semantic_parser(subparsers)
    add_audit_table_references_parser(subparsers)
    add_build_table_markdown_parser(subparsers)
    add_build_table_documents_parser(subparsers)

    return parser


# Parent chunk command

def add_build_parents_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-parents subcommand."""

    parser = subparsers.add_parser("build-parents", help="Build parent chunks from cleaned Markdown.")
    parser.add_argument("--input-dir", default=str(DEFAULT_CLEANED_MARKDOWN_DIR), help="Cleaned Markdown directory.")
    parser.add_argument("--output-path", default=str(DEFAULT_PARENT_CHUNKS_PATH), help="Parent JSONL output path.")
    parser.add_argument("--manifest-path", default=str(DEFAULT_SOURCE_MANIFEST_PATH), help="Optional source manifest JSON path.")
    parser.add_argument("--tables-root", default=str(DEFAULT_TABLES_ROOT), help="Extracted HTML tables root directory.")


def run_build_parents(args: argparse.Namespace) -> int:
    """Execute parent chunk generation and print a compact summary."""

    result = write_parent_chunk_output(
        input_dir=resolve_project_path(args.input_dir),
        output_path=resolve_project_path(args.output_path),
        manifest_path=resolve_project_path(args.manifest_path),
        tables_root=resolve_project_path(args.tables_root),
    )
    print(f"Built {result.chunk_count} parent chunks from {result.source_count} sources: {result.output_path}")
    return 0


# Sliding-window command

def add_build_sliding_window_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-sliding-window subcommand."""

    parser = subparsers.add_parser("build-sliding-window", help="Build sliding-window child chunks from parents.")
    parser.add_argument("--input-path", default=str(DEFAULT_PARENT_CHUNKS_PATH), help="Parent JSONL input path.")
    parser.add_argument("--output-path", default=str(DEFAULT_SLIDING_WINDOW_CHUNKS_PATH), help="Child JSONL output path.")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_SLIDING_WINDOW_CHUNK_SIZE, help="Target chunk size.")
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_SLIDING_WINDOW_CHUNK_OVERLAP, help="Chunk overlap.")
    parser.add_argument("--tables-root", default=str(DEFAULT_TABLES_ROOT), help="Extracted HTML tables root directory.")


def run_build_sliding_window(args: argparse.Namespace) -> int:
    """Execute sliding-window child chunk generation and print a compact summary."""

    result = write_sliding_window_child_output(
        input_path=resolve_project_path(args.input_path),
        output_path=resolve_project_path(args.output_path),
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        tables_root=resolve_project_path(args.tables_root),
    )
    print(f"Built {result.chunk_count} sliding-window child chunks from {result.parent_count} parents: {result.output_path}")
    return 0


# Semantic chunking command

def add_build_semantic_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-semantic subcommand."""

    parser = subparsers.add_parser("build-semantic", help="Build semantic child chunks from parents.")
    parser.add_argument("--input-path", default=str(DEFAULT_PARENT_CHUNKS_PATH), help="Parent JSONL input path.")
    parser.add_argument("--output-path", default=str(DEFAULT_SEMANTIC_CHUNKS_PATH), help="Child JSONL output path.")
    parser.add_argument("--tables-root", default=str(DEFAULT_TABLES_ROOT), help="Extracted HTML tables root directory.")
    parser.add_argument(
        "--breakpoint-threshold-type",
        default=DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE,
        help="Semantic breakpoint threshold type.",
    )
    parser.add_argument(
        "--breakpoint-threshold-amount",
        type=float,
        default=DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT,
        help="Semantic breakpoint threshold amount.",
    )


def run_build_semantic(args: argparse.Namespace) -> int:
    """Execute semantic child chunk generation and print a compact summary."""

    result = write_semantic_child_output(
        input_path=resolve_project_path(args.input_path),
        output_path=resolve_project_path(args.output_path),
        breakpoint_threshold_type=args.breakpoint_threshold_type,
        breakpoint_threshold_amount=args.breakpoint_threshold_amount,
        tables_root=resolve_project_path(args.tables_root),
    )
    print(f"Built {result.chunk_count} semantic child chunks from {result.parent_count} parents: {result.output_path}")
    return 0


# Regex-constrained semantic command

def add_build_regex_constrained_semantic_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the build-regex-constrained-semantic subcommand."""

    parser = subparsers.add_parser(
        "build-regex-constrained-semantic",
        help="Build source-preserving semantic child chunks from parents.",
    )
    parser.add_argument("--input-path", default=str(DEFAULT_PARENT_CHUNKS_PATH), help="Parent JSONL input path.")
    parser.add_argument(
        "--output-path",
        default=str(DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH),
        help="Child JSONL output path.",
    )
    parser.add_argument(
        "--breakpoint-threshold-type",
        default=DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE,
        help="Semantic breakpoint threshold type.",
    )
    parser.add_argument(
        "--breakpoint-threshold-amount",
        type=float,
        default=DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT,
        help="Semantic breakpoint threshold amount.",
    )
    parser.add_argument("--min-tokens", type=int, default=DEFAULT_MIN_TOKENS, help="Minimum child chunk tokens.")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Maximum child chunk tokens.")
    parser.add_argument("--tables-root", default=str(DEFAULT_TABLES_ROOT), help="Extracted HTML tables root directory.")


def run_build_regex_constrained_semantic(args: argparse.Namespace) -> int:
    """Execute regex-constrained semantic child chunk generation and print a compact summary."""

    result = write_regex_constrained_semantic_child_output(
        input_path=resolve_project_path(args.input_path),
        output_path=resolve_project_path(args.output_path),
        breakpoint_threshold_type=args.breakpoint_threshold_type,
        breakpoint_threshold_amount=args.breakpoint_threshold_amount,
        min_tokens=args.min_tokens,
        max_tokens=args.max_tokens,
        tables_root=resolve_project_path(args.tables_root),
    )
    print(
        "Built "
        f"{result.chunk_count} regex-constrained semantic child chunks from {result.parent_count} parents: "
        f"{result.output_path}"
    )
    return 0


# Table reference audit command

def add_audit_table_references_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the audit-table-references subcommand."""

    parser = subparsers.add_parser(
        "audit-table-references",
        help="Audit chunk table references against extracted HTML tables.",
    )
    parser.add_argument(
        "--chunks-path",
        action="append",
        required=True,
        help="Chunk JSONL input path. Repeat to audit parents and one or more child outputs together.",
    )
    parser.add_argument("--tables-root", default=str(DEFAULT_TABLES_ROOT), help="Extracted HTML tables root directory.")


def run_audit_table_references(args: argparse.Namespace) -> int:
    """Execute inverse table reference audit and print review findings."""

    chunks = []
    chunk_paths = [resolve_project_path(path) for path in args.chunks_path]
    for chunk_path in chunk_paths:
        chunks.extend(read_jsonl(chunk_path))

    missing_files, orphaned_tables = audit_table_references(chunks, resolve_project_path(args.tables_root))

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


# Table Markdown command

def add_build_table_markdown_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-table-markdown subcommand."""

    parser = subparsers.add_parser(
        "build-table-markdown",
        help="Convert extracted HTML tables to derived Markdown files.",
    )
    parser.add_argument("--tables-root", default=str(DEFAULT_TABLES_ROOT), help="Extracted HTML tables root directory.")
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_TABLE_MARKDOWN_ROOT),
        help="Derived Markdown table output directory.",
    )


def run_build_table_markdown(args: argparse.Namespace) -> int:
    """Convert extracted HTML tables and print a compact summary."""

    converted_paths = convert_table_html_batch(
        resolve_project_path(args.tables_root),
        resolve_project_path(args.output_root),
    )
    print(
        f"Converted {len(converted_paths)} table HTML file(s) to Markdown: "
        f"{resolve_project_path(args.output_root)}"
    )
    return 0


# Table document command

def add_build_table_documents_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-table-documents subcommand."""

    parser = subparsers.add_parser(
        "build-table-documents",
        help="Build vector-ready JSONL documents from derived Markdown tables.",
    )
    parser.add_argument(
        "--markdown-root",
        default=str(DEFAULT_TABLE_MARKDOWN_ROOT),
        help="Derived Markdown table input directory.",
    )
    parser.add_argument(
        "--output-path",
        default=str(DEFAULT_TABLE_DOCUMENTS_PATH),
        help="Vector-ready table document JSONL output path.",
    )


def run_build_table_documents(args: argparse.Namespace) -> int:
    """Build vector-ready table documents and print a compact summary."""

    document_count = write_table_documents(
        resolve_project_path(args.markdown_root),
        resolve_project_path(args.output_path),
    )
    print(f"Built {document_count} table document(s): {resolve_project_path(args.output_path)}")
    return 0
