"""Tests for vector-ready table documents built from extracted HTML tables."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pipeline.chunking.core.cli import main
from pipeline.tables.table_documents import (
    MAX_TABLE_DOCUMENT_CHARS,
    build_table_documents,
    table_document_id,
    table_rows_from_html,
    write_table_documents,
)


class TableDocumentsTest(unittest.TestCase):
    """Verify logical table document generation without raw HTML or physical metadata paths."""

    def test_small_html_table_produces_one_part(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_root, _html_root = self.write_table_sources(
                Path(temp_dir),
                "Resolución 0312 de 2019",
                0,
                markdown="fallback must not be used",
                html="""
                <table>
                  <tr><th>Standard</th><th>Item</th></tr>
                  <tr><td>A</td><td>B</td></tr>
                </table>
                """,
            )

            documents = build_table_documents(markdown_root)

            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0]["id"], "table-resolucion-0312-de-2019-0-part-0000")
            self.assertIn("| Standard | Item |", documents[0]["text"])
            self.assertIn("|---|---|", documents[0]["text"])
            self.assertIn("| A | B |", documents[0]["text"])
            self.assert_table_part_metadata(documents[0], part_index=0, part_count=1, oversized_row=False)

    def test_large_html_table_produces_multiple_parts_with_repeated_header_and_separator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = "\n".join(f"<tr><td>Requirement {index}</td><td>{'x' * 1500}</td></tr>" for index in range(6))
            markdown_root, _html_root = self.write_table_sources(
                Path(temp_dir),
                "Decreto 768 de 2022",
                0,
                markdown="fallback must not be used",
                html=f"<table><tr><th>Requirement</th><th>Description</th></tr>{rows}</table>",
            )

            documents = build_table_documents(markdown_root)

            self.assertGreater(len(documents), 1)
            self.assertEqual(documents[0]["id"], "table-decreto-768-de-2022-0-part-0000")
            self.assertEqual(documents[1]["id"], "table-decreto-768-de-2022-0-part-0001")
            for index, document in enumerate(documents):
                self.assertIn("| Requirement | Description |", document["text"])
                self.assertIn("|---|---|", document["text"])
                self.assertLessEqual(len(document["text"]), MAX_TABLE_DOCUMENT_CHARS)
                self.assert_table_part_metadata(
                    document,
                    part_index=index,
                    part_count=len(documents),
                    oversized_row=False,
                )

    def test_context_rows_before_widest_row_are_repeated_without_th_cells(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = "\n".join(f"<tr><td>Criterion {index}</td><td>{'x' * 1500}</td></tr>" for index in range(6))
            markdown_root, _html_root = self.write_table_sources(
                Path(temp_dir),
                "Resolución 0312 de 2019",
                4,
                markdown="fallback must not be used",
                html=f"""
                <table>
                  <tr><td>Minimum standards table</td></tr>
                  <tr><td>Applies to risk level I companies</td></tr>
                  <tr><td>Criterion</td><td>Description</td></tr>
                  {rows}
                </table>
                """,
            )

            documents = build_table_documents(markdown_root)

            self.assertGreater(len(documents), 1)
            for document in documents:
                self.assertIn("| Minimum standards table |  |", document["text"])
                self.assertIn("| Applies to risk level I companies |  |", document["text"])
                self.assertIn("| Criterion | Description |", document["text"])
                self.assertIn("|---|---|", document["text"])

    def test_rowspan_html_table_stays_in_one_unsplit_part(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = "\n".join(
                f"<tr><td>Standard {index}</td><td>{'x' * 1500}</td></tr>" for index in range(1, 6)
            )
            markdown_root, _html_root = self.write_table_sources(
                Path(temp_dir),
                "Resolución 0312 de 2019",
                4,
                markdown="fallback must not be used",
                html=f"""
                <table>
                  <tr><th>Cycle</th><th>Standard</th><th>Description</th></tr>
                  <tr><td rowspan="3">Planear</td><td>Standard 0</td><td>{'x' * 1500}</td></tr>
                  {rows}
                </table>
                """,
            )

            documents = build_table_documents(markdown_root)

            self.assertEqual(len(documents), 1)
            self.assert_table_part_metadata(documents[0], part_index=0, part_count=1, oversized_row=False)
            self.assertIn("| Cycle | Standard | Description |", documents[0]["text"])
            self.assertIn("Planear", documents[0]["text"])
            self.assertIn("Standard 0", documents[0]["text"])
            self.assertIn("Standard 5", documents[0]["text"])
            self.assertGreater(len(documents[0]["text"]), MAX_TABLE_DOCUMENT_CHARS)

    def test_metadata_is_logical_only_without_paths_or_raw_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_root, _html_root = self.write_table_sources(
                Path(temp_dir),
                "norma",
                2,
                markdown="fallback",
                html="<table><tr><td>A</td></tr></table>",
            )

            document = build_table_documents(markdown_root)[0]
            metadata = document["metadata"]

            self.assertNotIn("path", metadata)
            self.assertNotIn("markdown_path", metadata)
            self.assertNotIn("html_path", metadata)
            self.assertNotIn("source_path", metadata)
            self.assertNotIn("html", metadata)
            self.assertNotIn("<table", document["text"])

    def test_id_is_stable_safe_and_uses_uniform_part_suffix(self) -> None:
        first_id = table_document_id("Resolución 0312 de 2019", 12)
        second_id = table_document_id("Resolución 0312 de 2019", 12, 1)

        self.assertEqual(first_id, "table-resolucion-0312-de-2019-12-part-0000")
        self.assertEqual(second_id, "table-resolucion-0312-de-2019-12-part-0001")
        self.assertNotIn(" ", first_id)
        self.assertNotIn("ó", first_id)

    def test_oversized_row_is_allowed_and_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            oversized_text = "x" * (MAX_TABLE_DOCUMENT_CHARS + 100)
            markdown_root, _html_root = self.write_table_sources(
                Path(temp_dir),
                "norma",
                0,
                markdown="fallback must not be used",
                html=f"<table><tr><th>A</th></tr><tr><td>{oversized_text}</td></tr></table>",
            )

            document = build_table_documents(markdown_root)[0]

            self.assertGreater(len(document["text"]), MAX_TABLE_DOCUMENT_CHARS)
            self.assertEqual(document["metadata"]["oversized_row"], True)

    def test_html_parser_preserves_rows_and_cells_in_order(self) -> None:
        rows = table_rows_from_html(
            """
            <table>
              <tr><th>First</th><th>Second</th></tr>
              <tr><td>One</td><td>Two <strong>Three</strong></td></tr>
            </table>
            """
        )

        self.assertEqual(rows, [["First", "Second"], ["One", "Two Three"]])

    def test_html_parser_expands_colspan_cells_for_header_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown_root, _html_root = self.write_table_sources(
                Path(temp_dir),
                "Resolución 0312 de 2019",
                3,
                markdown="fallback must not be used",
                html="""
                <table>
                  <tr><th colspan="2">FASE</th><th>ACTIVIDAD</th><th>RESPONSABLE</th></tr>
                  <tr><td>Planear</td><td>Hacer</td><td>Capacitación</td><td>Empleador</td></tr>
                </table>
                """,
            )

            document = build_table_documents(markdown_root)[0]

            self.assertIn("| FASE | FASE | ACTIVIDAD | RESPONSABLE |", document["text"])
            self.assertIn("| Planear | Hacer | Capacitación | Empleador |", document["text"])
            self.assertNotIn("| FASE | ACTIVIDAD | RESPONSABLE |  |", document["text"])

    def test_invalid_html_uses_bounded_markdown_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown = "\n".join(f"line {index} {'x' * 1500}" for index in range(6))
            markdown_root, _html_root = self.write_table_sources(
                Path(temp_dir),
                "norma",
                0,
                markdown=markdown,
                html="<table><tr></tr></table>",
            )

            documents = build_table_documents(markdown_root)

            self.assertGreater(len(documents), 1)
            for document in documents:
                self.assertLessEqual(len(document["text"]), MAX_TABLE_DOCUMENT_CHARS)
                self.assertEqual(document["metadata"]["table_part_count"], len(documents))

    def test_cli_writes_expected_jsonl_from_markdown_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            markdown_root, _html_root = self.write_table_sources(
                workspace,
                "Resolución 0312 de 2019",
                1,
                markdown="fallback must not be used",
                html="<table><tr><th>Criterion</th></tr><tr><td>Value</td></tr></table>",
            )
            output_path = workspace / "processed" / "table_documents.jsonl"
            stdout = io.StringIO()

            with patch("pipeline.chunking.core.cli.DEFAULT_TABLE_MARKDOWN_ROOT", markdown_root), patch(
                "pipeline.chunking.core.cli.DEFAULT_TABLE_DOCUMENTS_PATH", output_path
            ), redirect_stdout(stdout):
                exit_code = main(["build-table-documents"])

            records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(exit_code, 0)
            self.assertIn("Built 1 table document(s):", stdout.getvalue())
            self.assertEqual(records[0]["id"], "table-resolucion-0312-de-2019-1-part-0000")
            self.assertEqual(records[0]["metadata"]["linked_placeholder"], "<!-- TABLE_1 -->")

    def test_removed_table_documents_cli_flags_are_rejected_by_argparse(self) -> None:
        removed_flags = [
            ["--markdown-root", "tables_markdown"],
            ["--output-path", "table_documents.jsonl"],
        ]

        for flag_args in removed_flags:
            with self.subTest(flag_args=flag_args):
                stderr = io.StringIO()
                with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
                    main(["build-table-documents", *flag_args])

                self.assertEqual(context.exception.code, 2)
                self.assertIn("unrecognized arguments", stderr.getvalue())

    def test_write_table_documents_returns_flattened_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            rows = "\n".join(f"<tr><td>{index}</td><td>{'x' * 1500}</td></tr>" for index in range(6))
            markdown_root, _html_root = self.write_table_sources(
                workspace,
                "norma",
                0,
                markdown="fallback must not be used",
                html=f"<table><tr><th>A</th><th>B</th></tr>{rows}</table>",
            )
            output_path = workspace / "documents.jsonl"

            count = write_table_documents(markdown_root, output_path)

            self.assertGreater(count, 1)
            self.assertEqual(count, len(output_path.read_text(encoding="utf-8").splitlines()))

    def assert_table_part_metadata(
        self,
        document: dict[str, object],
        part_index: int,
        part_count: int,
        oversized_row: bool,
    ) -> None:
        metadata = document["metadata"]
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata["type"], "table")
        self.assertEqual(metadata["table_part_index"], part_index)
        self.assertEqual(metadata["table_part_count"], part_count)
        self.assertEqual(metadata["table_key"], f"{metadata['source_stem']}:{metadata['table_index']}")
        self.assertEqual(metadata["oversized_row"], oversized_row)

    def write_table_sources(
        self,
        workspace: Path,
        source_stem: str,
        table_index: int,
        markdown: str,
        html: str,
    ) -> tuple[Path, Path]:
        markdown_root = workspace / "tables_markdown"
        html_root = workspace / "tables"
        markdown_path = markdown_root / source_stem / f"table_{table_index}.md"
        html_path = html_root / source_stem / f"table_{table_index}.html"
        markdown_path.parent.mkdir(parents=True)
        html_path.parent.mkdir(parents=True)
        markdown_path.write_text(markdown, encoding="utf-8")
        html_path.write_text(html, encoding="utf-8")
        return markdown_root, html_root


if __name__ == "__main__":
    unittest.main()
