"""Commands for the offline corpus ingestion pipeline."""

import argparse
import json
import sys

from pipeline.artifact_validation import ArtifactValidationError
from pipeline.chunking.config import PROJECT_ROOT
from pipeline.offline_orchestration import (
    STAGE_ORDER,
    OfflineBuildError,
    StageEvent,
    StageName,
    build_offline_corpus,
    default_stage_operations,
    validate_published_corpus,
)

STAGE_LABELS = {
    StageName.DOCX_INGESTION: "DOCX ingestion",
    StageName.MARKDOWN_CLEANUP: "Markdown cleanup",
    StageName.PARENT_CHUNKING: "Parent chunking",
    StageName.REGEX_CHILD_CHUNKING: "Regex child chunking",
    StageName.TABLE_REFERENCE_AUDIT: "Table reference audit",
    StageName.TABLE_MARKDOWN_CONVERSION: "Table Markdown conversion",
    StageName.TABLE_DOCUMENT_BUILD: "Table document build",
    StageName.CHROMA_INDEXING: "Chroma indexing",
    StageName.BM25_INDEXING: "BM25 indexing",
    StageName.CORPUS_VALIDATION: "Corpus validation",
    StageName.PREFLIGHT: "Preflight",
    StageName.PUBLICATION: "Publication",
}


def main(argv: list[str] | None = None) -> int:
    """Run an offline corpus build or read-only validation command."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            callback = json_progress if args.json else human_progress
            build_offline_corpus(
                project_root=PROJECT_ROOT,
                operations=default_stage_operations(),
                batch_size=args.batch_size,
                keep_workdir=args.keep_workdir,
                progress_callback=callback,
            )
            if not args.json:
                print("Offline corpus build published successfully", file=sys.stderr)
            return 0
        result = validate_published_corpus(PROJECT_ROOT)
        print(
            "Offline corpus validation completed — "
            f"{result.parent_count:,} parents, {result.source_record_count:,} records; Chroma and BM25 agree",
            file=sys.stderr,
        )
        return 0
    except OfflineBuildError as error:
        print(f"Cause: {error.cause}", file=sys.stderr)
        print(publication_state(error), file=sys.stderr)
        return 2
    except ArtifactValidationError as error:
        print("Offline corpus validation failed", file=sys.stderr)
        print(f"Cause: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(f"Offline corpus command failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Create the explicit offline corpus command parser."""

    parser = argparse.ArgumentParser(
        prog="python -m pipeline.offline_corpus",
        description="Build or validate the offline corpus ingestion pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build, validate, and publish the offline corpus.")
    build.add_argument("--batch-size", type=positive_int, default=8, help="Positive Chroma embedding batch size.")
    build.add_argument("--json", action="store_true", help="Write lifecycle events as JSON lines to stdout.")
    build.add_argument("--keep-workdir", action="store_true", help="Keep the isolated staging workspace.")
    subparsers.add_parser("validate", help="Read-only validation of the published offline corpus.")
    return parser


def positive_int(value: str) -> int:
    """Parse a strictly positive command-line integer."""

    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("--batch-size must be greater than 0")
    return parsed


def publication_state(error: OfflineBuildError) -> str:
    """Describe the published corpus state after a failed build."""

    if error.backup_path is not None:
        return f"The previous published corpus could not be restored; backup retained at {error.backup_path}"
    if error.stage is StageName.PUBLICATION:
        return "The previous published corpus was restored."
    return "The published corpus was not modified."


def human_progress(event: StageEvent) -> None:
    """Write concise lifecycle progress to standard error."""

    stage = StageName(str(event.stage))
    # El detalle de un fallo se imprime una sola vez como "Cause:"
    suffix = f" — {event.detail}" if event.detail and event.status != "failed" else ""
    prefix = f"[{event.number}/{len(STAGE_ORDER)}] " if event.number is not None else ""
    print(f"{prefix}{STAGE_LABELS[stage]} {event.status}{suffix}", file=sys.stderr)


def json_progress(event: StageEvent) -> None:
    """Write one JSON lifecycle event to standard output."""

    print(
        json.dumps(
            {
                "stage": str(event.stage),
                "number": event.number,
                "status": event.status,
                "detail": event.detail,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
