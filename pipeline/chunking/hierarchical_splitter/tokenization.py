"""Model-aligned tokenization helpers for hierarchical chunking."""

from functools import lru_cache

from pipeline.chunking.core.config import DEFAULT_EMBEDDING_MODEL

try:
    # pyrefly: ignore [missing-import]
    from transformers import AutoTokenizer
except ImportError:  # pragma: no cover - exercised when tokenizer is used without dependency
    AutoTokenizer = None


@lru_cache(maxsize=4)
def get_tokenizer(model_name: str = DEFAULT_EMBEDDING_MODEL):
    """Load and cache the tokenizer for the configured embedding model."""

    if AutoTokenizer is None:
        raise RuntimeError(
            "Could not initialize tokenizer: install 'transformers' to use Hugging Face AutoTokenizer."
        )
    try:
        return AutoTokenizer.from_pretrained(model_name, use_fast=True)
    except (OSError, ValueError, RuntimeError) as error:
        raise RuntimeError(f"Could not initialize tokenizer for {model_name!r}: {error}") from error


def estimate_token_count(text: str) -> int:
    """Return the number of model tokens, excluding special tokens."""

    return len(get_tokenizer().encode(text, add_special_tokens=False))


def token_offsets(text: str) -> list[tuple[int, int]]:
    """Return character offsets for each model token, excluding special tokens."""

    tokenizer = get_tokenizer()
    if not getattr(tokenizer, "is_fast", False):
        raise RuntimeError("Tokenizer offset mapping requires a fast Hugging Face tokenizer.")

    try:
        encoded = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    except (NotImplementedError, TypeError, ValueError) as error:
        raise RuntimeError("Tokenizer offset mapping requires a fast Hugging Face tokenizer.") from error

    return [(start, end) for start, end in encoded["offset_mapping"] if end > start]
