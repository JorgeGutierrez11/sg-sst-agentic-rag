"""Pure semantic child chunking with deterministic lexical fallback."""

import re
from dataclasses import dataclass

from pipeline.chunking.config import SEMANTIC_CHUNKING_STRATEGY
from pipeline.chunking.models import ChildChunk, ParentChunk
from pipeline.chunking.strategies.base import ChunkingStrategy
from pipeline.chunking.tokenization import count_tokens


SENTENCE_PATTERN = re.compile(r"[^.!?\n]+(?:[.!?]+|\n+|$)", flags=re.UNICODE)


@dataclass(frozen=True, slots=True)
class TextSegment:
    """Text segment with offsets."""

    text: str
    start_char: int
    end_char: int


class SemanticChunkingStrategy(ChunkingStrategy):
    """Split by paragraph and sentence cohesion without legal regex constraints."""

    name = SEMANTIC_CHUNKING_STRATEGY

    def chunk_parent(self, parent: ParentChunk) -> list[ChildChunk]:
        """Create pure semantic chunks using deterministic lexical boundaries."""

        segments = split_semantic_segments(parent.text)
        grouped = group_segments_by_token_budget(segments, self.max_tokens)
        return [
            self.build_child(
                parent,
                segment.text,
                index,
                segment.start_char,
                segment.end_char,
                {"split_reason": "lexical_semantic_boundary", "semantic_backend": "deterministic_fallback"},
            )
            for index, segment in enumerate(grouped)
            if segment.text.strip()
        ]


def split_semantic_segments(text: str) -> list[TextSegment]:
    """Split text into paragraph-first, sentence-second semantic segments."""

    paragraphs = _paragraph_segments(text)
    segments: list[TextSegment] = []
    for paragraph in paragraphs:
        if count_tokens(paragraph.text) <= 120:
            segments.append(paragraph)
            continue
        segments.extend(_sentence_segments(paragraph.text, paragraph.start_char))
    return segments or [TextSegment(text.strip(), text.find(text.strip()), len(text.strip()))]


def group_segments_by_token_budget(segments: list[TextSegment], max_tokens: int) -> list[TextSegment]:
    """Group semantic segments into chunks under the configured token budget."""

    groups: list[TextSegment] = []
    current: list[TextSegment] = []
    current_tokens = 0
    for segment in segments:
        segment_tokens = count_tokens(segment.text)
        if current and current_tokens + segment_tokens > max_tokens:
            groups.append(_merge_segments(current))
            current = []
            current_tokens = 0
        if segment_tokens > max_tokens:
            groups.extend(_split_oversized_segment(segment, max_tokens))
            continue
        current.append(segment)
        current_tokens += segment_tokens
    if current:
        groups.append(_merge_segments(current))
    return groups


def _paragraph_segments(text: str) -> list[TextSegment]:
    segments: list[TextSegment] = []
    cursor = 0
    for raw in re.split(r"(\n\s*\n+)", text):
        start = cursor
        cursor += len(raw)
        clean = raw.strip()
        if clean and not raw.strip().startswith("\n"):
            local_start = raw.find(clean)
            segments.append(TextSegment(clean, start + local_start, start + local_start + len(clean)))
    return segments


def _sentence_segments(text: str, offset: int) -> list[TextSegment]:
    segments = []
    for match in SENTENCE_PATTERN.finditer(text):
        clean = match.group(0).strip()
        if clean:
            start = offset + match.start() + match.group(0).find(clean)
            segments.append(TextSegment(clean, start, start + len(clean)))
    return segments


def _split_oversized_segment(segment: TextSegment, max_tokens: int) -> list[TextSegment]:
    from pipeline.chunking.tokenization import char_span_for_token_window, tokenize_with_spans

    tokens = tokenize_with_spans(segment.text)
    pieces = []
    for token_start in range(0, len(tokens), max_tokens):
        token_end = min(token_start + max_tokens, len(tokens))
        start, end = char_span_for_token_window(tokens, token_start, token_end)
        piece_text = segment.text[start:end].strip()
        if piece_text:
            pieces.append(TextSegment(piece_text, segment.start_char + start, segment.start_char + end))
    return pieces


def _merge_segments(segments: list[TextSegment]) -> TextSegment:
    text = "\n\n".join(segment.text for segment in segments).strip()
    return TextSegment(text, segments[0].start_char, segments[-1].end_char)
