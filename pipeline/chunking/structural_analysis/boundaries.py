"""Conservative legal boundary detection for Colombian normative Markdown."""

from collections.abc import Iterable
from dataclasses import dataclass
from re import Pattern

from pipeline.chunking.structural_analysis.patterns import BOUNDARY_PATTERNS


@dataclass(frozen=True)
class BoundaryMatch:
    """A structural legal boundary observed in Markdown text."""

    boundary_type: str
    value: str
    start_char: int
    end_char: int
    line: str


def iter_boundary_matches(text: str, boundary_types: Iterable[str] | None = None) -> list[BoundaryMatch]:
    """Return sorted legal boundary matches for the selected boundary types."""

    selected_types = tuple(boundary_types) if boundary_types else tuple(BOUNDARY_PATTERNS)
    matches: list[BoundaryMatch] = []
    for boundary_type in selected_types:
        pattern = BOUNDARY_PATTERNS[boundary_type]
        matches.extend(_matches_for_pattern(text, boundary_type, pattern))
    return sorted(matches, key=lambda match: (match.start_char, match.end_char, match.boundary_type))


def find_article_boundaries(text: str) -> list[BoundaryMatch]:
    """Return article boundary matches in reading order."""

    return iter_boundary_matches(text, boundary_types=("article",))


def extract_first_boundary_value(text: str, boundary_type: str) -> str | None:
    """Return the first matched value for a boundary type, when present."""

    matches = iter_boundary_matches(text, boundary_types=(boundary_type,))
    return matches[0].value if matches else None


def _matches_for_pattern(text: str, boundary_type: str, pattern: Pattern[str]) -> list[BoundaryMatch]:
    matches: list[BoundaryMatch] = []
    for match in pattern.finditer(text):
        line = _line_for_match(text, match.start())
        value = match.group(1).strip(" *.") if match.groups() else ""
        matches.append(BoundaryMatch(boundary_type, value, match.start(), match.end(), line))
    return matches


def _line_for_match(text: str, start_char: int) -> str:
    line_start = text.rfind("\n", 0, start_char) + 1
    line_end = text.find("\n", start_char)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end].strip()
