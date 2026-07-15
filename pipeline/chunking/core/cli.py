"""Command line interface for chunking operations."""

import argparse
import sys

from pipeline.chunking.core.config import (
    DEFAULT_CLEANED_MARKDOWN_DIR,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MIN_TOKENS,
    DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT,
    DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE,
    DEFAULT_SEMANTIC_CHUNKS_PATH,
    DEFAULT_PARENT_CHUNKS_PATH,
    DEFAULT_SLIDING_WINDOW_CHUNK_OVERLAP,
    DEFAULT_SLIDING_WINDOW_CHUNK_SIZE,
    DEFAULT_SLIDING_WINDOW_CHUNKS_PATH,
    DEFAULT_SOURCE_MANIFEST_PATH,
    resolve_project_path,
)
from pipeline.chunking.hierarchical_splitter.child_splitter import (
    write_regex_constrained_semantic_child_output,
    write_semantic_child_output,
    write_sliding_window_child_output,
)
from pipeline.chunking.hierarchical_splitter.parent_builder import write_parent_chunk_output


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
    except (FileNotFoundError, RuntimeError, ValueError) as error:
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
    return parser


# Parent chunk command


def add_build_parents_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-parents subcommand."""

    parser = subparsers.add_parser("build-parents", help="Build parent chunks from cleaned Markdown.")
    parser.add_argument("--input-dir", default=str(DEFAULT_CLEANED_MARKDOWN_DIR), help="Cleaned Markdown directory.")
    parser.add_argument("--output-path", default=str(DEFAULT_PARENT_CHUNKS_PATH), help="Parent JSONL output path.")
    parser.add_argument("--manifest-path", default=str(DEFAULT_SOURCE_MANIFEST_PATH), help="Optional source manifest JSON path.")


def run_build_parents(args: argparse.Namespace) -> int:
    """Execute parent chunk generation and print a compact summary."""

    result = write_parent_chunk_output(
        input_dir=resolve_project_path(args.input_dir),
        output_path=resolve_project_path(args.output_path),
        manifest_path=resolve_project_path(args.manifest_path),
    )
    print(f"Built {result.chunk_count} parent chunks from {result.source_count} sources: {result.output_path}")
    return 0


# Sliding-window command


def add_build_sliding_window_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-sliding-window subcommand."""

    parser = subparsers.add_parser("build-sliding-window", help="Build sliding-window child chunks from parents.")
    parser.add_argument("--input-path", default=str(DEFAULT_PARENT_CHUNKS_PATH), help="Parent JSONL input path.")
    parser.add_argument(
        "--output-path",
        default=str(DEFAULT_SLIDING_WINDOW_CHUNKS_PATH),
        help="Sliding-window child JSONL output path.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_SLIDING_WINDOW_CHUNK_SIZE,
        help="Maximum token window size for child chunks.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_SLIDING_WINDOW_CHUNK_OVERLAP,
        help="Token overlap between adjacent child chunks.",
    )


def run_build_sliding_window(args: argparse.Namespace) -> int:
    """Execute sliding-window child chunk generation and print a compact summary."""

    result = write_sliding_window_child_output(
        input_path=resolve_project_path(args.input_path),
        output_path=resolve_project_path(args.output_path),
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    print(f"Built {result.chunk_count} sliding-window child chunks from {result.parent_count} parents: {result.output_path}")
    return 0


# Semantic chunking command


def add_build_semantic_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the build-semantic subcommand."""

    parser = subparsers.add_parser("build-semantic", help="Build semantic child chunks from parents.")
    parser.add_argument("--input-path", default=str(DEFAULT_PARENT_CHUNKS_PATH), help="Parent JSONL input path.")
    parser.add_argument(
        "--output-path",
        default=str(DEFAULT_SEMANTIC_CHUNKS_PATH),
        help="Semantic child JSONL output path.",
    )
    parser.add_argument(
        "--breakpoint-threshold-type",
        default=DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE,
        help="SemanticChunker breakpoint threshold type.",
    )
    parser.add_argument(
        "--breakpoint-threshold-amount",
        type=float,
        default=DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT,
        help="SemanticChunker breakpoint threshold amount.",
    )


def run_build_semantic(args: argparse.Namespace) -> int:
    """Execute semantic child chunk generation and print a compact summary."""

    result = write_semantic_child_output(
        input_path=resolve_project_path(args.input_path),
        output_path=resolve_project_path(args.output_path),
        breakpoint_threshold_type=args.breakpoint_threshold_type,
        breakpoint_threshold_amount=args.breakpoint_threshold_amount,
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
        help="Regex-constrained semantic child JSONL output path.",
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
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=DEFAULT_MIN_TOKENS,
        help="Minimum target token size after semantic splitting.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Maximum target token size after semantic splitting.",
    )


def run_build_regex_constrained_semantic(args: argparse.Namespace) -> int:
    """Execute regex-constrained semantic child chunk generation and print a compact summary."""

    result = write_regex_constrained_semantic_child_output(
        input_path=resolve_project_path(args.input_path),
        output_path=resolve_project_path(args.output_path),
        breakpoint_threshold_type=args.breakpoint_threshold_type,
        breakpoint_threshold_amount=args.breakpoint_threshold_amount,
        min_tokens=args.min_tokens,
        max_tokens=args.max_tokens,
    )
    print(
        "Built "
        f"{result.chunk_count} regex-constrained semantic child chunks from {result.parent_count} parents: "
        f"{result.output_path}"
    )
    return 0
