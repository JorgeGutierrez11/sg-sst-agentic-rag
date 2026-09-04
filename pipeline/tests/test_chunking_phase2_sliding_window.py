"""Contract tests for Phase 2 sliding-window child chunking."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pipeline.chunking.cli import build_parser, main
from pipeline.chunking.io_jsonl import write_parent_chunks
from pipeline.chunking.hierarchical_splitter.child_splitter.shared import build_child_chunk, child_offsets
from pipeline.chunking.hierarchical_splitter.child_splitter.sliding_window import write_sliding_window_child_output
from pipeline.chunking.hierarchical_splitter.models import ParentChunk


class ChunkingPhase2SlidingWindowTest(unittest.TestCase):
    """Verify the sliding-window child chunking baseline."""

    def test_build_sliding_window_reads_parent_and_writes_children(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_path = workspace / "parents.jsonl"
            output_path = workspace / "sliding_window" / "chunks.jsonl"
            parent = make_parent_chunk(
                text=(
                    "Artículo 1. El empleador debe identificar peligros, evaluar riesgos y documentar controles. "
                    "La mejora continua debe conservar evidencias verificables para auditoría y seguimiento. "
                    "El responsable del SG-SST revisa acciones preventivas y correctivas periódicamente."
                )
            )
            write_parent_chunks([parent], input_path)

            with patch("pipeline.chunking.cli.DEFAULT_PARENT_CHUNKS_PATH", input_path), patch(
                "pipeline.chunking.cli.DEFAULT_SLIDING_WINDOW_CHUNKS_PATH", output_path
            ), redirect_stdout(io.StringIO()):
                exit_code = main(["build-sliding-window"])

            records = read_records(output_path)
            self.assertEqual(exit_code, 0)
            self.assertGreaterEqual(len(records), 1)
            self.assertEqual(records[0]["metadata"]["chunk"]["strategy"], "sliding_window")
            self.assertEqual(
                records[0]["metadata"]["chunk"]["backend"],
                "langchain_recursive_character_text_splitter",
            )

    def test_child_keeps_parent_source_traceability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = build_one_parent_fixture(Path(temp_dir))
            child = read_records(output_path)[0]

            self.assertEqual(child["parent_id"], "parent-decreto-0001")
            self.assertEqual(child["source_document_id"], "decreto-1072")
            self.assertTrue(child["text"])
            self.assertGreaterEqual(child["start_char"], 10)
            self.assertGreater(child["end_char"], child["start_char"])
            self.assertGreater(child["token_count"], 0)
            self.assertEqual(child["metadata"]["chunk"]["parent_chunk_id"], "parent-decreto-0001")

    def test_child_preserves_inherited_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = build_one_parent_fixture(Path(temp_dir))
            inherited = read_records(output_path)[0]["metadata"]["inherited"]

        self.assertEqual(inherited["source_name"], "Decreto 1072 de 2015")
        self.assertEqual(inherited["hierarchy"]["article"], "2.2.4.6.8")

    def test_child_with_table_placeholder_gets_minimal_table_metadata(self) -> None:
        with patch_child_token_count():
            child = build_child_chunk(
                parent=make_parent_chunk(text="Texto previo. <!-- TABLE_0 --> Texto posterior."),
                text="<!-- TABLE_0 -->",
                chunk_index=0,
                relative_start=14,
                chunk_metadata={"strategy": "test_child"},
            )

        self.assertEqual(
            child.metadata["chunk"]["tables"],
            [
                {
                    "placeholder": "<!-- TABLE_0 -->",
                    "table_index": 0,
                    "source_stem": "decreto_1072",
                }
            ],
        )

    def test_child_without_placeholder_does_not_inherit_parent_table_metadata(self) -> None:
        parent = make_parent_chunk(text="Texto con <!-- TABLE_0 --> y otro child sin tabla.")
        parent.metadata["chunk"]["tables"] = [
            {
                "placeholder": "<!-- TABLE_0 -->",
                "table_index": 0,
                "source_stem": "decreto_1072",
            }
        ]

        with patch_child_token_count():
            child = build_child_chunk(
                parent=parent,
                text="otro child sin tabla.",
                chunk_index=1,
                relative_start=29,
                chunk_metadata={"strategy": "test_child"},
            )

        self.assertNotIn("tables", child.metadata["chunk"])

    def test_child_table_metadata_uses_parent_inherited_source_stem(self) -> None:
        parent = make_parent_chunk(text="Texto <!-- TABLE_3 -->.")
        parent.metadata["inherited"]["source_stem"] = "Resolución 0312 de 2019"

        with patch_child_token_count():
            child = build_child_chunk(
                parent=parent,
                text="<!-- TABLE_3 -->",
                chunk_index=0,
                relative_start=6,
                chunk_metadata={"strategy": "test_child"},
            )

        self.assertEqual(child.metadata["chunk"]["tables"][0]["source_stem"], "Resolución 0312 de 2019")

    def test_children_offsets_stay_within_parent_and_match_exact_substrings(self) -> None:
        parent = make_parent_chunk(
            text=(
                "Artículo 1. El empleador debe identificar peligros, evaluar riesgos y documentar controles. "
                "Artículo 1. El empleador debe identificar peligros, evaluar riesgos y documentar controles. "
                "Las evidencias verificables deben conservarse para auditoría y seguimiento."
            )
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = build_parent_fixture(Path(temp_dir), parent)

            previous_start = parent.start_char - 1
            for child in read_records(output_path):
                start_char = child["start_char"]
                end_char = child["end_char"]
                self.assertGreaterEqual(start_char, parent.start_char)
                self.assertGreater(start_char, previous_start)
                self.assertLessEqual(end_char, parent.end_char)
                relative_start = start_char - parent.start_char
                relative_end = end_char - parent.start_char
                self.assertEqual(parent.text[relative_start:relative_end], child["text"])
                previous_start = start_char

    def test_child_offsets_returns_unresolved_when_text_does_not_match(self) -> None:
        parent = make_parent_chunk(text="Artículo 1. Texto normativo verificable.")

        self.assertEqual(child_offsets(parent, "texto ausente", 0), (None, None))

    def test_removed_chunk_size_flag_is_rejected_by_argparse(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
            main(["build-sliding-window", "--chunk-size", "10"])

        self.assertEqual(context.exception.code, 2)
        self.assertIn("unrecognized arguments: --chunk-size 10", stderr.getvalue())

    def test_parser_exposes_build_sliding_window_help(self) -> None:
        parser = build_parser()
        help_text = parser.format_help()

        self.assertIn("build-sliding-window", help_text)

    def test_malformed_parent_jsonl_rejected_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_path = workspace / "parents.jsonl"
            output_path = workspace / "chunks.jsonl"
            input_path.write_text('{"chunk_id": "missing-required-fields"}\n', encoding="utf-8")
            stderr = io.StringIO()

            with patch("pipeline.chunking.cli.DEFAULT_PARENT_CHUNKS_PATH", input_path), patch(
                "pipeline.chunking.cli.DEFAULT_SLIDING_WINDOW_CHUNKS_PATH", output_path
            ), redirect_stderr(stderr):
                exit_code = main(["build-sliding-window"])

            self.assertEqual(exit_code, 2)
            self.assertIn("error: Invalid parent chunk record", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_sliding_window_output_validates_child_table_references_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_path = workspace / "parents.jsonl"
            output_path = workspace / "chunks.jsonl"
            parent = make_parent_chunk(text="Texto previo. <!-- TABLE_0 --> Texto posterior.")
            write_parent_chunks([parent], input_path)

            with patch_child_token_count():
                child = build_child_chunk(
                    parent=parent,
                    text="<!-- TABLE_0 -->",
                    chunk_index=0,
                    relative_start=14,
                    chunk_metadata={"strategy": "sliding_window"},
                )

            with patch(
                "pipeline.chunking.hierarchical_splitter.child_splitter.sliding_window.build_sliding_window_child_chunks",
                return_value=[child],
            ):
                with self.assertRaisesRegex(ValueError, "Chunk references missing table file: .*table_0.html"):
                    write_sliding_window_child_output(input_path, output_path, 32, 8, tables_root=workspace / "tables")

            self.assertFalse(output_path.exists())


def build_one_parent_fixture(workspace: Path) -> Path:
    return build_parent_fixture(workspace, make_parent_chunk())


def patch_child_token_count():
    return patch("pipeline.chunking.hierarchical_splitter.child_splitter.shared.estimate_token_count", return_value=3)


def build_parent_fixture(workspace: Path, parent: ParentChunk) -> Path:
    input_path = workspace / "parents.jsonl"
    output_path = workspace / "chunks.jsonl"
    write_parent_chunks([parent], input_path)
    with patch("pipeline.chunking.cli.DEFAULT_PARENT_CHUNKS_PATH", input_path), patch(
        "pipeline.chunking.cli.DEFAULT_SLIDING_WINDOW_CHUNKS_PATH", output_path
    ), redirect_stdout(io.StringIO()):
        exit_code = main(["build-sliding-window"])
    if exit_code != 0:
        raise AssertionError(f"Fixture build failed with exit code {exit_code}")
    return output_path


def make_parent_chunk(text: str | None = None) -> ParentChunk:
    """Create one representative parent chunk for Phase 2 tests."""

    parent_text = text or "Artículo 1. Texto normativo con obligaciones verificables para una empresa de riesgo I."
    return ParentChunk(
        chunk_id="parent-decreto-0001",
        source_document_id="decreto-1072",
        source_path="data/processed/decreto_1072.md",
        parent_index=0,
        text=parent_text,
        start_char=10,
        end_char=10 + len(parent_text),
        token_count=20,
        metadata={
            "inherited": {
                "source_name": "Decreto 1072 de 2015",
                "source_stem": "decreto_1072",
                "hierarchy": {"article": "2.2.4.6.8"},
            },
            "chunk": {"strategy": "parent_article_boundary"},
        },
    )


def read_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    unittest.main()
