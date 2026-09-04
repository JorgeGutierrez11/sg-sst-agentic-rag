"""Tests for extracted table HTML to Markdown conversion."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pipeline.chunking.cli import main
from pipeline.tables.table_markdown import (
    convert_table_html_batch,
    convert_table_html_to_markdown,
)


class TableMarkdownTest(unittest.TestCase):
    """Verify derived Markdown table conversion without requiring real Pandoc."""

    def test_single_conversion_calls_pypandoc_and_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            html_path = workspace / "tables" / "norma" / "table_0.html"
            markdown_path = workspace / "processed" / "norma" / "table_0.md"
            html_path.parent.mkdir(parents=True)
            html_path.write_text("<table><tr><td>A</td></tr></table>", encoding="utf-8")
            convert_file = Mock(return_value="| A |\n|---|\n")

            with patch.dict("sys.modules", {"pypandoc": SimpleNamespace(convert_file=convert_file)}):
                result_path = convert_table_html_to_markdown(html_path, markdown_path)

            self.assertEqual(result_path, markdown_path)
            convert_file.assert_called_once_with(str(html_path), "markdown")
            self.assertEqual(markdown_path.read_text(encoding="utf-8"), "| A |\n|---|\n")

    def test_batch_conversion_preserves_source_stem_and_table_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tables_root = workspace / "tables"
            output_root = workspace / "processed" / "tables_markdown"
            first_table = tables_root / "Resolución 0312 de 2019" / "table_0.html"
            second_table = tables_root / "Decreto 1072 de 2015" / "table_12.html"
            first_table.parent.mkdir(parents=True)
            second_table.parent.mkdir(parents=True)
            first_table.write_text("<table></table>", encoding="utf-8")
            second_table.write_text("<table></table>", encoding="utf-8")

            with patch.dict(
                "sys.modules",
                {"pypandoc": SimpleNamespace(convert_file=Mock(return_value="| value |\n|---|\n"))},
            ):
                converted_paths = convert_table_html_batch(tables_root, output_root)

            self.assertEqual(
                converted_paths,
                [
                    output_root / "Decreto 1072 de 2015" / "table_12.md",
                    output_root / "Resolución 0312 de 2019" / "table_0.md",
                ],
            )
            self.assertTrue((output_root / "Resolución 0312 de 2019" / "table_0.md").exists())
            self.assertTrue((output_root / "Decreto 1072 de 2015" / "table_12.md").exists())

    def test_cli_reports_success_for_mocked_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tables_root = workspace / "tables"
            output_root = workspace / "processed" / "tables_markdown"
            table_path = tables_root / "norma" / "table_0.html"
            table_path.parent.mkdir(parents=True)
            table_path.write_text("<table></table>", encoding="utf-8")
            stdout = io.StringIO()

            with patch.dict(
                "sys.modules",
                {"pypandoc": SimpleNamespace(convert_file=Mock(return_value="| value |\n|---|\n"))},
            ), patch("pipeline.chunking.cli.DEFAULT_TABLES_ROOT", tables_root), patch(
                "pipeline.chunking.cli.DEFAULT_TABLE_MARKDOWN_ROOT", output_root
            ), redirect_stdout(stdout):
                exit_code = main(["build-table-markdown"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Converted 1 table HTML file(s) to Markdown:", stdout.getvalue())
            self.assertTrue((output_root / "norma" / "table_0.md").exists())

    def test_removed_table_markdown_cli_flags_are_rejected_by_argparse(self) -> None:
        removed_flags = [
            ["--tables-root", "tables"],
            ["--output-root", "tables_markdown"],
        ]

        for flag_args in removed_flags:
            with self.subTest(flag_args=flag_args):
                stderr = io.StringIO()
                with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
                    main(["build-table-markdown", *flag_args])

                self.assertEqual(context.exception.code, 2)
                self.assertIn("unrecognized arguments", stderr.getvalue())

    def test_cli_catches_conversion_failure_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tables_root = workspace / "tables"
            output_root = workspace / "processed" / "tables_markdown"
            table_path = tables_root / "norma" / "table_0.html"
            table_path.parent.mkdir(parents=True)
            table_path.write_text("<table></table>", encoding="utf-8")
            stderr = io.StringIO()

            with patch.dict(
                "sys.modules",
                {"pypandoc": SimpleNamespace(convert_file=Mock(side_effect=OSError("pandoc failed")))},
            ), patch("pipeline.chunking.cli.DEFAULT_TABLES_ROOT", tables_root), patch(
                "pipeline.chunking.cli.DEFAULT_TABLE_MARKDOWN_ROOT", output_root
            ), redirect_stderr(stderr):
                exit_code = main(["build-table-markdown"])

            self.assertEqual(exit_code, 2)
            self.assertIn("error: Failed to convert table HTML to Markdown:", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
