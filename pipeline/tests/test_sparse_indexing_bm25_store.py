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

        self.assertEqual(
            fake_bm25s.tokenized_texts,
            [
                "Metadata normativa:\nTipo de fragmento: child_chunk\n\nContenido:\nPrimero.",
                "Metadata normativa:\nTipo de fragmento: table\n\nContenido:\nSegundo.",
            ],
        )
        self.assertEqual(fake_bm25s.tokenized_stopwords, "es")
        self.assertEqual(fake_bm25s.bm25_constructor_call_count, 1)
        self.assertEqual(
            retriever.indexed_tokens,
            [
                "token:Metadata normativa:\nTipo de fragmento: child_chunk\n\nContenido:\nPrimero.",
                "token:Metadata normativa:\nTipo de fragmento: table\n\nContenido:\nSegundo.",
            ],
        )
        self.assertEqual([record["id"] for record in corpus], ["child-1", "table-1"])

    def test_build_bm25_index_tokenizes_enriched_text(self) -> None:
        fake_bm25s = FakeBm25sModule()
        records = [
            ChromaRecord(
                id="table-1",
                document="Tabla de estándares mínimos.",
                metadata={
                    "source_stem": "resolucion_0312_2019",
                    "normative_document_type": "resolucion",
                    "year": 2019,
                    "document_type": "table",
                    "table_key": "resolucion_0312_2019_table_1",
                },
            )
        ]
        expected_text = (
            "Metadata normativa:\n"
            "Fuente: resolucion_0312_2019\n"
            "Tipo normativo: resolucion\n"
            "Año: 2019\n"
            "Tipo de fragmento: table\n"
            "Tabla: resolucion_0312_2019_table_1\n\n"
            "Contenido:\n"
            "Tabla de estándares mínimos."
        )

        with patch.object(bm25_store, "bm25s_module", return_value=fake_bm25s):
            bm25_store.build_bm25_index(records)

        self.assertEqual(fake_bm25s.tokenized_texts, [expected_text])

    def test_bm25_corpus_preserves_original_document_and_metadata(self) -> None:
        record = ChromaRecord(
            id="table-1",
            document="Tabla de estándares mínimos.",
            metadata={"source_stem": "resolucion_0312_2019", "table_key": "table_1"},
        )

        corpus = bm25_store.bm25_corpus([record])

        self.assertEqual(corpus[0]["document"], "Tabla de estándares mínimos.")
        self.assertEqual(corpus[0]["metadata"], record.metadata)

    def test_bm25_text_for_indexing_excludes_trace_metadata(self) -> None:
        record = ChromaRecord(
            id="chunk-1",
            document="Contenido normativo.",
            metadata={
                "source_stem": "decreto_1072_2015",
                "_retrieval_sources": ["dense", "sparse"],
                "_chroma_id": "abc",
                "document_id": "doc-1",
                "parent_id": "parent-1",
                "start_char": 10,
                "token_count": 20,
            },
        )

        text = bm25_store.bm25_text_for_indexing(record)

        self.assertIn("Fuente: decreto_1072_2015", text)
        self.assertIn("Contenido:\nContenido normativo.", text)
        self.assertNotIn("_retrieval_sources", text)
        self.assertNotIn("dense", text)
        self.assertNotIn("_chroma_id", text)
        self.assertNotIn("abc", text)
        self.assertNotIn("document_id", text)
        self.assertNotIn("parent-1", text)
        self.assertNotIn("start_char", text)
        self.assertNotIn("token_count", text)

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
