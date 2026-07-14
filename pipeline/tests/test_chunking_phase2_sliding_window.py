"""Contract tests for Phase 2 sliding-window child chunking."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from pipeline.chunking.core.cli import build_parser, main
from pipeline.chunking.core.io_jsonl import write_parent_chunks
from pipeline.chunking.hierarchical_splitter.child_splitter.shared import child_offsets
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

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "build-sliding-window",
                        "--input-path",
                        str(input_path),
                        "--output-path",
                        str(output_path),
                        "--chunk-size",
                        "24",
                        "--chunk-overlap",
                        "6",
                    ]
                )

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

    def test_invalid_overlap_rejected_without_traceback(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["build-sliding-window", "--chunk-size", "10", "--chunk-overlap", "10"])

        self.assertEqual(exit_code, 2)
        self.assertIn("error: --chunk-overlap must be lower than --chunk-size", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_invalid_chunk_size_rejected_without_traceback(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["build-sliding-window", "--chunk-size", "0"])

        self.assertEqual(exit_code, 2)
        self.assertIn("error: --chunk-size must be greater than 0", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

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

            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "build-sliding-window",
                        "--input-path",
                        str(input_path),
                        "--output-path",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 2)
            self.assertIn("error: Invalid parent chunk record", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())


def build_one_parent_fixture(workspace: Path) -> Path:
    return build_parent_fixture(workspace, make_parent_chunk())


def build_parent_fixture(workspace: Path, parent: ParentChunk) -> Path:
    input_path = workspace / "parents.jsonl"
    output_path = workspace / "chunks.jsonl"
    write_parent_chunks([parent], input_path)
    with redirect_stdout(io.StringIO()):
        exit_code = main(
            [
                "build-sliding-window",
                "--input-path",
                str(input_path),
                "--output-path",
                str(output_path),
                "--chunk-size",
                "32",
                "--chunk-overlap",
                "8",
            ]
        )
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
