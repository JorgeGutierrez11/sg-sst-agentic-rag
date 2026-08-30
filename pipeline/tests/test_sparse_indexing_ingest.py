"""Tests for BM25 sparse indexing orchestration."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pipeline.sparse_indexing import ingest
from pipeline.sparse_indexing import main as sparse_indexing_main
from pipeline.vectorization.documents import ChromaRecord, LoadedVectorRecords


class SparseIndexingIngestTest(unittest.TestCase):
    """Verify sparse indexing uses canonical vector records and reports counts."""

    def test_ingest_missing_jsonl_inputs_fails_before_opening_bm25(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            chunks_path = Path(temporary_directory) / "missing-chunks.jsonl"
            tables_path = Path(temporary_directory) / "missing-tables.jsonl"
            persist_path = Path(temporary_directory) / "bm25"

            with patch.object(
                ingest,
                "build_bm25_index",
                side_effect=AssertionError("BM25 must not open when source JSONL files are missing"),
            ) as build_bm25_index:
                with self.assertRaisesRegex(ValueError, "Missing sparse indexing source JSONL"):
                    ingest.ingest_sparse_bm25_documents(chunks_path, tables_path, persist_path)

        build_bm25_index.assert_not_called()

    def test_ingest_uses_canonical_jsonl_loader_and_preserves_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            chunks_path = Path(temporary_directory) / "chunks.jsonl"
            tables_path = Path(temporary_directory) / "tables.jsonl"
            persist_path = Path(temporary_directory) / "bm25"
            self.write_jsonl(chunks_path, [])
            self.write_jsonl(tables_path, [])
            loaded = LoadedVectorRecords(
                records=[
                    ChromaRecord(id="child-1", document="Texto.", metadata={"document_type": "child_chunk"}),
                    ChromaRecord(id="table-1", document="Tabla.", metadata={"document_type": "table"}),
                ],
                skipped_child_chunk_count=1,
                skipped_table_count=2,
            )
            retriever = object()
            corpus = [{"id": "child-1"}, {"id": "table-1"}]

            with patch.object(ingest, "load_vector_record_batch", return_value=loaded) as load_vector_record_batch, patch.object(
                ingest, "build_bm25_index", return_value=(retriever, corpus)
            ) as build_bm25_index, patch.object(ingest, "save_bm25_index") as save_bm25_index, patch.object(
                ingest, "print_indexing_start"
            ):
                result = ingest.ingest_sparse_bm25_documents(chunks_path, tables_path, persist_path)

        load_vector_record_batch.assert_called_once_with(chunks_path, tables_path)
        build_bm25_index.assert_called_once_with(loaded.records)
        save_bm25_index.assert_called_once_with(retriever, persist_path, corpus)
        self.assertEqual(result.total_count, 2)
        self.assertEqual(result.child_chunk_count, 1)
        self.assertEqual(result.table_count, 1)
        self.assertEqual(result.skipped_child_chunk_count, 1)
        self.assertEqual(result.skipped_table_count, 2)

    def test_ingest_preserves_ids_from_child_chunks_and_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            chunks_path = Path(temporary_directory) / "chunks.jsonl"
            tables_path = Path(temporary_directory) / "tables.jsonl"
            persist_path = Path(temporary_directory) / "bm25"
            self.write_jsonl(
                chunks_path,
                [{"chunk_id": "child-valid", "text": "Valid child text.", "metadata": {"inherited": {}}}],
            )
            self.write_jsonl(
                tables_path,
                [
                    {
                        "id": "table-valid",
                        "text": "| Valid | Table |",
                        "metadata": {"source_stem": "Resolución 0312", "table_index": 1},
                    }
                ],
            )

            with patch.object(ingest, "build_bm25_index", return_value=("retriever", [])) as build_bm25_index, patch.object(
                ingest, "save_bm25_index"
            ), patch.object(ingest, "print_indexing_start"):
                result = ingest.ingest_sparse_bm25_documents(chunks_path, tables_path, persist_path)

        records = build_bm25_index.call_args.args[0]
        self.assertEqual([record.id for record in records], ["child-valid", "table-valid"])
        self.assertEqual(result.child_chunk_count, 1)
        self.assertEqual(result.table_count, 1)

    def test_sparse_indexing_cli_uses_default_paths(self) -> None:
        with patch.object(sparse_indexing_main, "ingest_sparse_bm25_documents") as ingest_sparse_bm25_documents:
            ingest_sparse_bm25_documents.return_value = ingest.SparseIndexResult(
                total_count=0,
                child_chunk_count=0,
                table_count=0,
                skipped_child_chunk_count=0,
                skipped_table_count=0,
                persist_path=Path("data/processed/bm25"),
            )

            with redirect_stdout(io.StringIO()):
                exit_code = sparse_indexing_main.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(ingest_sparse_bm25_documents.call_args.kwargs["persist_path"], ingest.DEFAULT_BM25_PATH)

    def write_jsonl(self, path: Path, records: list[dict[str, object]]) -> None:
        path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
