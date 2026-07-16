"""Contract tests for Phase 1 chunking commands."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pipeline.chunking.core.cli import build_parser, main
from pipeline.chunking.hierarchical_splitter.parent_builder import (
    build_parent_chunks_for_document,
    discover_markdown_sources,
    stable_parent_chunk_id,
)
from pipeline.chunking.structural_analysis.boundaries import extract_first_boundary_value, iter_boundary_matches
from pipeline.chunking.structural_analysis.metadata_infer import build_source_document


def count_words(text: str) -> int:
    return len(text.split())


def repeated_words(count: int) -> str:
    return " ".join(f"palabra{i}" for i in range(count))


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
                "\n".join(
                    [
                        "# Norma",
                        "",
                        f"Artículo 1. Objeto.\n{repeated_words(260)}",
                        "",
                        f"Artículo 2. Alcance.\n{repeated_words(260)}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (input_dir / "plain.md").write_text("Documento sin frontera de artículo.\nTexto único.\n", encoding="utf-8")
            (input_dir / "empty.md").write_text("   \n\t", encoding="utf-8")

            stdout = io.StringIO()
            with patch(
                "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
                side_effect=count_words,
            ), redirect_stdout(stdout):
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
            self.assertIn("Built 4 parent chunks from 3 sources", stdout.getvalue())
            self.assertEqual(len(records), 4)
            self.assertTrue(all(record["text"].strip() for record in records))
            split_reasons = [record["metadata"]["chunk"]["split_reason"] for record in records]
            self.assertEqual(split_reasons.count("article_boundary"), 2)
            self.assertEqual(split_reasons.count("document_preamble_before_first_article"), 1)
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
            with patch(
                "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
                side_effect=count_words,
            ), redirect_stderr(stderr):
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
                f"**Artículo 1. Objeto.** {repeated_words(260)}  "
                f"**Artículo 2. Campo de aplicación.** {repeated_words(260)}\n",
                encoding="utf-8",
            )

            with patch(
                "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
                side_effect=count_words,
            ), redirect_stdout(io.StringIO()):
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

    def test_quoted_bold_article_boundary_is_detected(self) -> None:
        text = '"**Artículo 2.2.4.6.37.***Transición*. Texto reformado.\n'

        self.assertEqual(extract_first_boundary_value(text, "article"), "2.2.4.6.37")

    def test_inline_article_reference_without_boundary_format_is_not_detected(self) -> None:
        text = "El empleador debe cumplir el Artículo 2 de esta norma y conservar evidencias.\n"

        self.assertIsNone(extract_first_boundary_value(text, "article"))

    def test_literal_boundary_accepts_common_markdown_formats(self) -> None:
        text = "a.) En forma obligatoria:\n**b.** Proponer medidas.\n**c)** Vigilar cumplimiento.\n"

        literals = iter_boundary_matches(text, boundary_types=("literal",))

        self.assertEqual([literal.value for literal in literals], ["a", "b", "c"])

    def test_preamble_before_first_article_is_emitted_with_truthful_metadata(self) -> None:
        text = "  # Decreto\nIntroducción general.\n\nArtículo 1. Objeto.\nTexto completo.\n"
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].text, "# Decreto\nIntroducción general.")
        self.assertEqual(chunks[0].start_char, 2)
        self.assertEqual(chunks[0].end_char, text.index("Artículo") - 2)
        self.assertEqual(chunks[0].metadata["chunk"]["strategy"], "parent_document_preamble")
        self.assertEqual(chunks[0].metadata["chunk"]["split_reason"], "document_preamble_before_first_article")
        self.assertEqual(chunks[0].metadata["chunk"]["section_type"], "preamble")
        self.assertFalse(chunks[0].metadata["chunk"]["indexable"])
        self.assertNotEqual(chunks[0].metadata["chunk"]["strategy"], "parent_whole_document")
        self.assertNotIn("article", chunks[0].metadata["inherited"].get("hierarchy", {}))

    def test_preamble_ending_with_colon_does_not_group_with_first_article(self) -> None:
        text = "# Decreto:\n\nArtículo 1. Objeto.\nTexto completo.\n"
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].text, "# Decreto:")
        self.assertEqual(chunks[0].metadata["chunk"]["strategy"], "parent_document_preamble")
        self.assertTrue(chunks[1].text.startswith("Artículo 1."))

    def test_hidden_path_check_uses_input_relative_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".hidden-parent-") as temp_dir:
            input_dir = Path(temp_dir) / "input"
            input_dir.mkdir()
            visible_source = input_dir / "norma.md"
            hidden_source_dir = input_dir / ".cache"
            hidden_source_dir.mkdir()
            visible_source.write_text("Artículo 1. Texto.\n", encoding="utf-8")
            (hidden_source_dir / "oculta.md").write_text("Artículo 1. Oculta.\n", encoding="utf-8")

            sources = discover_markdown_sources(input_dir)

        self.assertEqual(sources, [visible_source])

    def test_parent_id_digest_is_stable_when_same_text_moves_offsets(self) -> None:
        first_id = stable_parent_chunk_id("doc-1", 0, "Artículo 1. Texto estable.")
        moved_id = stable_parent_chunk_id("doc-1", 0, "Artículo 1. Texto estable.")
        reordered_id = stable_parent_chunk_id("doc-1", 1, "Artículo 1. Texto estable.")

        self.assertEqual(first_id.rsplit("-", 1)[-1], moved_id.rsplit("-", 1)[-1])
        self.assertEqual(first_id.rsplit("-", 1)[-1], reordered_id.rsplit("-", 1)[-1])
        self.assertIn("-0000-", first_id)
        self.assertIn("-0001-", reordered_id)

    def test_small_intro_article_groups_with_next_article_and_keeps_exact_offsets(self) -> None:
        text = (
            "Artículo 1. Modifíquese el artículo 2, el cual quedará así:\n\n"
            "Artículo 2. Texto ajustado.\nContenido completo.\n"
        )
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        self.assertEqual(len(chunks), 1)
        self.assertIn("Artículo 1.", chunks[0].text)
        self.assertIn("Artículo 2.", chunks[0].text)
        self.assertEqual(chunks[0].start_char, 0)
        self.assertEqual(chunks[0].end_char, len(text.strip()))
        self.assertEqual(chunks[0].text, text[chunks[0].start_char : chunks[0].end_char])

    def test_consecutive_small_articles_group_by_size_without_continuation_signal(self) -> None:
        text = "Artículo 1. Objeto.\nTexto completo.\n\nArtículo 2. Alcance.\nTexto completo.\n"
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].text.startswith("Artículo 1."))
        self.assertIn("Artículo 2.", chunks[0].text)

    def test_normal_article_metadata_remains_unchanged(self) -> None:
        text = f"Artículo 1. Objeto.\n{repeated_words(260)}\n\nArtículo 2. Alcance.\n{repeated_words(260)}\n"
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].metadata["inherited"]["hierarchy"]["article"], "1")
        self.assertNotIn("articles", chunks[0].metadata["inherited"]["hierarchy"])

    def test_grouped_parent_adds_article_list_traceability(self) -> None:
        text = "Artículo 1. Introducción:\n\nArtículo 2. Desarrollo.\nTexto completo.\n"
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].metadata["inherited"]["hierarchy"]["article"], "1")
        self.assertEqual(chunks[0].metadata["inherited"]["hierarchy"]["articles"], ["1", "2"])

    def test_grouping_stops_when_next_article_would_exceed_max_tokens(self) -> None:
        text = f"Artículo 1. Objeto:\nTexto corto.\n\nArtículo 2. Alcance.\n{repeated_words(1501)}\n"
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[0].text.startswith("Artículo 1."))
        self.assertNotIn("Artículo 2.", chunks[0].text)

    def test_intro_article_groups_only_with_direct_next_article(self) -> None:
        text = (
            "Artículo 1. El artículo 2 quedará así:\n\n"
            f"Artículo 2. Objeto.\n{repeated_words(1488)}\n\n"
            "Artículo 3. Alcance.\nTexto completo.\n"
        )
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        self.assertEqual(len(chunks), 2)
        self.assertIn("Artículo 1.", chunks[0].text)
        self.assertIn("Artículo 2.", chunks[0].text)
        self.assertNotIn("Artículo 3.", chunks[0].text)

    def test_last_small_article_merges_backward_when_allowed(self) -> None:
        text = f"Artículo 1. Objeto.\n{repeated_words(260)}\n\nArtículo 2. Cierre.\nTexto corto.\n"
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        self.assertEqual(len(chunks), 1)
        self.assertIn("Artículo 1.", chunks[0].text)
        self.assertIn("Artículo 2.", chunks[0].text)
        self.assertEqual(chunks[0].metadata["inherited"]["hierarchy"]["articles"], ["1", "2"])

    def test_last_small_article_does_not_merge_backward_when_combined_exceeds_max(self) -> None:
        text = f"Artículo 1. Objeto.\n{repeated_words(1495)}\n\nArtículo 2. Cierre.\nTexto corto final.\n"
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[0].text.startswith("Artículo 1."))
        self.assertTrue(chunks[1].text.startswith("Artículo 2."))

    def test_grouped_parent_does_not_add_merge_metadata(self) -> None:
        text = "Artículo 1. Introducción:\n\nArtículo 2. Desarrollo.\nTexto completo.\n"
        source_path = Path("norma.md")
        source_document = build_source_document(source_path, text, {})

        with patch(
            "pipeline.chunking.hierarchical_splitter.parent_builder.estimate_token_count",
            side_effect=count_words,
        ):
            chunks = build_parent_chunks_for_document(source_path, text, source_document)

        forbidden_keys = {
            "grouped_parent",
            "grouped_reason",
            "merged",
            "fusion",
            "merge_reason",
            "parent_size_status",
        }
        self.assertEqual(len(chunks), 1)
        self.assertTrue(forbidden_keys.isdisjoint(chunks[0].metadata["chunk"]))
        self.assertTrue(forbidden_keys.isdisjoint(chunks[0].metadata["inherited"]))
        self.assertTrue(forbidden_keys.isdisjoint(chunks[0].metadata["inherited"]["hierarchy"]))


if __name__ == "__main__":
    unittest.main()
