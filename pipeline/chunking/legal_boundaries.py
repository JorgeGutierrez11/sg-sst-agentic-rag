"""Regex-based detection of SG-SST legal hierarchy and legal text blocks."""

import re
from dataclasses import dataclass
from typing import Any


Hierarchy = dict[str, Any]

DOCUMENT_PATTERN = re.compile(
    r"\b(?P<document_type>Decreto|Resoluci[oó]n|Ley)\s+(?P<number>\d{1,5})\s+(?:de\s+)?(?P<year>\d{4})\b",
    flags=re.IGNORECASE,
)
HEADING_PATTERNS = {
    "title": re.compile(r"^\s{0,3}#{1,6}\s*T[ÍI]TULO\s+(.+)$|^\s*T[ÍI]TULO\s+(.+)$", re.IGNORECASE),
    "chapter": re.compile(r"^\s{0,3}#{1,6}\s*CAP[ÍI]TULO\s+(.+)$|^\s*CAP[ÍI]TULO\s+(.+)$", re.IGNORECASE),
    "section": re.compile(r"^\s{0,3}#{1,6}\s*SECCI[ÓO]N\s+(.+)$|^\s*SECCI[ÓO]N\s+(.+)$", re.IGNORECASE),
    "article": re.compile(r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:\*\*)?Art[íi]culo\s+(?P<value>[\w.°-]+)", re.IGNORECASE),
    "paragraph": re.compile(r"\bPar[áa]grafo\s*(?P<value>\d*|transitorio)?\b", re.IGNORECASE),
    "numeral": re.compile(r"(?:^|\n)\s*(?P<value>\d+(?:\.\d+)*)[.)]\s+", re.IGNORECASE),
    "literal": re.compile(r"(?:^|\n)\s*(?P<value>[a-z])[.)]\s+", re.IGNORECASE),
}
LEGAL_BLOCK_PATTERN = re.compile(
    r"(?m)^\s*(?:#{1,6}\s*)?(?:\*\*)?(?:Art[íi]culo\s+[\w.°-]+|Par[áa]grafo\b|\d+(?:\.\d+)*[.)]|[a-z][.)])\s+"
)


@dataclass(frozen=True, slots=True)
class LegalBlock:
    """Detected legal block with source offsets."""

    text: str
    start_char: int
    end_char: int
    hierarchy: Hierarchy


def extract_document_identity(text: str) -> Hierarchy:
    """Extract legal document type, number, and year when present."""

    match = DOCUMENT_PATTERN.search(text)
    if not match:
        return {}
    return {
        "document_type": _normalize_document_type(match.group("document_type")),
        "document_number": match.group("number"),
        "year": match.group("year"),
    }


def extract_hierarchy(text: str) -> Hierarchy:
    """Extract the first detectable legal hierarchy markers from text."""

    hierarchy = extract_document_identity(text)
    for key, pattern in HEADING_PATTERNS.items():
        match = pattern.search(text)
        if not match:
            continue
        value = match.groupdict().get("value") or next((item for item in match.groups() if item), "")
        hierarchy[key] = _clean_marker(value)
    return hierarchy


def split_legal_blocks(text: str) -> list[LegalBlock]:
    """Split text at legal block markers while preserving source offsets."""

    matches = list(LEGAL_BLOCK_PATTERN.finditer(text))
    if not matches:
        stripped = text.strip()
        if not stripped:
            return []
        start = text.find(stripped)
        return [LegalBlock(stripped, start, start + len(stripped), extract_hierarchy(stripped))]

    blocks: list[LegalBlock] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block_text = text[start:end].strip()
        if not block_text:
            continue
        block_start = start + (len(text[start:end]) - len(text[start:end].lstrip()))
        blocks.append(LegalBlock(block_text, block_start, block_start + len(block_text), extract_hierarchy(block_text)))
    return blocks


def merge_hierarchy(base: Hierarchy, update: Hierarchy) -> Hierarchy:
    """Merge hierarchy values while ignoring empty updates."""

    merged = dict(base)
    merged.update({key: value for key, value in update.items() if value not in (None, "")})
    return merged


def _normalize_document_type(value: str) -> str:
    normalized = value.lower().replace("ó", "o")
    return {"decreto": "Decreto", "resolucion": "Resolución", "ley": "Ley"}.get(normalized, value.title())


def _clean_marker(value: str) -> str:
    return re.sub(r"[*_`#]+", "", value).strip(" .:-\t")
