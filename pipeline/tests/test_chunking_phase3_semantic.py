"""Contract tests for Phase 3 semantic child chunking."""

import io
import json
import tempfile
import unittest
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pipeline.chunking.cli import build_parser, main
from pipeline.chunking.config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT,
    DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE,
)
from pipeline.chunking.io_jsonl import write_parent_chunks
from pipeline.chunking.hierarchical_splitter.models import ParentChunk


class ChunkingPhase3SemanticTest(unittest.TestCase):
    """Verify semantic chunking without loading the real embedding model."""

    def test_parser_exposes_build_semantic_help(self) -> None:
        parser = build_parser()
        help_text = parser.format_help()

        self.assertIn("build-semantic", help_text)
        self.assertNotIn("--breakpoint-threshold-type", help_text)

    def test_removed_semantic_input_flag_is_rejected_by_argparse(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
            main(["build-semantic", "--input-path", "parents.jsonl"])

        self.assertEqual(context.exception.code, 2)
        self.assertIn("unrecognized arguments: --input-path parents.jsonl", stderr.getvalue())

    def test_build_semantic_reads_parent_and_writes_children(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = build_one_semantic_fixture(Path(temp_dir))
            records = read_records(output_path)

            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["text"], "Artículo 1. El empleador identifica peligros.")
            self.assertEqual(records[1]["text"], "Debe conservar evidencias verificables.")

    def test_child_keeps_parent_source_traceability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            child = read_records(build_one_semantic_fixture(Path(temp_dir)))[0]

            self.assertEqual(child["parent_id"], "parent-decreto-0001")
            self.assertEqual(child["source_document_id"], "decreto-1072")
            self.assertTrue(child["text"])
            self.assertEqual(child["start_char"], 10)
            self.assertGreater(child["end_char"], child["start_char"])
            self.assertGreater(child["token_count"], 0)
            self.assertEqual(child["metadata"]["chunk"]["parent_chunk_id"], "parent-decreto-0001")

    def test_child_preserves_inherited_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            inherited = read_records(build_one_semantic_fixture(Path(temp_dir)))[0]["metadata"]["inherited"]

            self.assertEqual(inherited["source_name"], "Decreto 1072 de 2015")
            self.assertEqual(inherited["hierarchy"]["article"], "2.2.4.6.8")

    def test_semantic_metadata_includes_backend_model_and_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            chunk_metadata = read_records(build_one_semantic_fixture(Path(temp_dir)))[0]["metadata"]["chunk"]

            self.assertEqual(chunk_metadata["strategy"], "semantic_chunking")
            self.assertEqual(chunk_metadata["backend"], "langchain_semantic_chunker")
            self.assertEqual(chunk_metadata["embedding_model"], DEFAULT_EMBEDDING_MODEL)
            self.assertEqual(chunk_metadata["breakpoint_threshold_type"], DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE)
            self.assertEqual(chunk_metadata["breakpoint_threshold_amount"], DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT)
            self.assertEqual(chunk_metadata["split_reason"], "semantic_breakpoint")
            self.assertEqual(chunk_metadata["offset_status"], "resolved")
            self.assertNotIn("offset_reason", chunk_metadata)

    def test_empty_parent_list_writes_empty_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_path = workspace / "parents.jsonl"
            output_path = workspace / "semantic" / "chunks.jsonl"
            write_parent_chunks([], input_path)

            with semantic_cli_defaults(input_path, output_path), patch_semantic_splitter(), redirect_stdout(io.StringIO()):
                exit_code = main(["build-semantic"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "")

    def test_empty_parent_text_writes_no_children(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_path = workspace / "parents.jsonl"
            output_path = workspace / "semantic" / "chunks.jsonl"
            write_parent_chunks([make_parent_chunk(text="")], input_path)

            with semantic_cli_defaults(input_path, output_path), patch_semantic_splitter(), redirect_stdout(io.StringIO()):
                exit_code = main(["build-semantic"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "")

    def test_malformed_parent_jsonl_rejected_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_path = workspace / "parents.jsonl"
            output_path = workspace / "chunks.jsonl"
            input_path.write_text('{"chunk_id": "missing-required-fields"}\n', encoding="utf-8")
            stderr = io.StringIO()

            with semantic_cli_defaults(input_path, output_path), patch_semantic_splitter(), redirect_stderr(stderr):
                exit_code = main(["build-semantic"])

            self.assertEqual(exit_code, 2)
            self.assertIn("error: Invalid parent chunk record", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_normalized_semantic_text_writes_unresolved_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            input_path = workspace / "parents.jsonl"
            output_path = workspace / "chunks.jsonl"
            write_parent_chunks([make_parent_chunk()], input_path)

            with semantic_cli_defaults(input_path, output_path), patch_normalized_semantic_splitter(), redirect_stdout(
                io.StringIO()
            ):
                exit_code = main(["build-semantic"])

            self.assertEqual(exit_code, 0)
            records = read_records(output_path)
            self.assertEqual(len(records), 1)
            self.assertIsNone(records[0]["start_char"])
            self.assertIsNone(records[0]["end_char"])
            self.assertEqual(records[0]["metadata"]["chunk"]["offset_status"], "unresolved")
            self.assertEqual(
                records[0]["metadata"]["chunk"]["offset_reason"],
                "semantic_chunk_text_not_exact_substring",
            )


def build_one_semantic_fixture(workspace: Path) -> Path:
    input_path = workspace / "parents.jsonl"
    output_path = workspace / "semantic" / "chunks.jsonl"
    write_parent_chunks([make_parent_chunk()], input_path)
    with semantic_cli_defaults(input_path, output_path), patch_semantic_splitter(), redirect_stdout(io.StringIO()):
        exit_code = main(["build-semantic"])
    if exit_code != 0:
        raise AssertionError(f"Fixture build failed with exit code {exit_code}")
    return output_path


def patch_semantic_splitter():
    return patch(
        "pipeline.chunking.hierarchical_splitter.child_splitter.semantic.create_semantic_splitter",
        return_value=FakeSemanticSplitter(),
    )


def patch_normalized_semantic_splitter():
    return patch(
        "pipeline.chunking.hierarchical_splitter.child_splitter.semantic.create_semantic_splitter",
        return_value=NormalizedSemanticSplitter(),
    )


@contextmanager
def semantic_cli_defaults(input_path: Path, output_path: Path):
    with ExitStack() as stack:
        stack.enter_context(
            patch.multiple(
                "pipeline.chunking.cli",
                DEFAULT_PARENT_CHUNKS_PATH=input_path,
                DEFAULT_SEMANTIC_CHUNKS_PATH=output_path,
            )
        )
        stack.enter_context(
            patch(
                "pipeline.chunking.hierarchical_splitter.child_splitter.shared.estimate_token_count",
                side_effect=lambda text: max(1, len(text.split())),
            )
        )
        yield


class FakeSemanticSplitter:
    """Small test double that avoids embedding model downloads."""

    def create_documents(self, texts: list[str]) -> list[SimpleNamespace]:
        first, second = texts[0].split(" Debe ", maxsplit=1)
        return [
            SimpleNamespace(page_content=first),
            SimpleNamespace(page_content=f"Debe {second}"),
        ]


class NormalizedSemanticSplitter:
    """Test double that returns text not present verbatim in the parent."""

    def create_documents(self, texts: list[str]) -> list[SimpleNamespace]:
        return [SimpleNamespace(page_content=texts[0].replace("Artículo", "Articulo"))]


def make_parent_chunk(text: str | None = None) -> ParentChunk:
    """Create one representative parent chunk for Phase 3 tests."""

    parent_text = text if text is not None else "Artículo 1. El empleador identifica peligros. Debe conservar evidencias verificables."
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
