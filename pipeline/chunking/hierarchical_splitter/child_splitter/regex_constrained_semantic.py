"""Build source-preserving semantic child chunks constrained by regex spans."""

import math
import re
from dataclasses import dataclass
from pathlib import Path

from pipeline.chunking.core.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_MIN_TOKENS, DEFAULT_TABLES_ROOT
from pipeline.chunking.core.io_jsonl import read_parent_chunks, write_child_chunks
from pipeline.chunking.hierarchical_splitter.child_splitter.shared import (
    build_child_chunk,
    embedding_kwargs_for_model,
)
from pipeline.chunking.hierarchical_splitter.models import ChildBuildResult, ChildChunk, ParentChunk
from pipeline.chunking.hierarchical_splitter.tokenization import estimate_token_count, token_offsets
from pipeline.tables.table_references import validate_table_html_references

REGEX_CONSTRAINED_SEMANTIC_BACKEND = "custom_regex_constrained_semantic"
REGEX_CONSTRAINED_SEMANTIC_SPLIT_REASON = "semantic_breakpoint_with_regex_constraints"
SUPPORTED_THRESHOLD_TYPES = {"percentile", "gradient"}

# Definición de estructuras internas

@dataclass(frozen=True)
class TextUnit:
    """One exact text span available for semantic grouping."""

    text: str
    start_char: int
    end_char: int
    unit_type: str # Puede ser "paragraph" o "sentence"


@dataclass(frozen=True)
class ChunkSpan:
    """Internal exact parent span built from contiguous text units."""

    start_char: int
    end_char: int
    units: list[TextUnit]
    size_adjustment: str = "none" # Puede ser "none", "merge" o "split"


# Aplicación del método regex-constrained semantic

def write_regex_constrained_semantic_child_output(
    input_path: Path,                       
    output_path: Path,                      
    breakpoint_threshold_type: str,         # Tipo de umbral para los cortes semánticos
    breakpoint_threshold_amount: float,     # Cantidad del umbral
    embedding_model: str = DEFAULT_EMBEDDING_MODEL, 
    min_tokens: int = DEFAULT_MIN_TOKENS,   
    max_tokens: int = DEFAULT_MAX_TOKENS,
    tables_root: Path = DEFAULT_TABLES_ROOT,
) -> ChildBuildResult:
    """Read parent chunks, write regex-constrained semantic children, and return a summary."""

    validate_regex_constrained_semantic_options(
        breakpoint_threshold_type,
        breakpoint_threshold_amount,
        embedding_model,
        min_tokens,
        max_tokens,
    )
    if not input_path.exists():
        raise FileNotFoundError(f"Parent chunks input does not exist: {input_path}")

    parents = read_parent_chunks(input_path)
    children = build_regex_constrained_semantic_child_chunks(
        parents,
        breakpoint_threshold_type,
        breakpoint_threshold_amount,
        embedding_model,
        min_tokens,
        max_tokens,
    )
    validate_table_html_references(children, tables_root)
    write_child_chunks(children, output_path)
    return ChildBuildResult(parent_count=len(parents), chunk_count=len(children), output_path=output_path)


def build_regex_constrained_semantic_child_chunks(
    parents: list[ParentChunk],
    breakpoint_threshold_type: str,
    breakpoint_threshold_amount: float,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    min_tokens: int = DEFAULT_MIN_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[ChildChunk]:
    """Split parents by semantic breakpoints while emitting only exact source slices."""

    # validate_regex_constrained_semantic_options(
    #     breakpoint_threshold_type,
    #     breakpoint_threshold_amount,
    #     embedding_model,
    #     min_tokens,
    #     max_tokens,
    # )
    if not parents:
        return []

    embeddings = create_embedding_backend(embedding_model)
    children: list[ChildChunk] = []
    for parent in parents:
        units = extract_text_units(parent.text)
        if not units:
            continue

        breakpoints = semantic_breakpoints(units, embeddings, breakpoint_threshold_type, breakpoint_threshold_amount)
        spans = adjust_chunk_sizes(spans_from_breakpoints(units, breakpoints), parent.text, min_tokens, max_tokens)
        for chunk_index, span in enumerate(spans):
            children.append(
                create_regex_constrained_semantic_child_chunk(
                    parent,
                    span,
                    chunk_index,
                    embedding_model,
                    breakpoint_threshold_type,
                    breakpoint_threshold_amount,
                )
            )
    return children


# Definición de regex y unidades de texto

def extract_text_units(parent_text: str) -> list[TextUnit]:
    """Extract ordered non-empty paragraph/sentence units with exact parent offsets."""

    units: list[TextUnit] = []
    for match in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", parent_text, flags=re.DOTALL):
        block = match.group(0) # coincide con un bloque de texto
        if estimate_token_count(block) > DEFAULT_MAX_TOKENS:
            units.extend(sentence_units(block, match.start())) # Divide el bloque en unidades
        else:
            units.append(TextUnit(
                block,
                match.start(),
                match.end(),
                "paragraph"
            ))
    return units


def sentence_units(text: str, offset: int) -> list[TextUnit]:
    """Split an oversized paragraph into exact sentence-like units."""

    units: list[TextUnit] = []
    for match in re.finditer(r"\S[^.!?;:\n]*(?:[.!?;:]|(?=\n)|\Z)", text, flags=re.UNICODE):
        unit_text = match.group(0).strip()
        if not unit_text:
            continue
        start = offset + match.start() + len(match.group(0)) - len(match.group(0).lstrip())
        end = start + len(unit_text)
        units.append(TextUnit(
            unit_text,
            start,
            end,
            "sentence"
        ))

    if not units:
        stripped = text.strip()
        start = offset + text.index(stripped)
        return [TextUnit(
            stripped, 
            start, 
            start + len(stripped),
            "paragraph"
            )]
    return units


# Configuración de embeddings

def create_embedding_backend(embedding_model: str):
    """Create the embedding backend lazily so CLI validation stays dependency-light."""

    try:
        # pyrefly: ignore [missing-import]
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=embedding_model,
            **embedding_kwargs_for_model(embedding_model)
        )
    except (ImportError, TypeError, ValueError, RuntimeError, OSError) as error:
        raise RuntimeError(f"Could not initialize regex-constrained semantic backend: {error}") from error


# Cálculo de cortes semánticos

# Toma varias unidades de texto, calcula qué tan distintas son entre sí usando embeddings,
# y devuelve los índices después de los cuales conviene partir el chunk.
def semantic_breakpoints(
    units: list[TextUnit],
    embeddings,
    breakpoint_threshold_type: str,
    breakpoint_threshold_amount: float,
) -> set[int]:
    """Return unit indexes after which a semantic cut should be made."""

    if len(units) < 2:
        return set()

    vectors = embeddings.embed_documents([unit.text for unit in units])
    distances = [
        cosine_distance(vectors[index], vectors[index + 1])
        for index in range(len(vectors) - 1)
    ]

    if breakpoint_threshold_type == "percentile":
        threshold = percentile(distances, breakpoint_threshold_amount)
        return {
            index
            for index, distance in enumerate(distances)
            if distance >= threshold and distance > 0
        }

    if breakpoint_threshold_type == "gradient":
        if len(distances) < 2:
            return set()
        gradients = [
            abs(distances[index + 1] - distances[index])
            for index in range(len(distances) - 1)
        ]
        threshold = percentile(gradients, breakpoint_threshold_amount)
        return {
            index + 1
            for index, gradient in enumerate(gradients)
            if gradient >= threshold and gradient > 0
        }
    raise ValueError(f"Unsupported breakpoint threshold type: {breakpoint_threshold_type}")


# Construcción de spans desde los cortes

def spans_from_breakpoints(units: list[TextUnit], breakpoints: set[int]) -> list[ChunkSpan]:
    """Convert unit breakpoints into contiguous exact source spans."""

    spans: list[ChunkSpan] = []
    start_index = 0
    for index in range(len(units)):
        if index in breakpoints:
            spans.append(span_from_units(units[start_index:index + 1]))
            start_index = index + 1
    if start_index < len(units):
        spans.append(span_from_units(units[start_index:]))
    return spans


# Ajuste de tamaños mínimo y máximo

def adjust_chunk_sizes(spans: list[ChunkSpan], parent_text: str, min_tokens: int, max_tokens: int) -> list[ChunkSpan]:
    """Merge tiny spans and split oversized spans without losing source offsets."""

    merged = merge_small_spans(spans, parent_text, min_tokens, max_tokens)
    adjusted: list[ChunkSpan] = []
    for span in merged:
        if token_count_for_span(span, parent_text) > max_tokens:
            adjusted.extend(split_oversized_span(span, parent_text, max_tokens))
        else:
            adjusted.append(span)
    return adjusted


def merge_small_spans(spans: list[ChunkSpan], parent_text: str, min_tokens: int, max_tokens: int) -> list[ChunkSpan]:
    """Merge chunks below the minimum token target with an adjacent span when possible."""

    merged: list[ChunkSpan] = []
    index = 0
    while index < len(spans):
        span = spans[index]
        if token_count_for_span(span, parent_text) >= min_tokens or len(spans) == 1:
            merged.append(span)
            index += 1
            continue
        if index + 1 < len(spans):
            merged.append(combine_spans(span, spans[index + 1], "merged_small_chunk"))
            index += 2
        elif merged:
            previous = merged.pop()
            merged.append(combine_spans(previous, span, "merged_small_chunk"))
            index += 1
        else:
            merged.append(span)
            index += 1
    return merged


def split_oversized_span(span: ChunkSpan, parent_text: str, max_tokens: int) -> list[ChunkSpan]:
    """Split an oversized span by internal units, then by local token spans if needed."""

    pieces: list[ChunkSpan] = []
    current_units: list[TextUnit] = []
    for unit in span.units:
        candidate = current_units + [unit]
        candidate_span = span_from_units(candidate, "split_oversized_chunk")
        if current_units and token_count_for_span(candidate_span, parent_text) > max_tokens:
            pieces.append(span_from_units(current_units, "split_oversized_chunk"))
            current_units = [unit]
        else:
            current_units = candidate
    if current_units:
        pieces.append(span_from_units(current_units, "split_oversized_chunk"))

    final_pieces: list[ChunkSpan] = []
    for piece in pieces:
        if len(piece.units) == 1 and token_count_for_span(piece, parent_text) > max_tokens:
            final_pieces.extend(split_single_unit_by_tokens(piece.units[0], parent_text, max_tokens))
        else:
            final_pieces.append(piece)
    return final_pieces


def split_single_unit_by_tokens(unit: TextUnit, parent_text: str, max_tokens: int) -> list[ChunkSpan]:
    """Fallback split for one oversized regex unit using exact tokenizer offsets."""

    offsets = token_offsets(parent_text[unit.start_char:unit.end_char])
    if not offsets:
        return [ChunkSpan(unit.start_char, unit.end_char, [unit], "split_oversized_chunk")]

    pieces: list[ChunkSpan] = []
    for start_index in range(0, len(offsets), max_tokens):
        batch = offsets[start_index:start_index + max_tokens]
        start = unit.start_char + batch[0][0]
        end = unit.start_char + batch[-1][1]
        text_unit = TextUnit(parent_text[start:end], start, end, "token_window")
        pieces.append(ChunkSpan(start, end, [text_unit], "split_oversized_chunk"))
    return pieces


# Creación final de child chunks trazables

def create_regex_constrained_semantic_child_chunk(
    parent: ParentChunk,
    span: ChunkSpan,
    chunk_index: int,
    embedding_model: str,
    breakpoint_threshold_type: str,
    breakpoint_threshold_amount: float,
) -> ChildChunk:
    """Create one child chunk from an exact source slice."""

    text = parent.text[span.start_char:span.end_char]
    return build_child_chunk(
        parent,
        text,
        chunk_index,
        span.start_char,
        {
            "strategy": "regex_constrained_semantic",
            "backend": REGEX_CONSTRAINED_SEMANTIC_BACKEND,
            "embedding_model": embedding_model,
            "chunk_index": chunk_index,
            "parent_chunk_id": parent.chunk_id,
            "breakpoint_threshold_type": breakpoint_threshold_type,
            "breakpoint_threshold_amount": breakpoint_threshold_amount,
            "split_reason": REGEX_CONSTRAINED_SEMANTIC_SPLIT_REASON,
            "offset_status": "resolved",
            "unit_count": len(span.units),
            "unit_types": sorted({unit.unit_type for unit in span.units}),
            "size_adjustment": span.size_adjustment,
        },
        require_resolved_offsets=True,
    )


# Validación de opciones del método

def validate_regex_constrained_semantic_options(
    breakpoint_threshold_type: str,
    breakpoint_threshold_amount: float,
    embedding_model: str,
    min_tokens: int,
    max_tokens: int,
) -> None:
    """Reject invalid options before model loading starts."""

    if breakpoint_threshold_type not in SUPPORTED_THRESHOLD_TYPES:
        raise ValueError(
            "--breakpoint-threshold-type must be one of: "
            f"{', '.join(sorted(SUPPORTED_THRESHOLD_TYPES))}."
        )
    if breakpoint_threshold_amount < 0 or breakpoint_threshold_amount > 100:
        raise ValueError("--breakpoint-threshold-amount must be between 0 and 100.")
    if not embedding_model.strip():
        raise ValueError("Embedding model name must not be empty.")
    if min_tokens < 0:
        raise ValueError("--min-tokens must be greater than or equal to 0.")
    if max_tokens <= 0:
        raise ValueError("--max-tokens must be greater than 0.")
    if min_tokens >= max_tokens:
        raise ValueError("--min-tokens must be lower than --max-tokens.")


# Utilidades internas de spans, tokens y distancias

def span_from_units(units: list[TextUnit], size_adjustment: str = "none") -> ChunkSpan:
    """Build a span covering contiguous units and their original separators."""

    return ChunkSpan(units[0].start_char, units[-1].end_char, units, size_adjustment)


def combine_spans(left: ChunkSpan, right: ChunkSpan, size_adjustment: str) -> ChunkSpan:
    """Combine two adjacent spans while preserving exact source boundaries."""

    return ChunkSpan(left.start_char, right.end_char, left.units + right.units, size_adjustment)


def token_count_for_span(span: ChunkSpan, parent_text: str) -> int:
    """Estimate tokens for an exact parent text slice."""

    return estimate_token_count(parent_text[span.start_char:span.end_char])


def cosine_distance(left: list[float], right: list[float]) -> float:
    """Return cosine distance between two embedding vectors."""

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return 1 - (dot / (left_norm * right_norm))


def percentile(values: list[float], amount: float) -> float:
    """Return a simple interpolated percentile without adding a numeric dependency."""

    if not values:
        return 0.0

    ordered = sorted(values)
    position = (len(ordered) - 1) * (amount / 100)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(position)]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction
