"""Tests for post-retrieval reranking."""

import sys
import types
import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.models import RetrievedDocument
from agents.consulta_normativa.langchain_rag.retrieval.reranking import (
    document_text_for_reranking,
    get_reranker,
    rerank_documents,
    rerank_node,
)


class LangChainRagRerankingTest(unittest.TestCase):
    """Verify reranking behavior without loading the real CrossEncoder model."""

    def tearDown(self) -> None:
        get_reranker.cache_clear()

    def test_rerank_documents_sorts_by_descending_fake_scores(self) -> None:
        first = RetrievedDocument("first", {})
        second = RetrievedDocument("second", {})
        third = RetrievedDocument("third", {})

        ranked = rerank_documents("query", [first, second, third], FakeReranker([0.2, 0.9, 0.4]), final_top_k=3)

        self.assertEqual(ranked, [second, third, first])

    def test_rerank_documents_preserves_retrieved_document_identity(self) -> None:
        first = RetrievedDocument("first", {})
        second = RetrievedDocument("second", {})

        ranked = rerank_documents("query", [first, second], FakeReranker([0.1, 0.8]), final_top_k=1)

        self.assertIs(ranked[0], second)

    def test_document_text_for_reranking_adds_compact_normative_metadata(self) -> None:
        document = RetrievedDocument(
            "El empleador debe identificar peligros y valorar riesgos.",
            {
                "source_stem": "decreto_1072_2015",
                "normative_document_type": "decreto",
                "year": 2015,
                "article": "2.2.4.6.15",
                "document_type": "child_chunk",
            },
        )

        text = document_text_for_reranking(document)

        self.assertIn("Metadata normativa:", text)
        self.assertIn("Fuente: decreto_1072_2015", text)
        self.assertIn("Tipo normativo: decreto", text)
        self.assertIn("Año: 2015", text)
        self.assertIn("Artículo: 2.2.4.6.15", text)
        self.assertIn("Tipo de fragmento: child_chunk", text)
        self.assertIn("Contenido:\nEl empleador debe identificar peligros", text)

    def test_document_text_for_reranking_excludes_trace_metadata(self) -> None:
        document = RetrievedDocument(
            "Contenido normativo.",
            {
                "source_stem": "resolucion_0312_2019",
                "_chroma_id": "abc",
                "_document_id": "doc-1",
                "_retrieval_sources": ["dense", "sparse"],
                "document_id": "doc-1",
                "parent_id": "parent-1",
                "expanded_from_child_ids": ["child-1"],
                "start_char": 10,
                "end_char": 50,
                "token_count": 20,
            },
        )

        text = document_text_for_reranking(document)

        self.assertIn("Fuente: resolucion_0312_2019", text)
        self.assertNotIn("_chroma_id", text)
        self.assertNotIn("abc", text)
        self.assertNotIn("_retrieval_sources", text)
        self.assertNotIn("dense", text)
        self.assertNotIn("document_id", text)
        self.assertNotIn("parent-1", text)
        self.assertNotIn("expanded_from_child_ids", text)
        self.assertNotIn("start_char", text)
        self.assertNotIn("token_count", text)

    def test_document_text_for_reranking_returns_document_when_metadata_empty(self) -> None:
        document = RetrievedDocument("Solo contenido.", {})

        self.assertEqual(document_text_for_reranking(document), "Solo contenido.")

    def test_rerank_documents_scores_enriched_text_and_returns_raw_documents(self) -> None:
        reranker = FakeReranker([0.9])
        document = RetrievedDocument(
            "Texto normativo original",
            {"source_stem": "resolucion_0312_2019"},
        )

        selected_documents = rerank_documents(
            "¿Qué exige la Resolución 0312?",
            [document],
            reranker,
            final_top_k=1,
        )

        candidate_pairs = reranker.pairs
        self.assertEqual(candidate_pairs[0][0], "¿Qué exige la Resolución 0312?")
        self.assertIn("Fuente: resolucion_0312_2019", candidate_pairs[0][1])
        self.assertIn("Contenido:\nTexto normativo original", candidate_pairs[0][1])
        self.assertEqual(selected_documents[0].document, "Texto normativo original")

    def test_rerank_node_writes_back_to_documents(self) -> None:
        first = RetrievedDocument("first", {})
        second = RetrievedDocument("second", {})

        update = rerank_node(FakeReranker([0.1, 0.9]), candidate_pool_size=2, final_top_k=2)(
            {"question": "query", "documents": [first, second]}
        )

        self.assertEqual(update["documents"], [second, first])
        self.assertNotIn("reranked_documents", update)
        self.assertFalse(update["reranking_trace"]["fallback"])

    def test_rerank_node_limits_to_final_top_k(self) -> None:
        documents = [RetrievedDocument(str(index), {}) for index in range(3)]

        update = rerank_node(FakeReranker([0.1, 0.9, 0.8]), candidate_pool_size=3, final_top_k=2)(
            {"question": "query", "documents": documents}
        )

        self.assertEqual(update["documents"], [documents[1], documents[2]])

    def test_rerank_node_falls_back_when_predict_raises(self) -> None:
        first = RetrievedDocument("first", {})
        second = RetrievedDocument("second", {})

        update = rerank_node(FailingReranker(), candidate_pool_size=2, final_top_k=1)(
            {"question": "query", "documents": [first, second]}
        )

        self.assertEqual(update["documents"], [first])
        self.assertTrue(update["reranking_trace"]["fallback"])
        self.assertEqual(update["reranking_trace"]["error"], "RuntimeError")

    def test_rerank_node_falls_back_when_lazy_loader_raises(self) -> None:
        first = RetrievedDocument("first", {})

        def failing_loader() -> object:
            raise ModuleNotFoundError("sentence-transformers missing")

        update = rerank_node(failing_loader, candidate_pool_size=1, final_top_k=1)(
            {"question": "query", "documents": [first]}
        )

        self.assertEqual(update["documents"], [first])
        self.assertTrue(update["reranking_trace"]["fallback"])
        self.assertEqual(update["reranking_trace"]["error"], "ModuleNotFoundError")

    def test_rerank_node_skips_reranker_loading_when_documents_are_empty(self) -> None:
        def failing_loader() -> object:
            raise AssertionError("reranker should not load without candidates")

        update = rerank_node(failing_loader, candidate_pool_size=10, final_top_k=5)(
            {"question": "query", "documents": []}
        )

        self.assertEqual(update["documents"], [])
        self.assertFalse(update["reranking_trace"]["fallback"])
        self.assertEqual(update["reranking_trace"]["candidate_count"], 0)
        self.assertEqual(update["reranking_trace"]["selected_count"], 0)

    def test_get_reranker_imports_cross_encoder_lazily_and_caches_instance(self) -> None:
        get_reranker.cache_clear()
        calls: list[tuple[str, int]] = []

        class FakeCrossEncoder:
            def __init__(self, model_name: str, max_length: int) -> None:
                calls.append((model_name, max_length))

        fake_module = types.SimpleNamespace(CrossEncoder=FakeCrossEncoder)

        with patch.dict(sys.modules, {"sentence_transformers": fake_module}):
            first = get_reranker("fake-model", 128)
            second = get_reranker("fake-model", 128)

        self.assertIs(first, second)
        self.assertEqual(calls, [("fake-model", 128)])


class FakeReranker:
    """Fake CrossEncoder-like reranker returning deterministic scores."""

    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.pairs: list[tuple[str, str]] = []

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        self.pairs = pairs
        return self.scores


class FailingReranker:
    """Fake CrossEncoder-like reranker that fails during scoring."""

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        raise RuntimeError("predict failed")


if __name__ == "__main__":
    unittest.main()
