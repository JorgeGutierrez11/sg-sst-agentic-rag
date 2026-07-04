"""Pure fixed-token sliding window child chunking."""

from pipeline.chunking.models import ChildChunk, ParentChunk
from pipeline.chunking.config import SLIDING_WINDOW_STRATEGY
from pipeline.chunking.strategies.base import ChunkingStrategy
from pipeline.chunking.tokenization import char_span_for_token_window, tokenize_with_spans


class SlidingWindowStrategy(ChunkingStrategy):
    """Split parent text into fixed token windows with controlled overlap."""

    name = SLIDING_WINDOW_STRATEGY

    def chunk_parent(self, parent: ParentChunk) -> list[ChildChunk]:
        """Create pure sliding-window chunks without legal or semantic constraints."""

        tokens = tokenize_with_spans(parent.text)
        if not tokens:
            return []
        chunks: list[ChildChunk] = []
        step = max(1, self.max_tokens - self.overlap_tokens)
        token_start = 0
        while token_start < len(tokens):
            token_end = min(token_start + self.max_tokens, len(tokens))
            start_char, end_char = char_span_for_token_window(tokens, token_start, token_end)
            text = parent.text[start_char:end_char].strip()
            if text:
                chunks.append(
                    self.build_child(
                        parent,
                        text,
                        len(chunks),
                        start_char,
                        end_char,
                        {
                            "split_reason": "fixed_token_window",
                            "token_start": token_start,
                            "token_end": token_end,
                            "overlap_tokens": self.overlap_tokens if chunks else 0,
                        },
                    )
                )
            if token_end == len(tokens):
                break
            token_start += step
        return chunks
