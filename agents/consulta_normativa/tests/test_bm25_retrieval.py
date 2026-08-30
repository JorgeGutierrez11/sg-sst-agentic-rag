"""Tests for runtime BM25 sparse retrieval helpers."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.retrieval import bm25_retrieval


class Bm25RetrievalTest(unittest.TestCase):
    """Verify BM25 runtime retrieval stays query-only and Chroma-shaped."""

    def test_open_existing_index_fails_when_path_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "missing-bm25"

            with self.assertRaisesRegex(ValueError, "BM25 persist path does not exist"):
                bm25_retrieval.open_existing_index(missing_path)

    def test_open_existing_index_loads_existing_corpus_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            persist_path = Path(temporary_directory) / "bm25"
            persist_path.mkdir()
            fake_bm25s = FakeBm25sModule(FakeIndex([]))

            with patch.object(bm25_retrieval, "bm25s_module", return_value=fake_bm25s):
                index = bm25_retrieval.open_existing_index(persist_path)

        self.assertIs(index, fake_bm25s.loaded_index)
        self.assertEqual(fake_bm25s.loaded_path, str(persist_path))
        self.assertEqual(fake_bm25s.load_corpus, True)

    def test_query_top_k_tokenizes_query_and_returns_chroma_like_shape(self) -> None:
        index = FakeIndex(
            [
                {"id": "child-1", "document": "Texto normativo.", "metadata": {"document_type": "child_chunk"}},
                {"id": "table-1", "document": "| Estándar |", "metadata": {"document_type": "table"}},
            ]
        )
        fake_bm25s = FakeBm25sModule(index)

        with patch.object(bm25_retrieval, "bm25s_module", return_value=fake_bm25s):
            result = bm25_retrieval.query_top_k(index, "¿Qué exige el SG-SST?", top_k=2)

        self.assertEqual(fake_bm25s.tokenized_queries, ["¿Qué exige el SG-SST?"])
        self.assertEqual(fake_bm25s.tokenized_stopwords, "es")
        self.assertEqual(index.last_query_tokens, ["query-token:¿Qué exige el SG-SST?"])
        self.assertEqual(index.last_k, 2)
        self.assertEqual(index.last_return_as, "tuple")
        self.assertEqual(result["ids"], [["child-1", "table-1"]])
        self.assertEqual(result["documents"], [["Texto normativo.", "| Estándar |"]])
        self.assertEqual(result["metadatas"], [[{"document_type": "child_chunk"}, {"document_type": "table"}]])
        self.assertEqual(result["scores"], [[1.5, 0.7]])

    def test_query_top_k_accepts_results_object_when_return_as_is_not_supported(self) -> None:
        index = FakeLegacyResultsIndex([{"id": "child-1", "document": "Texto.", "metadata": {}}])
        fake_bm25s = FakeBm25sModule(index)

        with patch.object(bm25_retrieval, "bm25s_module", return_value=fake_bm25s):
            result = bm25_retrieval.query_top_k(index, "pregunta", top_k=1)

        self.assertEqual(result["ids"], [["child-1"]])
        self.assertEqual(result["documents"], [["Texto."]])
        self.assertEqual(result["metadatas"], [[{}]])
        self.assertEqual(result["scores"], [[1.5]])

    def test_query_top_k_caps_top_k_to_corpus_size(self) -> None:
        index = FakeIndex([{"id": "child-1", "document": "Texto.", "metadata": {}}])
        fake_bm25s = FakeBm25sModule(index)

        with patch.object(bm25_retrieval, "bm25s_module", return_value=fake_bm25s):
            bm25_retrieval.query_top_k(index, "pregunta", top_k=5)

        self.assertEqual(index.last_k, 1)

    def test_query_top_k_returns_empty_shape_for_empty_corpus_or_non_positive_top_k(self) -> None:
        self.assertEqual(bm25_retrieval.query_top_k(FakeIndex([]), "pregunta", top_k=5), bm25_retrieval.EMPTY_QUERY_RESULT)
        self.assertEqual(
            bm25_retrieval.query_top_k(FakeIndex([{"id": "child-1", "document": "Texto.", "metadata": {}}]), "pregunta", top_k=0),
            bm25_retrieval.EMPTY_QUERY_RESULT,
        )

    def test_bm25_retriever_delegates_to_query_top_k(self) -> None:
        index = object()
        expected_result = {"ids": [["child-1"]], "documents": [["Texto."]], "metadatas": [[{}]], "scores": [[1.0]]}

        with patch.object(bm25_retrieval, "query_top_k", return_value=expected_result) as query_top_k:
            retrieve = bm25_retrieval.bm25_retriever(index)
            result = retrieve("pregunta", 3)

        self.assertIs(result, expected_result)
        query_top_k.assert_called_once_with(index, "pregunta", 3)

    @unittest.skipIf(importlib.util.find_spec("bm25s") is None, "bm25s is not installed")
    def test_query_top_k_with_real_bm25s_index_returns_saved_corpus_records(self) -> None:
        import bm25s

        corpus = [
            {"id": "sg-sst-1", "document": "seguridad salud trabajo empresa", "metadata": {"source": "doc-1"}},
            {"id": "nomina-1", "document": "vacaciones salario nomina", "metadata": {"source": "doc-2"}},
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            persist_path = Path(temporary_directory) / "bm25"
            retriever = bm25s.BM25()
            retriever.index(bm25s.tokenize([record["document"] for record in corpus], stopwords="es"))
            retriever.save(str(persist_path), corpus=corpus)

            loaded_index = bm25_retrieval.open_existing_index(persist_path)
            result = bm25_retrieval.query_top_k(loaded_index, "seguridad empresa", top_k=1)

        self.assertEqual(set(result), {"ids", "documents", "metadatas", "scores"})
        self.assertEqual(result["ids"], [["sg-sst-1"]])
        self.assertEqual(result["documents"], [["seguridad salud trabajo empresa"]])
        self.assertEqual(result["metadatas"], [[{"source": "doc-1"}]])
        self.assertEqual(len(result["scores"][0]), 1)
        self.assertIsInstance(result["scores"][0][0], float)


class FakeBm25sModule:
    """Small BM25S module test double."""

    def __init__(self, loaded_index: "FakeIndex") -> None:
        self.loaded_index = loaded_index
        self.loaded_path = ""
        self.load_corpus = False
        self.tokenized_queries: list[str] = []
        self.tokenized_stopwords: str | None = None
        self.BM25 = FakeBm25Loader(self)

    def tokenize(self, queries: list[str], *, stopwords: str | None = None) -> list[str]:
        self.tokenized_queries = queries
        self.tokenized_stopwords = stopwords
        return [f"query-token:{query}" for query in queries]


class FakeBm25Loader:
    """BM25 loader test double."""

    def __init__(self, module: FakeBm25sModule) -> None:
        self.module = module

    def load(self, path: str, *, load_corpus: bool) -> "FakeIndex":
        self.module.loaded_path = path
        self.module.load_corpus = load_corpus
        return self.module.loaded_index


class FakeIndex:
    """Small loaded BM25 index test double."""

    def __init__(self, corpus: list[dict[str, object]]) -> None:
        self.corpus = corpus
        self.last_query_tokens: list[str] = []
        self.last_k = 0
        self.last_return_as = ""

    def retrieve(
        self,
        query_tokens: list[str],
        *,
        k: int,
        return_as: str = "",
    ) -> tuple[list[list[dict[str, object]]], list[list[float]]]:
        self.last_query_tokens = query_tokens
        self.last_k = k
        self.last_return_as = return_as
        return [self.corpus[:k]], [[1.5, 0.7][:k]]


class FakeResults:
    """Small BM25S Results-like object test double."""

    def __init__(self, documents: list[list[dict[str, object]]], scores: list[list[float]]) -> None:
        self.documents = documents
        self.scores = scores


class FakeLegacyResultsIndex(FakeIndex):
    """Loaded BM25 index test double for APIs without return_as support."""

    def retrieve(self, query_tokens: list[str], *, k: int) -> FakeResults:
        self.last_query_tokens = query_tokens
        self.last_k = k
        return FakeResults([self.corpus[:k]], [[1.5, 0.7][:k]])


if __name__ == "__main__":
    unittest.main()
