"""Tests for base RAG vector document normalization."""

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.vectorization.documents import child_chunk_to_chroma, load_vector_record_batch, table_document_to_chroma


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

    def assert_metadata_is_flat(self, metadata: dict[str, object]) -> None:
        for value in metadata.values():
            self.assertIsInstance(value, (str, int, float, bool))

    def write_jsonl(self, path: Path, records: list[dict[str, object]]) -> None:
        path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
