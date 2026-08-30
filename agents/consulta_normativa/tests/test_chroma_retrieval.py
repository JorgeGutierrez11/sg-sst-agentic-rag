"""Tests for runtime Chroma retrieval helpers."""

import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.retrieval import chroma_retrieval


class ChromaRetrievalTest(unittest.TestCase):
    """Verify Chroma retriever adapters stay query-only and delegate work."""

    def test_chroma_retriever_delegates_to_query_top_k(self) -> None:
        collection = object()
        expected_result = {
            "ids": [["child-1"]],
            "documents": [["Texto normativo."]],
            "metadatas": [[{"document_type": "child_chunk"}]],
            "distances": [[0.2]],
        }

        with patch.object(chroma_retrieval, "query_top_k", return_value=expected_result) as query_top_k:
            retrieve = chroma_retrieval.chroma_retriever(collection)
            result = retrieve("¿Qué exige el SG-SST?", 4)

        self.assertIs(result, expected_result)
        query_top_k.assert_called_once_with(collection, "¿Qué exige el SG-SST?", 4)


if __name__ == "__main__":
    unittest.main()
