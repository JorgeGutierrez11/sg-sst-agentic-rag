"""Tests for the BM25S sparse store boundary."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.sparse_indexing import bm25_store
from pipeline.vectorization.documents import ChromaRecord


class SparseIndexingBm25StoreTest(unittest.TestCase):
    """Verify BM25 corpus construction, indexing, and persistence payloads."""

    def test_bm25_corpus_preserves_id_document_metadata_and_order(self) -> None:
        records = [
            ChromaRecord(id="child-1", document="Decreto 1072 texto.", metadata={"document_type": "child_chunk"}),
            ChromaRecord(id="table-1", document="| Estándar |", metadata={"document_type": "table"}),
        ]

        corpus = bm25_store.bm25_corpus(records)

        self.assertEqual(corpus[0], {"id": "child-1", "document": "Decreto 1072 texto.", "metadata": {"document_type": "child_chunk"}})
        self.assertEqual(corpus[1]["id"], "table-1")

    def test_build_bm25_index_tokenizes_texts_in_corpus_order(self) -> None:
        fake_bm25s = FakeBm25sModule()
        records = [
            ChromaRecord(id="child-1", document="Primero.", metadata={"document_type": "child_chunk"}),
            ChromaRecord(id="table-1", document="Segundo.", metadata={"document_type": "table"}),
        ]

        with patch.object(bm25_store, "bm25s_module", return_value=fake_bm25s):
            retriever, corpus = bm25_store.build_bm25_index(records)

        self.assertEqual(fake_bm25s.tokenized_texts, ["Primero.", "Segundo."])
        self.assertEqual(fake_bm25s.tokenized_stopwords, "es")
        self.assertEqual(fake_bm25s.bm25_constructor_call_count, 1)
        self.assertEqual(retriever.indexed_tokens, ["token:Primero.", "token:Segundo."])
        self.assertEqual([record["id"] for record in corpus], ["child-1", "table-1"])

    def test_save_bm25_index_calls_save_with_corpus(self) -> None:
        retriever = FakeRetriever()
        corpus = [{"id": "child-1", "document": "Texto.", "metadata": {}}]

        with tempfile.TemporaryDirectory() as temporary_directory:
            persist_path = Path(temporary_directory) / "bm25"
            bm25_store.save_bm25_index(retriever, persist_path, corpus)

        self.assertEqual(retriever.saved_path, str(persist_path))
        self.assertIs(retriever.saved_corpus, corpus)


class FakeBm25sModule:
    """Small BM25S module test double."""

    def __init__(self) -> None:
        self.tokenized_texts: list[str] = []
        self.tokenized_stopwords: str | None = None
        self.bm25_constructor_call_count = 0

    def tokenize(self, texts: list[str], *, stopwords: str | None = None) -> list[str]:
        self.tokenized_texts = texts
        self.tokenized_stopwords = stopwords
        return [f"token:{text}" for text in texts]

    def BM25(self) -> "FakeRetriever":
        self.bm25_constructor_call_count += 1
        return FakeRetriever()


class FakeRetriever:
    """Small BM25 retriever test double."""

    def __init__(self) -> None:
        self.indexed_tokens: list[str] = []
        self.saved_path = ""
        self.saved_corpus: list[dict[str, object]] = []

    def index(self, tokens: list[str]) -> None:
        self.indexed_tokens = tokens

    def save(self, path: str, *, corpus: list[dict[str, object]]) -> None:
        self.saved_path = path
        self.saved_corpus = corpus


if __name__ == "__main__":
    unittest.main()
