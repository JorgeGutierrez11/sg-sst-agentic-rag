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
)
from pipeline.chunking.hierarchical_splitter.child_splitter import (
    write_regex_constrained_semantic_child_output,
    write_semantic_child_output,
    write_sliding_window_child_output,
)
from pipeline.chunking.hierarchical_splitter.parent_builder import write_parent_chunk_output
from pipeline.tables.main import add_table_command_parsers, is_table_command, run_table_command


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
        if is_table_command(args.command):
            return run_table_command(
                args,
                parent_chunks_path=DEFAULT_PARENT_CHUNKS_PATH,
                regex_constrained_semantic_chunks_path=DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
                tables_root=DEFAULT_TABLES_ROOT,
                table_markdown_root=DEFAULT_TABLE_MARKDOWN_ROOT,
                table_documents_path=DEFAULT_TABLE_DOCUMENTS_PATH,
            )
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
    add_table_command_parsers(subparsers)

    return parser


# Parent chunk command

def add_build_parents_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-parents subcommand."""

    subparsers.add_parser("build-parents", help="Build parent chunks from cleaned Markdown.")


def run_build_parents(_args: argparse.Namespace) -> int:
    """Execute parent chunk generation and print a compact summary."""

    result = write_parent_chunk_output(
        input_dir=DEFAULT_CLEANED_MARKDOWN_DIR,
        output_path=DEFAULT_PARENT_CHUNKS_PATH,
        manifest_path=DEFAULT_SOURCE_MANIFEST_PATH,
        tables_root=DEFAULT_TABLES_ROOT,
    )
    print(f"Built {result.chunk_count} parent chunks from {result.source_count} sources: {result.output_path}")
    return 0


# Sliding-window command

def add_build_sliding_window_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-sliding-window subcommand."""

    subparsers.add_parser("build-sliding-window", help="Build sliding-window child chunks from parents.")


def run_build_sliding_window(_args: argparse.Namespace) -> int:
    """Execute sliding-window child chunk generation and print a compact summary."""

    result = write_sliding_window_child_output(
        input_path=DEFAULT_PARENT_CHUNKS_PATH,
        output_path=DEFAULT_SLIDING_WINDOW_CHUNKS_PATH,
        chunk_size=DEFAULT_SLIDING_WINDOW_CHUNK_SIZE,
        chunk_overlap=DEFAULT_SLIDING_WINDOW_CHUNK_OVERLAP,
        tables_root=DEFAULT_TABLES_ROOT,
    )
    print(f"Built {result.chunk_count} sliding-window child chunks from {result.parent_count} parents: {result.output_path}")
    return 0


# Semantic chunking command

def add_build_semantic_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-semantic subcommand."""

    subparsers.add_parser("build-semantic", help="Build semantic child chunks from parents.")


def run_build_semantic(_args: argparse.Namespace) -> int:
    """Execute semantic child chunk generation and print a compact summary."""

    result = write_semantic_child_output(
        input_path=DEFAULT_PARENT_CHUNKS_PATH,
        output_path=DEFAULT_SEMANTIC_CHUNKS_PATH,
        breakpoint_threshold_type=DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE,
        breakpoint_threshold_amount=DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT,
        tables_root=DEFAULT_TABLES_ROOT,
    )
    print(f"Built {result.chunk_count} semantic child chunks from {result.parent_count} parents: {result.output_path}")
    return 0


# Regex-constrained semantic command

def add_build_regex_constrained_semantic_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the build-regex-constrained-semantic subcommand."""

    subparsers.add_parser(
        "build-regex-constrained-semantic",
        help="Build source-preserving semantic child chunks from parents.",
    )


def run_build_regex_constrained_semantic(_args: argparse.Namespace) -> int:
    """Execute regex-constrained semantic child chunk generation and print a compact summary."""

    result = write_regex_constrained_semantic_child_output(
        input_path=DEFAULT_PARENT_CHUNKS_PATH,
        output_path=DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
        breakpoint_threshold_type=DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE,
        breakpoint_threshold_amount=DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT,
        min_tokens=DEFAULT_MIN_TOKENS,
        max_tokens=DEFAULT_MAX_TOKENS,
        tables_root=DEFAULT_TABLES_ROOT,
    )
    print(
        "Built "
        f"{result.chunk_count} regex-constrained semantic child chunks from {result.parent_count} parents: "
        f"{result.output_path}"
    )
    return 0
