import logging
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "interim"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def _remove_pandoc_divs(text: str) -> str:
    return re.sub(
        r'^:::[ \t]+\{[^}]+\}[ \t]*\n([\s\S]*?)^:::[ \t]*\n?',
        r'\1',
        text,
        flags=re.MULTILINE
    )


def _remove_images(text: str) -> str:
    text = re.sub(r'!\[.*?\]\([^)]*\)\{[^}]*\}', '', text)
    text = re.sub(r'^[ \t]+$', '', text, flags=re.MULTILINE)
    return text


def _fix_hard_linebreaks(text: str) -> str:
    return re.sub(r'\\\n', ' ', text)


def _clean_underline_spans(text: str) -> str:
    return re.sub(r'\[([^\]]+)\]\{\.underline\}', r'\1', text)


def _fix_escaped_lists(text: str) -> str:
    text = re.sub(r'^(\d+)\\\.', r'\1.', text, flags=re.MULTILINE)
    text = re.sub(r'^\\-', r'-', text, flags=re.MULTILINE)
    text = re.sub(r'^([a-zA-Z])\\\)', r'\1.)', text, flags=re.MULTILINE)
    return text


def _merge_split_bold(text: str) -> str:
    return re.sub(r'\*\*([^\*\n]+)\*\*[ \t]+\*\*', r'**\1 ', text)


def _normalize_blank_lines(text: str) -> str:
    return re.sub(r'\n{3,}', '\n\n', text)


def _fix_degree_symbols(text: str) -> str:
    text = re.sub(r'\*\*Artículo[ \t]+1\*°\*\*\*\*\.[ \t]+\*\*', r'**Artículo 1°**. ***', text)
    text = re.sub(r'\*\*([^*]+)\*\*°\*\*([^*]*)\*\*', r'**\1°\2**', text)
    text = re.sub(r'\*\*([^*]+)\*\*°(?!\*)', r'**\1°**', text)
    return text


def _fix_bold_italic_suffixes(text: str) -> str:
    return re.sub(r'\*\*\*\*([.,;:]*)\*', r'\1***', text)


_CLEANING_OPS = [
    ("Pandoc divs", _remove_pandoc_divs),
    ("Imágenes", _remove_images),
    ("Saltos duros", _fix_hard_linebreaks),
    ("Underline spans", _clean_underline_spans),
    ("Listas escapadas", _fix_escaped_lists),
    ("Bold partido", _merge_split_bold),
    ("Líneas en blanco", _normalize_blank_lines),
    ("Grados", _fix_degree_symbols),
    ("Sufijos bold-italic", _fix_bold_italic_suffixes),
]


def clean_markdown(text: str, stem: str = "") -> str:
    """Apply the configured cleanup operations to Markdown content."""

    for name, fn in _CLEANING_OPS:
        before = len(text)
        text = fn(text)
        logger.debug(f"  [{stem}] {name}: −{before - len(text):,} chars")
    return text


def clean_markdown_directory(input_dir: Path, output_dir: Path) -> None:
    """Clean every Markdown file in a directory and write the results."""

    output_dir.mkdir(parents=True, exist_ok=True)

    md_files = sorted(input_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No se encontraron .md en: {input_dir}")

    logger.info(f"📂 {len(md_files)} archivos .md encontrados")

    for md_path in md_files:
        raw = md_path.read_text(encoding="utf-8")
        cleaned = clean_markdown(raw, stem=md_path.stem)

        out_path = output_dir / md_path.name
        out_path.write_text(cleaned, encoding="utf-8")

        reduction = len(raw) - len(cleaned)
        pct = reduction / len(raw) * 100 if raw else 0
        logger.info(f"  ✅ {md_path.name} | −{reduction:,} chars ({pct:.1f}%)")


def run_phase2(input_dir: Path, output_dir: Path) -> None:
    """Backward-compatible alias for clean_markdown_directory."""

    clean_markdown_directory(input_dir, output_dir)


if __name__ == "__main__":
    INPUT_DIR = DEFAULT_INPUT_DIR
    OUTPUT_DIR = DEFAULT_OUTPUT_DIR

    clean_markdown_directory(INPUT_DIR, OUTPUT_DIR)

    sample = next(OUTPUT_DIR.glob("*.md"), None)
    if sample:
        print(f"\n{'='*60}\nMUESTRA: {sample.name}\n{'='*60}")
        print(sample.read_text(encoding="utf-8")[:800])
