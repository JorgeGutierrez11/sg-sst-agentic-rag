"""Command line interface for Phase 1 chunking operations."""

import argparse
import sys

from pipeline.chunking.core.config import (
    DEFAULT_CLEANED_MARKDOWN_DIR,
    DEFAULT_PARENT_CHUNKS_PATH,
    DEFAULT_SOURCE_MANIFEST_PATH,
    resolve_project_path,
)
from pipeline.chunking.hierarchical_splitter.parent_builder import write_parent_chunk_output


def main(argv: list[str] | None = None) -> int:
    """Run the chunking CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build-parents":
            return run_build_parents(args)
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    raise ValueError(f"Unsupported command: {args.command}")


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""

    parser = argparse.ArgumentParser(description="SG-SST Phase 1 chunking utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_build_parents_parser(subparsers)
    return parser


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
