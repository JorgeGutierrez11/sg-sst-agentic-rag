"""Smoke tests for the table processing CLI entrypoint."""

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from pipeline.tables import main as tables_main


class TablesMainTest(unittest.TestCase):
    """Verify table commands are directly available from pipeline.tables.main."""

    def test_parser_exposes_table_commands(self) -> None:
        parser = tables_main.build_parser()

        command_actions = [action for action in parser._actions if action.dest == "command"]
        self.assertEqual(len(command_actions), 1)
        self.assertEqual(
            set(command_actions[0].choices),
            {"audit-table-references", "build-table-markdown", "build-table-documents"},
        )

    def test_main_runs_audit_table_references_command(self) -> None:
        stdout = io.StringIO()

        with patch("pipeline.tables.main.read_jsonl", side_effect=[[], []]) as read_jsonl, patch(
            "pipeline.tables.main.audit_table_references",
            return_value=([], []),
        ) as audit_table_references, redirect_stdout(stdout):
            exit_code = tables_main.main(["audit-table-references"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(read_jsonl.call_count, 2)
        audit_table_references.assert_called_once()
        self.assertIn("Audited 0 chunks", stdout.getvalue())

    def test_main_runs_build_table_markdown_command(self) -> None:
        stdout = io.StringIO()
        converted_path = Path("data/processed/tables_markdown/norma/table_0.md")

        with patch(
            "pipeline.tables.main.convert_table_html_batch",
            Mock(return_value=[converted_path]),
        ) as convert_table_html_batch, redirect_stdout(stdout):
            exit_code = tables_main.main(["build-table-markdown"])

        self.assertEqual(exit_code, 0)
        convert_table_html_batch.assert_called_once()
        self.assertIn("Converted 1 table HTML file(s) to Markdown:", stdout.getvalue())

    def test_main_runs_build_table_documents_command(self) -> None:
        stdout = io.StringIO()

        with patch("pipeline.tables.main.write_table_documents", Mock(return_value=1)) as write_table_documents, redirect_stdout(
            stdout
        ):
            exit_code = tables_main.main(["build-table-documents"])

        self.assertEqual(exit_code, 0)
        write_table_documents.assert_called_once()
        self.assertIn("Built 1 table document(s):", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
