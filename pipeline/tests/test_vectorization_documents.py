"""Tests for base RAG vector document normalization."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pipeline.vectorization import ingest
from pipeline.vectorization import main as vectorization_main
from pipeline.vectorization.documents import (
    ChromaRecord,
    LoadedVectorRecords,
    child_chunk_to_chroma,
    load_vector_record_batch,
    table_document_to_chroma,
)


class VectorizationDocumentsTest(unittest.TestCase):
    """Verify ChromaDB records stay flat, stable, and traceable."""

    def test_child_chunk_metadata_is_flat_and_includes_table_keys(self) -> None:
        record = {
            "chunk_id": "child-1",
            "parent_id": "parent-1",
            "source_document_id": "source-1",
            "text": "Artículo 1. Texto. <!-- TABLE_0 -->",
            "start_char": 10,
            "end_char": 42,
            "metadata": {
                "inherited": {
                    "source_stem": "Resolución 0312 de 2019",
                    "hierarchy": {"article": "1"},
                },
                "chunk": {
                    "tables": [
                        {
                            "source_stem": "Resolución 0312 de 2019",
                            "table_index": 0,
                            "placeholder": "<!-- TABLE_0 -->",
                        }
                    ]
                },
            },
        }

        chroma_record = child_chunk_to_chroma(record)

        self.assertEqual(chroma_record.id, "child-1")
        self.assertEqual(chroma_record.metadata["document_type"], "child_chunk")
        self.assertEqual(chroma_record.metadata["source_stem"], "Resolución 0312 de 2019")
        self.assertEqual(chroma_record.metadata["article"], "1")
        self.assertEqual(chroma_record.metadata["has_tables"], True)
        self.assertEqual(chroma_record.metadata["table_keys"], "Resolución 0312 de 2019:0")
        self.assert_metadata_is_flat(chroma_record.metadata)

    def test_table_document_metadata_uses_logical_table_key(self) -> None:
        record = {
            "id": "table-resolucion-0312-de-2019-0",
            "text": "| Ítem | Criterio |\n|---|---|",
            "metadata": {
                "type": "table",
                "source_stem": "Resolución 0312 de 2019",
                "table_index": 0,
                "linked_placeholder": "<!-- TABLE_0 -->",
            },
        }

        chroma_record = table_document_to_chroma(record)

        self.assertEqual(chroma_record.id, "table-resolucion-0312-de-2019-0")
        self.assertEqual(chroma_record.metadata["document_type"], "table")
        self.assertEqual(chroma_record.metadata["table_key"], "Resolución 0312 de 2019:0")
        self.assertEqual(chroma_record.metadata["linked_placeholder"], "<!-- TABLE_0 -->")
        self.assert_metadata_is_flat(chroma_record.metadata)

    def test_blank_text_with_id_raises_controlled_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty text"):
            table_document_to_chroma({"id": "table-1", "text": "   ", "metadata": {}})

    def test_invalid_table_metadata_raises_controlled_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "malformed 'metadata'"):
            table_document_to_chroma({"id": "table-1", "text": "Valid text.", "metadata": []})

        with self.assertRaisesRegex(ValueError, "invalid integer metadata field 'table_index'"):
            table_document_to_chroma(
                {
                    "id": "table-1",
                    "text": "Valid text.",
                    "metadata": {"source_stem": "Resolución 0312", "table_index": "not-a-number"},
                }
            )

    def test_bulk_loading_skips_empty_child_and_table_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            chunks_path = Path(temporary_directory) / "chunks.jsonl"
            tables_path = Path(temporary_directory) / "tables.jsonl"
            self.write_jsonl(
                chunks_path,
                [
                    {
                        "chunk_id": "child-valid",
                        "parent_id": "parent-1",
                        "source_document_id": "source-1",
                        "text": "Valid child text.",
                        "metadata": {"inherited": {"source_stem": "Decreto 1072 de 2015"}},
                    },
                    {"chunk_id": "child-empty", "text": "   ", "metadata": {}},
                ],
            )
            self.write_jsonl(
                tables_path,
                [
                    {
                        "id": "table-valid",
                        "text": "| Valid | Table |",
                        "metadata": {"source_stem": "Resolución 0312 de 2019", "table_index": 1},
                    },
                    {"id": "table-empty", "text": "", "metadata": {}},
                ],
            )

            loaded = load_vector_record_batch(chunks_path, tables_path)

        self.assertEqual([record.id for record in loaded.records], ["child-valid", "table-valid"])
        self.assertEqual(loaded.skipped_child_chunk_count, 1)
        self.assertEqual(loaded.skipped_table_count, 1)
        self.assertEqual(loaded.skipped_count, 2)

    def test_ingest_missing_jsonl_inputs_fails_before_opening_chroma(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            chunks_path = Path(temporary_directory) / "missing-chunks.jsonl"
            tables_path = Path(temporary_directory) / "missing-tables.jsonl"
            persist_path = Path(temporary_directory) / "chroma"

            with patch.object(
                ingest,
                "open_or_create_collection",
                side_effect=AssertionError("Chroma must not open when source JSONL files are missing"),
            ) as open_or_create_collection:
                with self.assertRaisesRegex(ValueError, "Missing vectorization source JSONL"):
                    ingest.ingest_base_rag_documents(chunks_path, tables_path, persist_path)

        open_or_create_collection.assert_not_called()

    def test_ingest_rejects_invalid_batch_size_before_opening_chroma(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            chunks_path = Path(temporary_directory) / "chunks.jsonl"
            tables_path = Path(temporary_directory) / "tables.jsonl"
            persist_path = Path(temporary_directory) / "chroma"
            self.write_jsonl(chunks_path, [])
            self.write_jsonl(tables_path, [])

            with patch.object(
                ingest,
                "open_or_create_collection",
                side_effect=AssertionError("Chroma must not open with invalid batch size"),
            ) as open_or_create_collection:
                with self.assertRaisesRegex(ValueError, "--batch-size must be greater than 0"):
                    ingest.ingest_base_rag_documents(chunks_path, tables_path, persist_path, batch_size=0)

        open_or_create_collection.assert_not_called()

    def test_ingest_passes_batch_size_to_chroma_upsert(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            chunks_path = Path(temporary_directory) / "chunks.jsonl"
            tables_path = Path(temporary_directory) / "tables.jsonl"
            persist_path = Path(temporary_directory) / "chroma"
            self.write_jsonl(chunks_path, [])
            self.write_jsonl(tables_path, [])
            loaded = LoadedVectorRecords(
                records=[ChromaRecord(id="child-1", document="Texto.", metadata={"document_type": "child_chunk"})]
            )

            with patch.object(ingest, "load_vector_record_batch", return_value=loaded), patch.object(
                ingest, "open_or_create_collection", return_value="collection"
            ), patch.object(ingest, "upsert_records", return_value=1) as upsert_records, patch.object(
                ingest, "print_ingest_start"
            ) as print_ingest_start, patch.object(ingest, "print_collection_opening") as print_collection_opening:
                result = ingest.ingest_base_rag_documents(chunks_path, tables_path, persist_path, batch_size=3)

        self.assertEqual(result.total_count, 1)
        print_ingest_start.assert_called_once_with(1, 3)
        print_collection_opening.assert_called_once()
        upsert_records.assert_called_once()
        self.assertEqual(upsert_records.call_args.kwargs["batch_size"], 3)
        self.assertIs(upsert_records.call_args.kwargs["on_batch_complete"], ingest.print_batch_progress)

    def test_ingest_reports_progress_before_opening_chroma(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            chunks_path = Path(temporary_directory) / "chunks.jsonl"
            tables_path = Path(temporary_directory) / "tables.jsonl"
            persist_path = Path(temporary_directory) / "chroma"
            self.write_jsonl(chunks_path, [])
            self.write_jsonl(tables_path, [])
            loaded = LoadedVectorRecords(
                records=[ChromaRecord(id="child-1", document="Texto.", metadata={"document_type": "child_chunk"})]
            )
            calls: list[str] = []

            with patch.object(ingest, "load_vector_record_batch", return_value=loaded), patch.object(
                ingest, "print_ingest_start", side_effect=lambda *_args: calls.append("start")
            ), patch.object(
                ingest, "print_collection_opening", side_effect=lambda *_args: calls.append("opening")
            ), patch.object(
                ingest, "open_or_create_collection", side_effect=lambda *_args: calls.append("open") or "collection"
            ), patch.object(ingest, "upsert_records", side_effect=lambda *_args, **_kwargs: calls.append("upsert") or 1):
                ingest.ingest_base_rag_documents(chunks_path, tables_path, persist_path, batch_size=3)

        self.assertEqual(calls, ["start", "opening", "open", "upsert"])

    def test_vectorization_cli_uses_default_batch_size(self) -> None:
        with patch.object(vectorization_main, "ingest_base_rag_documents") as ingest_base_rag_documents:
            ingest_base_rag_documents.return_value = ingest.IngestResult(
                total_count=0,
                child_chunk_count=0,
                table_count=0,
                skipped_child_chunk_count=0,
                skipped_table_count=0,
                persist_path=Path("data/processed/chroma"),
                collection_name="sg_sst_base_rag",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = vectorization_main.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(ingest_base_rag_documents.call_args.kwargs["batch_size"], ingest.DEFAULT_INGEST_BATCH_SIZE)

    def test_vectorization_cli_passes_explicit_batch_size_to_ingest(self) -> None:
        with patch.object(vectorization_main, "ingest_base_rag_documents") as ingest_base_rag_documents:
            ingest_base_rag_documents.return_value = ingest.IngestResult(
                total_count=0,
                child_chunk_count=0,
                table_count=0,
                skipped_child_chunk_count=0,
                skipped_table_count=0,
                persist_path=Path("data/processed/chroma"),
                collection_name="sg_sst_base_rag",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = vectorization_main.main(["--batch-size", "2"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(ingest_base_rag_documents.call_args.kwargs["batch_size"], 2)

    def assert_metadata_is_flat(self, metadata: dict[str, object]) -> None:
        for value in metadata.values():
            self.assertIsInstance(value, (str, int, float, bool))

    def write_jsonl(self, path: Path, records: list[dict[str, object]]) -> None:
        path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
