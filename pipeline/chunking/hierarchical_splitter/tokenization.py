"""Deterministic stdlib-only token estimation for Phase 1."""

import re


TOKEN_PATTERN = re.compile(r"\w+(?:[-']\w+)*|[^\w\s]", flags=re.UNICODE)


def estimate_token_count(text: str) -> int:
    """Estimate token count with a deterministic regex tokenizer."""

    return len(TOKEN_PATTERN.findall(text))
