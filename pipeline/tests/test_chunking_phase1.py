"""Contract tests for Phase 1 chunking commands."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from pipeline.chunking.core.cli import build_parser, main


class ChunkingPhase1CLITest(unittest.TestCase):
    """Verify behavior-preserving Phase 1 chunking contracts."""

    def test_parser_exposes_phase_one_subcommands(self) -> None:
        parser = build_parser()
        help_text = parser.format_help()

        self.assertIn("build-parents", help_text)
        self.assertNotIn("--strategy", help_text)

    def test_build_parents_writes_jsonl_and_skips_empty_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_dir = workspace / "input"
            input_dir.mkdir()
            output_path = workspace / "chunks" / "parents.jsonl"
            (input_dir / "norma.md").write_text(
                "# Norma\n\nArtículo 1. Objeto.\nTexto inicial.\n\nArtículo 2. Alcance.\nTexto final.\n",
                encoding="utf-8",
            )
            (input_dir / "plain.md").write_text("Documento sin frontera de artículo.\nTexto único.\n", encoding="utf-8")
            (input_dir / "empty.md").write_text("   \n\t", encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "build-parents",
                        "--input-dir",
                        str(input_dir),
                        "--output-path",
                        str(output_path),
                        "--manifest-path",
                        str(workspace / "missing_manifest.json"),
                    ]
                )

            records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(exit_code, 0)
            self.assertIn("Built 3 parent chunks from 3 sources", stdout.getvalue())
            self.assertEqual(len(records), 3)
            self.assertTrue(all(record["text"].strip() for record in records))
            split_reasons = [record["metadata"]["chunk"]["split_reason"] for record in records]
            self.assertEqual(split_reasons.count("article_boundary"), 2)
            self.assertEqual(split_reasons.count("no_article_boundary_found"), 1)

    def test_malformed_manifest_returns_controlled_cli_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_dir = workspace / "input"
            input_dir.mkdir()
            manifest_path = workspace / "source_manifest.json"
            (input_dir / "norma.md").write_text("Artículo 1. Texto.\n", encoding="utf-8")
            manifest_path.write_text("{not-json", encoding="utf-8")

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "build-parents",
                        "--input-dir",
                        str(input_dir),
                        "--output-path",
                        str(workspace / "parents.jsonl"),
                        "--manifest-path",
                        str(manifest_path),
                    ]
                )

            self.assertEqual(exit_code, 2)
            self.assertIn("error: Source manifest is not valid JSON", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_build_parents_splits_inline_bold_articles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_dir = workspace / "input"
            input_dir.mkdir()
            output_path = workspace / "parents.jsonl"
            (input_dir / "decreto.md").write_text(
                "**Artículo 1. Objeto.** Texto inicial.  **Artículo 2. Campo de aplicación.** Texto final.\n",
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "build-parents",
                        "--input-dir",
                        str(input_dir),
                        "--output-path",
                        str(output_path),
                        "--manifest-path",
                        str(workspace / "missing_manifest.json"),
                    ]
                )

            self.assertEqual(exit_code, 0)
            records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 2)
            self.assertTrue(records[0]["text"].startswith("**Artículo 1."))
            self.assertTrue(records[1]["text"].startswith("**Artículo 2."))


if __name__ == "__main__":
    unittest.main()
