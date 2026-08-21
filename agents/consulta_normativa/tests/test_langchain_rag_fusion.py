"""Tests for Multi-Query retrieval fusion."""

import unittest

from agents.consulta_normativa.langchain_rag.models import RetrievedDocument
from agents.consulta_normativa.langchain_rag.retrieval.fusion import (
    document_identity,
    reciprocal_rank_fusion,
    retrieve_variant_node,
    rrf_fuse_node,
)


class LangChainRagFusionTest(unittest.TestCase):
    """Verify document identity, variant retrieval, and RRF behavior."""

    def test_document_identity_uses_chroma_id_first(self) -> None:
        document = RetrievedDocument("texto", {"_chroma_id": "chunk-1", "chunk_id": "chunk-1", "source_stem": "source"})

        self.assertEqual(document_identity(document), "id:chunk-1")

    def test_document_identity_falls_back_for_chunk_metadata_without_chroma_id(self) -> None:
        document = RetrievedDocument(
            "texto",
            {"source_stem": "res-0312", "parent_id": "art-1", "start_char": 10, "end_char": 20},
        )

        identity = document_identity(document)

        self.assertTrue(identity.startswith("fallback:res-0312 (tipo desconocido):"))

    def test_document_identity_falls_back_for_table_metadata_without_chroma_id(self) -> None:
        document = RetrievedDocument(
            "tabla",
            {"source_document_id": "res-0312", "table_key": "standards", "table_part_index": 0},
        )

        identity = document_identity(document)

        self.assertTrue(identity.startswith("fallback:res-0312 (tipo desconocido):"))

    def test_document_identity_falls_back_to_reference_and_text_hash(self) -> None:
        document = RetrievedDocument("texto sin metadata estable", {"source_stem": "res-0312"})

        identity = document_identity(document)

        self.assertTrue(identity.startswith("fallback:res-0312 (tipo desconocido):"))

    def test_reciprocal_rank_fusion_deduplicates_and_boosts_repeated_documents(self) -> None:
        top_once = RetrievedDocument("solo top", {"_chroma_id": "top-once"})
        repeated_low_first = RetrievedDocument("repetido", {"_chroma_id": "repeated"})
        middle_once = RetrievedDocument("solo medio", {"_chroma_id": "middle-once"})
        repeated_high_second = RetrievedDocument("repetido actualizado", {"_chroma_id": "repeated"})

        fused = reciprocal_rank_fusion(
            [[top_once, middle_once, repeated_low_first], [repeated_high_second]],
            k=60,
        )

        self.assertEqual([document_identity(document) for document in fused], ["id:repeated", "id:top-once", "id:middle-once"])
        self.assertIs(fused[0], repeated_low_first)

    def test_rrf_fuse_node_writes_documents_only(self) -> None:
        first = RetrievedDocument("first", {"_chroma_id": "first"})
        second = RetrievedDocument("second", {"_chroma_id": "second"})

        update = rrf_fuse_node(rrf_k=60, top_k=1)({"retrieved_lists": [[first], [second]]})

        self.assertEqual(update, {"documents": [first]})

    def test_retrieve_variant_node_normalizes_one_variant_result(self) -> None:
        calls: list[tuple[str, int]] = []

        def retriever(query: str, top_k: int) -> dict[str, object]:
            calls.append((query, top_k))
            return {"documents": [["texto"]], "metadatas": [[{"chunk_id": "doc-1"}]]}

        update = retrieve_variant_node(retriever, top_k=2)({"query": "consulta normativa"})

        self.assertEqual(calls, [("consulta normativa", 2)])
        self.assertEqual(update, {"retrieved_lists": [[RetrievedDocument("texto", {"chunk_id": "doc-1"})]]})


if __name__ == "__main__":
    unittest.main()
