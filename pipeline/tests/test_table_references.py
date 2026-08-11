"""Tests for pure table placeholder detection."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pipeline.chunking.core.cli import main
from pipeline.tables.table_references import (
    audit_table_references,
    missing_table_html_paths,
    table_html_path,
    table_references_for_text,
    validate_table_html_references,
)


class TableReferencesTest(unittest.TestCase):
    """Verify minimal table reference metadata extraction."""

    def test_no_placeholder_returns_empty_list(self) -> None:
        references = table_references_for_text("Artículo 1. Texto sin tablas.", "Decreto 1072 de 2015")

        self.assertEqual(references, [])

    def test_one_placeholder_returns_minimal_metadata(self) -> None:
        references = table_references_for_text("Texto previo. <!-- TABLE_0 --> Texto posterior.", "Resolución 0312 de 2019")

        self.assertEqual(
            references,
            [
                {
                    "placeholder": "<!-- TABLE_0 -->",
                    "table_index": 0,
                    "source_stem": "Resolución 0312 de 2019",
                }
            ],
        )

    def test_whitespace_tolerant_placeholder_returns_original_placeholder(self) -> None:
        references = table_references_for_text("Texto <!--   TABLE_12   --> cierre.", "Resolución 2346 de 2007")

        self.assertEqual(
            references,
            [
                {
                    "placeholder": "<!--   TABLE_12   -->",
                    "table_index": 12,
                    "source_stem": "Resolución 2346 de 2007",
                }
            ],
        )

    def test_multiple_placeholders_preserve_order(self) -> None:
        references = table_references_for_text(
            "Inicio <!-- TABLE_2 --> medio <!-- TABLE_0 --> fin <!--   TABLE_12   -->.",
            "Ley 1562 de 2012",
        )

        self.assertEqual(
            references,
            [
                {
                    "placeholder": "<!-- TABLE_2 -->",
                    "table_index": 2,
                    "source_stem": "Ley 1562 de 2012",
                },
                {
                    "placeholder": "<!-- TABLE_0 -->",
                    "table_index": 0,
                    "source_stem": "Ley 1562 de 2012",
                },
                {
                    "placeholder": "<!--   TABLE_12   -->",
                    "table_index": 12,
                    "source_stem": "Ley 1562 de 2012",
                },
            ],
        )

    def test_table_html_path_uses_convention(self) -> None:
        path = table_html_path(Path("data/interim/tables"), "Resolución 0312 de 2019", 3)

        self.assertEqual(path, Path("data/interim/tables/Resolución 0312 de 2019/table_3.html"))

    def test_table_html_path_rejects_unsafe_source_stems(self) -> None:
        unsafe_source_stems = ["../outside", "/tmp/outside", "nested/source", "nested\\source", "", ".", ".."]

        for source_stem in unsafe_source_stems:
            with self.subTest(source_stem=source_stem):
                with self.assertRaisesRegex(ValueError, "Unsafe table source stem"):
                    table_html_path(Path("data/interim/tables"), source_stem, 0)

    def test_validation_passes_when_referenced_html_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tables_root = Path(temp_dir) / "tables"
            table_path = tables_root / "norma" / "table_0.html"
            table_path.parent.mkdir(parents=True)
            table_path.write_text("<table></table>", encoding="utf-8")
            chunks = [chunk_record_with_tables("norma", 0)]

            validate_table_html_references(chunks, tables_root)

            self.assertEqual(missing_table_html_paths(chunks, tables_root), [])

    def test_validation_fails_clearly_when_referenced_html_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tables_root = Path(temp_dir) / "tables"

            with self.assertRaisesRegex(ValueError, "Chunk references missing table file: .*table_2.html"):
                validate_table_html_references([chunk_record_with_tables("norma", 2)], tables_root)

    def test_audit_returns_missing_referenced_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tables_root = Path(temp_dir) / "tables"

            missing_files, orphaned_tables = audit_table_references([chunk_record_with_tables("norma", 2)], tables_root)

            self.assertEqual(missing_files, [str(tables_root / "norma" / "table_2.html")])
            self.assertEqual(orphaned_tables, [])

    def test_audit_returns_orphaned_existing_table_html_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tables_root = Path(temp_dir) / "tables"
            referenced_path = tables_root / "norma" / "table_0.html"
            orphaned_path = tables_root / "norma" / "table_1.html"
            referenced_path.parent.mkdir(parents=True)
            referenced_path.write_text("<table></table>", encoding="utf-8")
            orphaned_path.write_text("<table></table>", encoding="utf-8")

            missing_files, orphaned_tables = audit_table_references([chunk_record_with_tables("norma", 0)], tables_root)

            self.assertEqual(missing_files, [])
            self.assertEqual(orphaned_tables, [str(orphaned_path)])

    def test_audit_passes_with_no_missing_or_orphaned_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tables_root = Path(temp_dir) / "tables"
            table_path = tables_root / "norma" / "table_0.html"
            table_path.parent.mkdir(parents=True)
            table_path.write_text("<table></table>", encoding="utf-8")

            missing_files, orphaned_tables = audit_table_references([chunk_record_with_tables("norma", 0)], tables_root)

            self.assertEqual(missing_files, [])
            self.assertEqual(orphaned_tables, [])

    def test_parent_build_fails_controlled_when_referenced_html_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_dir = workspace / "input"
            input_dir.mkdir()
            output_path = workspace / "parents.jsonl"
            (input_dir / "norma.md").write_text("Artículo 1. Tabla.\n<!-- TABLE_0 -->\n", encoding="utf-8")
            stderr = io.StringIO()

            with patch(
                "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
                return_value=10,
            ), patch("pipeline.chunking.core.cli.DEFAULT_CLEANED_MARKDOWN_DIR", input_dir), patch(
                "pipeline.chunking.core.cli.DEFAULT_PARENT_CHUNKS_PATH", output_path
            ), patch(
                "pipeline.chunking.core.cli.DEFAULT_SOURCE_MANIFEST_PATH", workspace / "missing_manifest.json"
            ), patch("pipeline.chunking.core.cli.DEFAULT_TABLES_ROOT", workspace / "tables"), redirect_stderr(stderr):
                exit_code = main(["build-parents"])

            self.assertEqual(exit_code, 2)
            self.assertFalse(output_path.exists())
            self.assertIn("error: Chunk references missing table file:", stderr.getvalue())
            self.assertIn("norma/table_0.html", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_audit_cli_exits_non_zero_on_missing_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            chunks_path = workspace / "chunks.jsonl"
            write_jsonl_records(chunks_path, [chunk_record_with_tables("norma", 2)])
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch("pipeline.chunking.core.cli.DEFAULT_PARENT_CHUNKS_PATH", chunks_path), patch(
                "pipeline.chunking.core.cli.DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH", workspace / "missing.jsonl"
            ), patch("pipeline.chunking.core.cli.DEFAULT_TABLES_ROOT", workspace / "tables"), redirect_stdout(
                stdout
            ), redirect_stderr(stderr):
                exit_code = main(["audit-table-references"])

            self.assertEqual(exit_code, 2)
            self.assertIn("Missing referenced table files:", stderr.getvalue())
            self.assertIn("norma/table_2.html", stderr.getvalue())

    def test_removed_audit_cli_flags_are_rejected_by_argparse(self) -> None:
        removed_flags = [
            ["--chunks-path", "chunks.jsonl"],
            ["--tables-root", "tables"],
        ]

        for flag_args in removed_flags:
            with self.subTest(flag_args=flag_args):
                stderr = io.StringIO()
                with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
                    main(["audit-table-references", *flag_args])

                self.assertEqual(context.exception.code, 2)
                self.assertIn("unrecognized arguments", stderr.getvalue())

    def test_audit_cli_exits_zero_and_warns_on_orphaned_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            chunks_path = workspace / "chunks.jsonl"
            tables_root = workspace / "tables"
            referenced_path = tables_root / "norma" / "table_0.html"
            orphaned_path = tables_root / "norma" / "table_1.html"
            referenced_path.parent.mkdir(parents=True)
            referenced_path.write_text("<table></table>", encoding="utf-8")
            orphaned_path.write_text("<table></table>", encoding="utf-8")
            write_jsonl_records(chunks_path, [chunk_record_with_tables("norma", 0)])
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch("pipeline.chunking.core.cli.DEFAULT_PARENT_CHUNKS_PATH", chunks_path), patch(
                "pipeline.chunking.core.cli.DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH", workspace / "missing.jsonl"
            ), patch("pipeline.chunking.core.cli.DEFAULT_TABLES_ROOT", tables_root), redirect_stdout(stdout), redirect_stderr(
                stderr
            ):
                exit_code = main(["audit-table-references"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Audited 1 chunks", stdout.getvalue())
            self.assertIn("Warning: extracted table files not referenced by provided chunks:", stderr.getvalue())
            self.assertIn("norma/table_1.html", stderr.getvalue())


def chunk_record_with_tables(source_stem: str, table_index: int) -> dict:
    return {
        "metadata": {
            "chunk": {
                "tables": [
                    {
                        "placeholder": f"<!-- TABLE_{table_index} -->",
                        "table_index": table_index,
                        "source_stem": source_stem,
                    }
                ]
            }
        }
    }


def write_jsonl_records(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
