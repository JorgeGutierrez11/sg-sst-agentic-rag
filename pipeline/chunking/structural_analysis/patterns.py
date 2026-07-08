"""Conservative legal boundary regex patterns for Colombian normative Markdown."""

import re
from re import Pattern


LEGAL_PATTERN_FLAGS = re.IGNORECASE | re.MULTILINE

TITLE_PATTERN = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?(?:\*\*)?T[ÍI]TULO\s+(.+?)(?:\*\*)?\s*$",
    LEGAL_PATTERN_FLAGS,
)
CHAPTER_PATTERN = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?(?:\*\*)?CAP[ÍI]TULO\.?\s+(.+?)(?:\*\*)?\s*$",
    LEGAL_PATTERN_FLAGS,
)
SECTION_PATTERN = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?(?:\*\*)?SECCI[ÓO]N\s+(.+?)(?:\*\*)?\s*$",
    LEGAL_PATTERN_FLAGS,
)
ARTICLE_PATTERN = re.compile(
    r"(?:^\s{0,3}(?:#{1,6}\s*)?(?:\*\*)?|\s{2,}\*\*)Art[íi]culo\s+([\w.°º-]+)(?:\*\*)?\.?:?",
    LEGAL_PATTERN_FLAGS,
)
PARAGRAPH_PATTERN = re.compile(r"^\s{0,3}(?:\*\*)?Par[áa]grafo\b\s*([\w°º.-]*)", LEGAL_PATTERN_FLAGS)
NUMERAL_PATTERN = re.compile(r"^\s{0,6}(\d{1,3})[.)]\s+", re.MULTILINE)
LITERAL_PATTERN = re.compile(r"^\s{0,6}([a-z])\)\s+", LEGAL_PATTERN_FLAGS)

BOUNDARY_PATTERNS: dict[str, Pattern[str]] = {
    "title": TITLE_PATTERN,
    "chapter": CHAPTER_PATTERN,
    "section": SECTION_PATTERN,
    "article": ARTICLE_PATTERN,
    "paragraph": PARAGRAPH_PATTERN,
    "numeral": NUMERAL_PATTERN,
    "literal": LITERAL_PATTERN,
}
