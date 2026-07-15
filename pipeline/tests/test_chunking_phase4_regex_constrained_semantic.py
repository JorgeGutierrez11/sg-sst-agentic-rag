"""Contract tests for regex-constrained semantic child chunking."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pipeline.chunking.core.cli import build_parser, main
from pipeline.chunking.core.io_jsonl import write_parent_chunks
from pipeline.chunking.hierarchical_splitter.models import ParentChunk


class ChunkingPhase4RegexConstrainedSemanticTest(unittest.TestCase):
    """Verify source-preserving semantic chunking without loading real embeddings."""

    def test_parser_exposes_build_regex_constrained_semantic_help(self) -> None:
        parser = build_parser()

        self.assertIn("build-regex-constrained-semantic", parser.format_help())

    def test_command_writes_regex_constrained_semantic_child_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = build_fixture(Path(temp_dir), make_parent_chunk())
            records = read_records(output_path)

            self.assertEqual(len(records), 3)
            self.assertEqual(records[0]["metadata"]["chunk"]["strategy"], "regex_constrained_semantic")

            self.assertEqual(records[0]["metadata"]["chunk"]["backend"], "custom_regex_constrained_semantic")


    def test_all_emitted_offsets_are_resolved_and_match_parent_slices(self) -> None:
        parent = make_parent_chunk()
        with tempfile.TemporaryDirectory() as temp_dir:
            records = read_records(build_fixture(Path(temp_dir), parent))

        for child in records:
            self.assertIsNotNone(child["start_char"])
            self.assertIsNotNone(child["end_char"])
            relative_start = child["start_char"] - parent.start_char
            relative_end = child["end_char"] - parent.start_char
            self.assertEqual(parent.text[relative_start:relative_end], child["text"])
            self.assertEqual(child["metadata"]["chunk"]["offset_status"], "resolved")

    def test_offsets_stay_monotonic_with_repeated_text(self) -> None:
        repeated = "Artículo 1. Texto repetido.\n\nArtículo 1. Texto repetido.\n\nArtículo 1. Texto repetido."
        parent = make_parent_chunk(text=repeated)
        with tempfile.TemporaryDirectory() as temp_dir:
            records = read_records(build_fixture(Path(temp_dir), parent))

        starts = [record["start_char"] for record in records]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual(len(set(starts)), len(starts))

    def test_metadata_includes_unit_count_and_size_adjustment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            chunk_metadata = read_records(build_fixture(Path(temp_dir), make_parent_chunk()))[0]["metadata"]["chunk"]

        self.assertEqual(chunk_metadata["strategy"], "regex_constrained_semantic")
        self.assertEqual(chunk_metadata["backend"], "custom_regex_constrained_semantic")
        self.assertEqual(chunk_metadata["offset_status"], "resolved")
        self.assertEqual(chunk_metadata["unit_count"], 1)
        self.assertEqual(chunk_metadata["unit_types"], ["paragraph"])
        self.assertEqual(chunk_metadata["size_adjustment"], "none")

    def test_min_chunk_merge_behavior(self) -> None:
        parent = make_parent_chunk(text="Uno corto.\n\nDos corto.\n\nTres corto.")
        with tempfile.TemporaryDirectory() as temp_dir:
            records = read_records(build_fixture(Path(temp_dir), parent, min_tokens=5, max_tokens=30))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["metadata"]["chunk"]["size_adjustment"], "merged_small_chunk")
        self.assertIn("Uno corto", records[0]["text"])
        self.assertIn("Dos corto", records[0]["text"])
        self.assertIn("Tres corto", records[0]["text"])

    def test_oversized_chunk_split_fallback_behavior(self) -> None:
        parent = make_parent_chunk(text=" ".join(f"palabra{i}" for i in range(18)))
        with tempfile.TemporaryDirectory() as temp_dir:
            records = read_records(build_fixture(Path(temp_dir), parent, min_tokens=1, max_tokens=5))

        self.assertGreater(len(records), 1)
        for record in records:
            self.assertLessEqual(record["token_count"], 5)
            self.assertEqual(record["metadata"]["chunk"]["size_adjustment"], "split_oversized_chunk")

    def test_invalid_options_produce_controlled_cli_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "build-regex-constrained-semantic",
                    "--breakpoint-threshold-type",
                    "unknown",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("error: --breakpoint-threshold-type must be one of", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


def build_fixture(workspace: Path, parent: ParentChunk, min_tokens: int = 1, max_tokens: int = 80) -> Path:
    input_path = workspace / "parents.jsonl"
    output_path = workspace / "regex_constrained_semantic" / "chunks.jsonl"
    write_parent_chunks([parent], input_path)
    with patch_embedding_backend(), patch_tokenizer(), redirect_stdout(io.StringIO()):
        exit_code = main(
            [
                "build-regex-constrained-semantic",
                "--input-path",
                str(input_path),
                "--output-path",
                str(output_path),
                "--breakpoint-threshold-type",
                "percentile",
                "--breakpoint-threshold-amount",
                "0",
                "--min-tokens",
                str(min_tokens),
                "--max-tokens",
                str(max_tokens),
            ]
        )
    if exit_code != 0:
        raise AssertionError(f"Fixture build failed with exit code {exit_code}")
    return output_path


def patch_embedding_backend():
    return patch(
        "pipeline.chunking.hierarchical_splitter.child_splitter.regex_constrained_semantic.create_embedding_backend",
        return_value=FakeEmbeddings(),
    )


def patch_tokenizer():
    return patch(
        "pipeline.chunking.hierarchical_splitter.tokenization.get_tokenizer",
        return_value=FakeTokenizer(),
    )


class FakeEmbeddings:
    """Small embedding test double with alternating vector directions."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = [[1.0, 0.0], [0.0, 1.0]]
        return [vectors[index % 2] for index, _text in enumerate(texts)]


class FakeTokenizer:
    """Whitespace tokenizer test double with offset mapping support."""

    is_fast = True

    def encode(self, text: str, add_special_tokens: bool = False) -> list[str]:
        return [text[start:end] for start, end in token_spans(text)]

    def __call__(self, text: str, add_special_tokens: bool = False, return_offsets_mapping: bool = False) -> dict:
        if not return_offsets_mapping:
            return {}
        return {"offset_mapping": token_spans(text)}


def token_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for index, character in enumerate(text):
        if character.isspace():
            if start is not None:
                spans.append((start, index))
                start = None
        elif start is None:
            start = index
    if start is not None:
        spans.append((start, len(text)))
    return spans


def make_parent_chunk(text: str | None = None) -> ParentChunk:
    """Create one representative parent chunk for Phase 4 tests."""

    parent_text = text or (
        "Artículo 1. El empleador identifica peligros.\n\n"
        "Debe conservar evidencias verificables.\n\n"
        "El responsable revisa acciones correctivas."
    )
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
