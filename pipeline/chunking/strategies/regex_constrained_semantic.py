"""Hybrid legal-boundary constrained semantic child chunking."""

from pipeline.chunking.config import REGEX_CONSTRAINED_SEMANTIC_STRATEGY
from pipeline.chunking.legal_boundaries import LEGAL_BLOCK_PATTERN, split_legal_blocks
from pipeline.chunking.models import ChildChunk, ParentChunk
from pipeline.chunking.strategies.base import ChunkingStrategy
from pipeline.chunking.strategies.semantic_chunking import (
    TextSegment,
    group_segments_by_token_budget,
    split_semantic_segments,
)
from pipeline.chunking.tokenization import count_tokens


class RegexConstrainedSemanticStrategy(ChunkingStrategy):
    """Keep legal blocks intact when small and semantically split oversized blocks."""

    name = REGEX_CONSTRAINED_SEMANTIC_STRATEGY

    def chunk_parent(self, parent: ParentChunk) -> list[ChildChunk]:
        """Create hybrid chunks constrained by detected legal block boundaries."""

        legal_boundary_detected = bool(LEGAL_BLOCK_PATTERN.search(parent.text))
        segments = self._legal_constrained_segments(parent.text)
        chunks: list[ChildChunk] = []
        for segment in segments:
            chunks.append(
                self.build_child(
                    parent,
                    segment.text,
                    len(chunks),
                    segment.start_char,
                    segment.end_char,
                    {
                        "split_reason": "legal_boundary_or_oversized_semantic_split",
                        "legal_boundary_detected": legal_boundary_detected,
                        "overlap_tokens": 0,
                        "requested_overlap_tokens": self.overlap_tokens if chunks else 0,
                    },
                )
            )
        return chunks

    def _legal_constrained_segments(self, text: str) -> list[TextSegment]:
        legal_blocks = split_legal_blocks(text)
        semantic_segments: list[TextSegment] = []
        for block in legal_blocks:
            if count_tokens(block.text) <= self.max_tokens:
                semantic_segments.append(TextSegment(block.text, block.start_char, block.end_char))
                continue
            for segment in split_semantic_segments(block.text):
                semantic_segments.append(
                    TextSegment(
                        segment.text,
                        block.start_char + segment.start_char,
                        block.start_char + segment.end_char,
                    )
                )
        grouped = group_segments_by_token_budget(semantic_segments, self.max_tokens)
        return _restore_source_slices(text, grouped)


def _restore_source_slices(text: str, segments: list[TextSegment]) -> list[TextSegment]:
    """Rebuild grouped segment text from the original source span."""

    return [
        TextSegment(text[segment.start_char : segment.end_char].strip(), segment.start_char, segment.end_char)
        for segment in segments
    ]
