"""Deterministic approximate tokenization with character offsets."""

import re
from dataclasses import dataclass


TOKEN_PATTERN = re.compile(r"\w+(?:[-°]\w+)*|[^\w\s]", flags=re.UNICODE)


@dataclass(frozen=True, slots=True)
class TokenSpan:
    """Approximate token and its source character span."""

    text: str
    start: int
    end: int


def tokenize_with_spans(text: str) -> list[TokenSpan]:
    """Split text into deterministic approximate tokens with offsets."""

    return [TokenSpan(match.group(0), match.start(), match.end()) for match in TOKEN_PATTERN.finditer(text)]


def count_tokens(text: str) -> int:
    """Count approximate tokens deterministically."""

    return len(tokenize_with_spans(text))


def char_span_for_token_window(tokens: list[TokenSpan], start: int, end: int) -> tuple[int, int]:
    """Return the character span covered by a token window."""

    if not tokens or start >= end:
        return 0, 0
    bounded_start = max(0, min(start, len(tokens) - 1))
    bounded_end = max(bounded_start + 1, min(end, len(tokens)))
    return tokens[bounded_start].start, tokens[bounded_end - 1].end
