"""Central path configuration for the SG-SST chunking pipeline."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

DEFAULT_CLEANED_MARKDOWN_DIR = DATA_DIR / "processed"
DEFAULT_INTERIM_MARKDOWN_DIR = DATA_DIR / "interim"
DEFAULT_CHUNKS_DIR = DATA_DIR / "processed" / "chunks"
DEFAULT_PARENT_CHUNKS_PATH = DEFAULT_CHUNKS_DIR / "parents.jsonl"
DEFAULT_COMPARISON_DIR = DEFAULT_CHUNKS_DIR / "comparison"
DEFAULT_SOURCE_MANIFEST_PATH = DATA_DIR / "processed" / "metadata" / "source_manifest.json"

DEFAULT_MIN_TOKENS = 80
DEFAULT_MAX_TOKENS = 350

GENERATED_OUTPUT_DIRS = (DEFAULT_CHUNKS_DIR,)

STRATEGY_OUTPUTS = {
    "sliding_window": DEFAULT_CHUNKS_DIR / "sliding_window" / "chunks.jsonl",
    "semantic_chunking": DEFAULT_CHUNKS_DIR / "semantic_chunking" / "chunks.jsonl",
    "regex_constrained_semantic": DEFAULT_CHUNKS_DIR / "regex_constrained_semantic" / "chunks.jsonl",
}


def resolve_project_path(path: str | Path) -> Path:
    """Return an absolute path, resolving relative paths from the project root."""

    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def is_generated_output_path(path: Path) -> bool:
    """Return True when a path is inside generated chunking outputs."""

    resolved_path = path.resolve()
    return any(resolved_path.is_relative_to(output_dir.resolve()) for output_dir in GENERATED_OUTPUT_DIRS)
