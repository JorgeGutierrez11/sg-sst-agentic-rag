import logging
import re
from pathlib import Path
from collections.abc import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "interim"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


# Public API

def clean_markdown(text: str, stem: str = "") -> str:
    """Apply the configured cleanup operations to Markdown content."""

    for name, operation in _CLEANING_OPS:
        before = len(text)
        text = operation(text)

        logger.debug(
            "  [%s] %s: −%s chars",
            stem,
            name,
            f"{before - len(text):,}",
        )

    return text


def clean_markdown_directory(input_dir: Path, output_dir: Path) -> None:
    """Clean every Markdown file in a directory and write the results."""

    output_dir.mkdir(parents=True, exist_ok=True)

    md_files = sorted(input_dir.glob("*.md"))

    if not md_files:
        raise FileNotFoundError(
            f"No se encontraron .md en: {input_dir}"
        )

    logger.info("📂 %s archivos .md encontrados", len(md_files))

    for md_path in md_files:
        raw = md_path.read_text(encoding="utf-8")

        cleaned = clean_markdown(
            raw,
            stem=md_path.stem,
        )

        out_path = output_dir / md_path.name
        out_path.write_text(
            cleaned,
            encoding="utf-8",
        )

        reduction = len(raw) - len(cleaned)
        pct = reduction / len(raw) * 100 if raw else 0

        logger.info(
            "  ✅ %s | −%s chars (%.1f%%)",
            md_path.name,
            f"{reduction:,}",
            pct,
        )


def run_phase2(input_dir: Path, output_dir: Path) -> None:
    """Backward-compatible alias for clean_markdown_directory."""

    clean_markdown_directory(
        input_dir,
        output_dir,
    )


# Cleaning operations

def _remove_pandoc_divs(text: str) -> str:
    """Remove Pandoc fenced div wrappers while preserving their content."""

    return re.sub(
        r"^:::[ \t]+\{[^}]+\}[ \t]*\n([\s\S]*?)^:::[ \t]*\n?",
        r"\1",
        text,
        flags=re.MULTILINE,
    )


def _remove_images(text: str) -> str:
    """Remove Markdown images and empty lines left by them."""

    text = re.sub(
        r"!\[.*?\]\([^)]*\)\{[^}]*\}",
        "",
        text,
    )

    return re.sub(
        r"^[ \t]+$",
        "",
        text,
        flags=re.MULTILINE,
    )


def _fix_hard_linebreaks(text: str) -> str:
    """Replace escaped Markdown hard line breaks with normal spaces."""

    return re.sub(
        r"\\\n",
        " ",
        text,
    )


def _clean_underline_spans(text: str) -> str:
    """Remove Pandoc underline annotations while preserving their text."""

    return re.sub(
        r"\[([^\]]+)\]\{\.underline\}",
        r"\1",
        text,
    )


def _fix_escaped_lists(text: str) -> str:
    """Normalize escaped ordered, unordered and alphabetic lists."""

    text = re.sub(
        r"^(\d+)\\\.",
        r"\1.",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"^\\-",
        "-",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"^([a-zA-Z])\\\)",
        r"\1.)",
        text,
        flags=re.MULTILINE,
    )

    return text


def _fix_soft_hyphen_artifacts(text: str) -> str:
    """Remove soft-hyphen artifacts introduced during DOCX/Pandoc conversion."""

    # Markdown markers incorrectly inserted around a soft hyphen.
    text = re.sub(
        r"\*{3}\u00ad\*{3}",
        "",
        text,
    )

    # Remaining soft hyphens embedded in extracted words.
    return text.replace("\u00ad", "")


def _merge_split_bold(text: str) -> str:
    """Merge adjacent bold fragments incorrectly split by Pandoc."""

    return re.sub(
        r"\*\*([^*\n]+)\*\*[ \t]+\*\*",
        r"**\1 ",
        text,
    )


def _normalize_blank_lines(text: str) -> str:
    """Limit consecutive blank lines to one empty Markdown line."""

    return re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )


def _fix_degree_symbols(text: str) -> str:
    """Repair malformed bold formatting around degree symbols."""

    text = re.sub(
        r"\*\*Artículo[ \t]+1\*°\*\*\*\*\.[ \t]+\*\*",
        r"**Artículo 1°**. ***",
        text,
    )

    text = re.sub(
        r"\*\*([^*]+)\*\*°\*\*([^*]*)\*\*",
        r"**\1°\2**",
        text,
    )

    text = re.sub(
        r"\*\*([^*]+)\*\*°(?!\*)",
        r"**\1°**",
        text,
    )

    return text


def _fix_bold_italic_suffixes(text: str) -> str:
    """Repair punctuation placed outside malformed bold-italic markers."""

    return re.sub(
        r"\*\*\*\*([.,;:]*)\*",
        r"\1***",
        text,
    )


def _normalize_article_headings(text: str) -> str:
    """
    Input pattern:

        **Artículo 2.2.4.6.17. *Planificación del SG-SST. ***El empleador...

    Output:

        ***Artículo 2.2.4.6.17. Planificación del SG-SST.*** El empleador...
    """

    return _ARTICLE_HEADING_PATTERN.sub(
        _replace_article_heading,
        text,
    )


def _replace_article_heading(match: re.Match[str]) -> str:
    """Build a balanced Markdown article heading from a malformed match."""

    indent = match.group("indent")
    article = match.group("article").strip()
    title = match.group("title").strip()

    return f"{indent}***{article} {title}*** "


# Cleaning configuration

_ARTICLE_HEADING_PATTERN = re.compile(
    r"^"
    r"(?P<indent>[ \t]*)"
    r"\*\*"
    r"(?P<article>Artículo[ \t]+[^*\n]+?)"
    r"[ \t]+\*"
    r"(?P<title>[^*\n]+?)"
    r"[ \t]*"
    r"\*\*\*"
    r"[ \t]*",
    flags=re.MULTILINE,
)


_CLEANING_OPS: tuple[
    tuple[str, Callable[[str], str]],
    ...,
] = (
    ("Pandoc divs", _remove_pandoc_divs),
    ("Imágenes", _remove_images),
    ("Saltos duros", _fix_hard_linebreaks),
    ("Underline spans", _clean_underline_spans),
    ("Listas escapadas", _fix_escaped_lists),

    # Must happen before article normalization.
    ("Soft hyphens", _fix_soft_hyphen_artifacts),

    ("Bold partido", _merge_split_bold),
    ("Líneas en blanco", _normalize_blank_lines),
    ("Grados", _fix_degree_symbols),
    ("Sufijos bold-italic", _fix_bold_italic_suffixes),

    # Specialized legal-heading normalization.
    ("Encabezados de artículos", _normalize_article_headings),
)


# CLI

if __name__ == "__main__":
    clean_markdown_directory(
        DEFAULT_INPUT_DIR,
        DEFAULT_OUTPUT_DIR,
    )

    sample = next(
        DEFAULT_OUTPUT_DIR.glob("*.md"),
        None,
    )

    if sample:
        print(f"\n{'=' * 60}")
        print(f"MUESTRA: {sample.name}")
        print("=" * 60)
        print(
            sample.read_text(encoding="utf-8")[:800]
        )