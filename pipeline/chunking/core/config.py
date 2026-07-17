"""Central path configuration for the SG-SST chunking pipeline."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

DEFAULT_CLEANED_MARKDOWN_DIR = DATA_DIR / "processed"
DEFAULT_INTERIM_MARKDOWN_DIR = DATA_DIR / "interim"
DEFAULT_TABLES_ROOT = DEFAULT_INTERIM_MARKDOWN_DIR / "tables"
DEFAULT_TABLE_MARKDOWN_ROOT = DATA_DIR / "processed" / "tables_markdown"
DEFAULT_TABLE_DOCUMENTS_PATH = DATA_DIR / "processed" / "table_documents.jsonl"
DEFAULT_CHUNKS_DIR = DATA_DIR / "processed" / "chunks"
DEFAULT_PARENT_CHUNKS_PATH = DEFAULT_CHUNKS_DIR / "parents.jsonl"
DEFAULT_SLIDING_WINDOW_CHUNKS_PATH = DEFAULT_CHUNKS_DIR / "sliding_window" / "chunks.jsonl"
DEFAULT_SEMANTIC_CHUNKS_PATH = DEFAULT_CHUNKS_DIR / "semantic_chunking" / "chunks.jsonl"
DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH = DEFAULT_CHUNKS_DIR / "regex_constrained_semantic" / "chunks.jsonl"
DEFAULT_COMPARISON_DIR = DEFAULT_CHUNKS_DIR / "comparison"
DEFAULT_SOURCE_MANIFEST_PATH = DATA_DIR / "processed" / "metadata" / "source_manifest.json"

DEFAULT_MIN_TOKENS = 80
DEFAULT_MAX_TOKENS = 350
DEFAULT_SLIDING_WINDOW_CHUNK_SIZE = 350
DEFAULT_SLIDING_WINDOW_CHUNK_OVERLAP = 70

# Define qué modelo convierte el texto en vectores semánticos.
DEFAULT_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
# Define qué tipo de umbral se utiliza para determinar los puntos de corte semánticos.
DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE = "gradient"
# Define qué cantidad de texto se utiliza para determinar los puntos de corte semánticos.
DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT = 95

GENERATED_OUTPUT_DIRS = (DEFAULT_CHUNKS_DIR, DEFAULT_TABLE_MARKDOWN_ROOT)

STRATEGY_OUTPUTS = {
    "sliding_window": DEFAULT_SLIDING_WINDOW_CHUNKS_PATH,
    "semantic_chunking": DEFAULT_SEMANTIC_CHUNKS_PATH,
    "regex_constrained_semantic": DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH,
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
