"""CLI entrypoint for SG-SST vectorization commands."""

import argparse
import sys

from pipeline.chunking.core.config import (
    DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
    DEFAULT_TABLE_DOCUMENTS_PATH,
    resolve_project_path,
)
from pipeline.vectorization.chroma_store import DEFAULT_COLLECTION_NAME
from pipeline.vectorization.ingest import DEFAULT_CHROMA_PATH, ingest_base_rag_documents


def main(argv: list[str] | None = None) -> int:
    """Run the vectorization CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "ingest":
            return run_ingest(args)
    except (ImportError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    raise ValueError(f"Unsupported command: {args.command}")


def build_parser() -> argparse.ArgumentParser:
    """Create the vectorization CLI parser."""

    parser = argparse.ArgumentParser(description="SG-SST vectorization utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest_parser = subparsers.add_parser("ingest", help="Index base RAG child chunks and table documents in ChromaDB.")
    ingest_parser.add_argument("--chunks-path", default=str(DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH))
    ingest_parser.add_argument("--tables-path", default=str(DEFAULT_TABLE_DOCUMENTS_PATH))
    ingest_parser.add_argument("--persist-path", default=str(DEFAULT_CHROMA_PATH))
    ingest_parser.add_argument("--collection", default=DEFAULT_COLLECTION_NAME)
    return parser


def run_ingest(args: argparse.Namespace) -> int:
    """Run base RAG ingestion and print indexed counts by document type."""

    result = ingest_base_rag_documents(
        chunks_path=resolve_project_path(args.chunks_path),
        tables_path=resolve_project_path(args.tables_path),
        persist_path=resolve_project_path(args.persist_path),
        collection_name=args.collection,
    )
    print(f"Indexed {result.total_count} document(s) into {result.collection_name}: {result.persist_path}")
    print(f"- child_chunk: {result.child_chunk_count}")
    print(f"- table: {result.table_count}")
    print(f"Skipped {result.skipped_count} invalid/empty source record(s).")
    print(f"- child_chunk skipped: {result.skipped_child_chunk_count}")
    print(f"- table skipped: {result.skipped_table_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
