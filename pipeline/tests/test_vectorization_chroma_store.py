"""Tests for the ChromaDB vector store boundary."""

import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.vectorization import chroma_store
from pipeline.vectorization.chroma_store import record_batches, upsert_records
from pipeline.vectorization.documents import ChromaRecord


class VectorizationChromaStoreTest(unittest.TestCase):
    """Verify Chroma collection writes use the expected upsert payload."""

    def test_upsert_records_sends_ids_documents_and_metadata(self) -> None:
        collection = FakeCollection()
        records = [
            ChromaRecord(id="child-1", document="Texto normativo.", metadata={"document_type": "child_chunk"}),
            ChromaRecord(id="table-1", document="| A | B |", metadata={"document_type": "table"}),
        ]

        inserted_count = upsert_records(collection, records)

        self.assertEqual(inserted_count, 2)
        self.assertEqual(collection.payloads[-1]["ids"], ["child-1", "table-1"])
        self.assertEqual(collection.payloads[-1]["documents"], ["Texto normativo.", "| A | B |"])
        self.assertEqual(
            collection.payloads[-1]["metadatas"],
            [{"document_type": "child_chunk"}, {"document_type": "table"}],
        )

    def test_upsert_records_splits_large_payloads_into_batches(self) -> None:
        collection = FakeCollection()
        records = [
            ChromaRecord(id=f"record-{index}", document=f"Texto {index}.", metadata={"document_type": "child_chunk"})
            for index in range(5)
        ]
        progress: list[tuple[int, int, int]] = []

        inserted_count = upsert_records(
            collection,
            records,
            batch_size=2,
            on_batch_complete=lambda batch_index, total_batches, inserted: progress.append(
                (batch_index, total_batches, inserted)
            ),
        )

        self.assertEqual(inserted_count, 5)
        self.assertEqual([payload["ids"] for payload in collection.payloads], [
            ["record-0", "record-1"],
            ["record-2", "record-3"],
            ["record-4"],
        ])
        self.assertEqual(progress, [(1, 3, 2), (2, 3, 4), (3, 3, 5)])

    def test_upsert_records_rejects_invalid_batch_size(self) -> None:
        collection = FakeCollection()
        records = [ChromaRecord(id="child-1", document="Texto.", metadata={"document_type": "child_chunk"})]

        with self.assertRaisesRegex(ValueError, "--batch-size must be greater than 0"):
            upsert_records(collection, records, batch_size=0)

    def test_record_batches_preserves_order(self) -> None:
        records = [ChromaRecord(id=str(index), document="Texto.", metadata={"document_type": "child_chunk"}) for index in range(3)]

        batches = record_batches(records, batch_size=2)

        self.assertEqual([[record.id for record in batch] for batch in batches], [["0", "1"], ["2"]])

    def test_upsert_records_skips_empty_batches(self) -> None:
        collection = FakeCollection()

        inserted_count = upsert_records(collection, [])

        self.assertEqual(inserted_count, 0)
        self.assertEqual(collection.payloads, [])

    def test_open_or_create_collection_uses_get_or_create_with_qwen_embedding(self) -> None:
        client = FakeChromaClient()
        embedding_function = object()

        with patch.object(chroma_store, "persistent_client", return_value=client) as persistent_client, patch.object(
            chroma_store, "qwen_embedding_function", return_value=embedding_function
        ):
            collection = chroma_store.open_or_create_collection(Path("/tmp/chroma"), "test_collection")

        self.assertEqual(collection, "created-collection")
        persistent_client.assert_called_once_with(Path("/tmp/chroma"), create_path=True)
        self.assertEqual(client.get_or_create_payload, {"name": "test_collection", "embedding_function": embedding_function})
        self.assertEqual(client.get_payload, {})


class FakeCollection:
    """Small collection test double that records the last upsert payload."""

    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def upsert(self, **kwargs: object) -> None:
        self.payloads.append(kwargs)


class FakeChromaClient:
    """Small Chroma client test double that records collection-opening calls."""

    def __init__(self) -> None:
        self.get_or_create_payload: dict[str, object] = {}
        self.get_payload: dict[str, object] = {}

    def get_or_create_collection(self, **kwargs: object) -> str:
        self.get_or_create_payload = kwargs
        return "created-collection"

    def get_collection(self, **kwargs: object) -> str:
        self.get_payload = kwargs
        return "existing-collection"


if __name__ == "__main__":
    unittest.main()
