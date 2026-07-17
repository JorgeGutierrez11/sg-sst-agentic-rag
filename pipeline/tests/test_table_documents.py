"""Tests for vector-ready table documents built from Markdown tables."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from pipeline.chunking.core.cli import main
from pipeline.tables.table_documents import (
    build_table_documents,
    table_document_id,
    write_table_documents,
)


class TableDocumentsTest(unittest.TestCase):
    """Verify logical table document generation without raw HTML or physical metadata paths."""

    def test_one_markdown_table_becomes_one_jsonl_ready_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_root = Path(temp_dir) / "tables_markdown"
            table_path = markdown_root / "Resolución 0312 de 2019" / "table_0.md"
            table_path.parent.mkdir(parents=True)
            table_path.write_text("| Standard | Item |\n|---|---|\n| A | B |\n", encoding="utf-8")

            documents = build_table_documents(markdown_root)

            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0]["text"], "| Standard | Item |\n|---|---|\n| A | B |\n")
            self.assertEqual(
                documents[0]["metadata"],
                {
                    "type": "table",
                    "source_stem": "Resolución 0312 de 2019",
                    "table_index": 0,
                    "linked_placeholder": "<!-- TABLE_0 -->",
                },
            )

    def test_metadata_is_logical_only_without_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_root = Path(temp_dir) / "tables_markdown"
            table_path = markdown_root / "norma" / "table_2.md"
            table_path.parent.mkdir(parents=True)
            table_path.write_text("| A |\n|---|\n", encoding="utf-8")

            metadata = build_table_documents(markdown_root)[0]["metadata"]

            self.assertNotIn("path", metadata)
            self.assertNotIn("markdown_path", metadata)
            self.assertNotIn("html_path", metadata)
            self.assertNotIn("source_path", metadata)

    def test_id_is_stable_safe_and_includes_table_identity(self) -> None:
        first_id = table_document_id("Resolución 0312 de 2019", 12)
        second_id = table_document_id("Resolución 0312 de 2019", 12)

        self.assertEqual(first_id, second_id)
        self.assertEqual(first_id, "table-resolucion-0312-de-2019-12")
        self.assertIn("12", first_id)
        self.assertNotIn(" ", first_id)
        self.assertNotIn("ó", first_id)

    def test_cli_writes_expected_jsonl_from_markdown_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            markdown_root = workspace / "tables_markdown"
            output_path = workspace / "processed" / "table_documents.jsonl"
            table_path = markdown_root / "Resolución 0312 de 2019" / "table_1.md"
            table_path.parent.mkdir(parents=True)
            table_path.write_text("| Criterion |\n|---|\n| Value |\n", encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "build-table-documents",
                        "--markdown-root",
                        str(markdown_root),
                        "--output-path",
                        str(output_path),
                    ]
                )

            records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(exit_code, 0)
            self.assertIn("Built 1 table document(s):", stdout.getvalue())
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["id"], "table-resolucion-0312-de-2019-1")
            self.assertEqual(records[0]["metadata"]["linked_placeholder"], "<!-- TABLE_1 -->")
            self.assertNotIn("html_path", records[0]["metadata"])

    def test_write_table_documents_returns_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            markdown_root = workspace / "tables_markdown"
            output_path = workspace / "documents.jsonl"
            table_path = markdown_root / "norma" / "table_0.md"
            table_path.parent.mkdir(parents=True)
            table_path.write_text("| A |\n|---|\n", encoding="utf-8")

            count = write_table_documents(markdown_root, output_path)

            self.assertEqual(count, 1)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
