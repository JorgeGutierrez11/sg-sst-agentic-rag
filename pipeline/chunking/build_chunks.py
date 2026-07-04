"""CLI for building parent and child chunks from processed SG-SST corpus files."""

import argparse
import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.chunking.config import (
    DEFAULT_INPUT_DIR,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MIN_TOKENS,
    DEFAULT_OVERLAP_TOKENS,
    DEFAULT_PARENT_CHUNKS_PATH,
    REGEX_CONSTRAINED_SEMANTIC_STRATEGY,
    SEMANTIC_CHUNKING_STRATEGY,
    SLIDING_WINDOW_STRATEGY,
    STRATEGY_OUTPUTS,
)
from pipeline.chunking.parent_chunks import build_parent_chunks
from pipeline.chunking.serialization import write_child_chunks, write_parent_chunks
from pipeline.chunking.strategies import (
    RegexConstrainedSemanticStrategy,
    SemanticChunkingStrategy,
    SlidingWindowStrategy,
)
from pipeline.chunking.strategies.base import ChunkingStrategy


logger = logging.getLogger(__name__)


def main() -> None:
    """Parse CLI arguments and build child chunks."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else STRATEGY_OUTPUTS[args.strategy]
    manifest_path = Path(args.manifest) if args.manifest else DEFAULT_MANIFEST_PATH
    manifest = manifest_path if manifest_path.exists() else None

    parents = build_parent_chunks(input_path, manifest)
    strategy = create_strategy(args.strategy, args.max_tokens, args.overlap_tokens, args.min_tokens)
    children = [child for parent in parents for child in strategy.chunk_parent(parent)]

    write_parent_chunks(DEFAULT_PARENT_CHUNKS_PATH, parents)
    write_child_chunks(output_path, children)
    logger.info("Wrote %s parent chunks and %s child chunks to %s", len(parents), len(children), output_path)


def parse_args() -> argparse.Namespace:
    """Return parsed command-line arguments."""

    parser = argparse.ArgumentParser(description="Build SG-SST parent-child chunks.")
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_DIR),
        help="Input file or directory with .md, .txt, or .jsonl files.",
    )
    parser.add_argument(
        "--strategy",
        choices=sorted(STRATEGY_OUTPUTS.keys()),
        required=True,
        help="Child chunking strategy to run.",
    )
    parser.add_argument(
        "--output",
        help="Output JSONL path. Defaults to data/processed/chunks/<strategy>/chunks.jsonl.",
    )
    parser.add_argument("--manifest", help="Optional JSON source manifest keyed by document id or source stem.")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Maximum approximate tokens per chunk.",
    )
    parser.add_argument(
        "--overlap-tokens",
        type=int,
        default=DEFAULT_OVERLAP_TOKENS,
        help="Approximate overlap tokens.",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=DEFAULT_MIN_TOKENS,
        help="Minimum approximate tokens for metrics only.",
    )
    args = parser.parse_args()
    validate_args(args, parser)
    return args


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Reject invalid numeric chunking settings before strategy execution."""

    if args.max_tokens <= 0:
        parser.error("--max-tokens must be greater than 0.")
    if args.overlap_tokens < 0:
        parser.error("--overlap-tokens must be 0 or greater.")
    if args.overlap_tokens >= args.max_tokens:
        parser.error("--overlap-tokens must be less than --max-tokens.")


def create_strategy(name: str, max_tokens: int, overlap_tokens: int, min_tokens: int) -> ChunkingStrategy:
    """Instantiate a chunking strategy by name."""

    if name == SLIDING_WINDOW_STRATEGY:
        return SlidingWindowStrategy(max_tokens=max_tokens, overlap_tokens=overlap_tokens, min_tokens=min_tokens)
    if name == SEMANTIC_CHUNKING_STRATEGY:
        return SemanticChunkingStrategy(max_tokens=max_tokens, overlap_tokens=0, min_tokens=min_tokens)
    if name == REGEX_CONSTRAINED_SEMANTIC_STRATEGY:
        return RegexConstrainedSemanticStrategy(
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
            min_tokens=min_tokens,
        )
    raise ValueError(f"Unsupported strategy: {name}")


if __name__ == "__main__":
    main()
