"""Compare child chunking strategy outputs with deterministic metrics."""

import argparse
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.chunking.core.config import (
    DEFAULT_COMPARISON_DIR,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MIN_TOKENS,
    STRATEGY_OUTPUTS,
)
from pipeline.chunking.core.io_jsonl import read_child_chunks
from pipeline.chunking.hierarchical_splitter.models import ChildChunk


JsonDict = dict[str, Any]


def main() -> None:
    """Read strategy outputs and write comparison artifacts."""

    args = parse_args()
    output_dir = Path(args.output_dir)
    metrics = compare_strategy_outputs(
        {strategy: Path(path) for strategy, path in args.strategy_output},
        min_tokens=args.min_tokens,
        max_tokens=args.max_tokens,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "comparison_report.md").write_text(render_report(metrics), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Return parsed comparison arguments."""

    parser = argparse.ArgumentParser(description="Compare SG-SST chunking strategy outputs.")
    parser.add_argument("--output-dir", default=str(DEFAULT_COMPARISON_DIR), help="Directory for comparison artifacts.")
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=DEFAULT_MIN_TOKENS,
        help="Threshold for chunks that are too small.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Threshold for chunks that are too large.",
    )
    parser.add_argument(
        "--strategy-output",
        action="append",
        nargs=2,
        metavar=("STRATEGY", "PATH"),
        default=[(strategy, str(path)) for strategy, path in STRATEGY_OUTPUTS.items()],
        help="Strategy name and JSONL path. Can be passed multiple times.",
    )
    args = parser.parse_args()
    validate_thresholds(args.min_tokens, args.max_tokens, parser)
    return args


def validate_thresholds(min_tokens: int, max_tokens: int, parser: argparse.ArgumentParser) -> None:
    """Reject invalid token thresholds before comparison metrics are computed."""

    if min_tokens < 0:
        parser.error("--min-tokens must be greater than or equal to 0.")
    if max_tokens <= 0:
        parser.error("--max-tokens must be greater than 0.")
    if min_tokens >= max_tokens:
        parser.error("--min-tokens must be lower than --max-tokens.")


def compare_strategy_outputs(paths: dict[str, Path], min_tokens: int, max_tokens: int) -> JsonDict:
    """Compute metrics for every available strategy output."""

    metrics: JsonDict = {"strategies": {}, "summary": {}}
    for strategy, path in paths.items():
        chunks = read_child_chunks(path) if path.exists() else []
        metrics["strategies"][strategy] = strategy_metrics(chunks, min_tokens, max_tokens, path)
    metrics["summary"] = summarize(metrics["strategies"])
    return metrics


def strategy_metrics(chunks: list[ChildChunk], min_tokens: int, max_tokens: int, path: Path) -> JsonDict:
    """Compute deterministic quality and coverage metrics for one strategy."""

    token_counts = [chunk.token_count for chunk in chunks]
    parent_ids = {chunk.parent_id for chunk in chunks}
    source_count = sum(1 for chunk in chunks if _has_source_metadata(chunk))
    article_count = sum(1 for chunk in chunks if _has_article_metadata(chunk))
    return {
        "path": str(path),
        "total_chunks": len(chunks),
        "avg_token_count": round(mean(token_counts), 2) if token_counts else 0,
        "min_token_count": min(token_counts) if token_counts else 0,
        "max_token_count": max(token_counts) if token_counts else 0,
        "chunks_too_small": sum(1 for count in token_counts if count < min_tokens),
        "chunks_too_large": sum(1 for count in token_counts if count > max_tokens),
        "overlap_count": sum(1 for chunk in chunks if chunk.metadata.get("chunk", {}).get("overlap_tokens", 0) > 0),
        "unresolved_offset_count": sum(1 for chunk in chunks if chunk.start_char is None or chunk.end_char is None),
        "percentage_with_article_metadata": _percentage(article_count, len(chunks)),
        "percentage_with_source_metadata": _percentage(source_count, len(chunks)),
        "orphan_child_chunks": sum(1 for chunk in chunks if not chunk.parent_id),
        "unique_parent_count": len(parent_ids),
    }


def summarize(strategy_results: JsonDict) -> JsonDict:
    """Build strategy-level summary from metrics."""

    available = {name: data for name, data in strategy_results.items() if data["total_chunks"] > 0}
    if not available:
        return {"available_strategies": 0, "note": "No strategy outputs were found."}
    return {
        "available_strategies": len(available),
        "most_chunks": max(available, key=lambda name: available[name]["total_chunks"]),
        "fewest_oversized_chunks": min(available, key=lambda name: available[name]["chunks_too_large"]),
        "fewest_unresolved_offsets": min(available, key=lambda name: available[name]["unresolved_offset_count"]),
        "best_article_metadata_coverage": max(
            available,
            key=lambda name: available[name]["percentage_with_article_metadata"],
        ),
    }


def render_report(metrics: JsonDict) -> str:
    """Render a Markdown comparison report."""

    lines = [
        "# Chunking Strategy Comparison",
        "",
        "| Strategy | Chunks | Avg tokens | Too small | Too large | Unresolved offsets | Article metadata | Source metadata |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy, data in metrics["strategies"].items():
        lines.append(
            "| {strategy} | {total_chunks} | {avg_token_count} | {chunks_too_small} | "
            "{chunks_too_large} | {unresolved_offset_count} | {article}% | {source}% |".format(
                strategy=strategy,
                total_chunks=data["total_chunks"],
                avg_token_count=data["avg_token_count"],
                chunks_too_small=data["chunks_too_small"],
                chunks_too_large=data["chunks_too_large"],
                unresolved_offset_count=data["unresolved_offset_count"],
                article=data["percentage_with_article_metadata"],
                source=data["percentage_with_source_metadata"],
            )
        )
    lines.extend(["", "## Summary", "", json.dumps(metrics["summary"], ensure_ascii=False, indent=2)])
    return "\n".join(lines) + "\n"


def _has_article_metadata(chunk: ChildChunk) -> bool:
    hierarchy = chunk.metadata.get("inherited", {}).get("hierarchy", {})
    return bool(hierarchy.get("article"))


def _has_source_metadata(chunk: ChildChunk) -> bool:
    inherited = chunk.metadata.get("inherited", {})
    return bool(inherited.get("source_name") or inherited.get("source_stem"))


def _percentage(count: int, total: int) -> float:
    return round((count / total * 100), 2) if total else 0.0


if __name__ == "__main__":
    main()
