"""Tests for runtime Hybrid Retrieval helpers."""

import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.retrieval import hybrid_retrieval


class HybridRetrievalTest(unittest.TestCase):
    """Verify Chroma and BM25 retrieval are fused without score mixing."""

    def test_hybrid_retriever_calls_dense_and_sparse_for_same_query(self) -> None:
        calls: list[tuple[str, str, int]] = []

        with patch.object(
            hybrid_retrieval.chroma_retrieval,
            "query_top_k",
            side_effect=lambda collection, query, top_k: calls.append(("dense", query, top_k)) or empty_result(),
        ), patch.object(
            hybrid_retrieval.bm25_retrieval,
            "query_top_k",
            side_effect=lambda index, query, top_k: calls.append(("sparse", query, top_k)) or empty_result(),
        ):
            retriever = hybrid_retrieval.hybrid_retriever(
                "collection",
                "index",
                candidate_top_k=10,
                rrf_k=60,
            )
            retriever("consulta", 5)

        self.assertEqual(calls, [("dense", "consulta", 10), ("sparse", "consulta", 10)])

    def test_rrf_fuses_rankings_and_deduplicates_same_id(self) -> None:
        result = run_hybrid(
            dense_result=raw_result([("shared", "Dense shared", {}), ("dense-only", "Dense only", {})]),
            sparse_result=raw_result([("sparse-only", "Sparse only", {}), ("shared", "Sparse shared", {})]),
        )

        self.assertEqual(result["ids"], [["id:shared", "id:sparse-only", "id:dense-only"]])
        self.assertEqual(result["documents"], [["Dense shared", "Sparse only", "Dense only"]])

    def test_fusion_does_not_mix_dense_distances_and_sparse_scores(self) -> None:
        result = run_hybrid(
            dense_result=raw_result([("dense-low-distance", "Dense", {})], distances=[999.0]),
            sparse_result=raw_result([("sparse-high-score", "Sparse", {})], scores=[999.0]),
        )

        self.assertEqual(set(result), {"ids", "documents", "metadatas"})
        self.assertNotIn("distances", result)
        self.assertNotIn("scores", result)

    def test_caller_top_k_controls_final_count(self) -> None:
        result = run_hybrid(
            dense_result=raw_result([("one", "One", {}), ("two", "Two", {}), ("three", "Three", {})]),
            sparse_result=empty_result(),
            requested_top_k=2,
        )
        empty_result_for_non_positive_top_k = run_hybrid(
            dense_result=raw_result([("one", "One", {})]),
            sparse_result=empty_result(),
            requested_top_k=0,
        )

        self.assertEqual(result["ids"], [["id:one", "id:two"]])
        self.assertEqual(empty_result_for_non_positive_top_k, empty_result())

    def test_metadata_is_preserved_for_formatting_and_reference_consumers(self) -> None:
        metadata = {"source_stem": "res-0312", "document_type": "table", "table_index": 0}

        result = run_hybrid(dense_result=raw_result([("table-1", "Table", metadata)]), sparse_result=empty_result())

        self.assertEqual(result["metadatas"][0][0]["source_stem"], "res-0312")
        self.assertEqual(result["metadatas"][0][0]["document_type"], "table")
        self.assertEqual(result["metadatas"][0][0]["table_index"], 0)
        self.assertEqual(result["metadatas"][0][0]["_document_id"], "table-1")
        self.assertNotIn("_chroma_id", result["metadatas"][0][0])

    def test_document_id_metadata_deduplicates_results_across_engines(self) -> None:
        result = run_hybrid(
            dense_result=raw_result([("chroma-id", "Dense shared", {"_document_id": "canonical-id"})]),
            sparse_result=raw_result([("bm25-id", "Sparse shared", {"_document_id": "canonical-id"})]),
        )

        metadata = result["metadatas"][0][0]
        self.assertEqual(result["ids"], [["id:canonical-id"]])
        self.assertEqual(result["documents"], [["Dense shared"]])
        self.assertEqual(metadata["_retrieval_sources"], ["chroma", "bm25"])

    def test_chroma_only_result_has_dense_retrieval_source_metadata(self) -> None:
        result = run_hybrid(dense_result=raw_result([("dense", "Dense", {})]), sparse_result=empty_result())

        metadata = result["metadatas"][0][0]
        self.assertEqual(traceability_metadata(metadata), {"_retrieval_sources": ["chroma"]})

    def test_bm25_only_result_has_sparse_retrieval_source_metadata(self) -> None:
        result = run_hybrid(dense_result=empty_result(), sparse_result=raw_result([("sparse", "Sparse", {})]))

        metadata = result["metadatas"][0][0]
        self.assertEqual(traceability_metadata(metadata), {"_retrieval_sources": ["bm25"]})

    def test_deduplicated_result_has_both_retrieval_sources_metadata(self) -> None:
        result = run_hybrid(
            dense_result=raw_result([("shared", "Dense shared", {})]),
            sparse_result=raw_result([("shared", "Sparse shared", {})]),
        )

        metadata = result["metadatas"][0][0]
        self.assertEqual(result["ids"], [["id:shared"]])
        self.assertEqual(traceability_metadata(metadata), {"_retrieval_sources": ["chroma", "bm25"]})

    def test_one_empty_branch_returns_other_branch_results(self) -> None:
        result = run_hybrid(
            dense_result=empty_result(),
            sparse_result=raw_result([("sparse", "Sparse document", {"source_stem": "decreto-1072"})]),
        )

        self.assertEqual(result["ids"], [["id:sparse"]])
        self.assertEqual(result["documents"], [["Sparse document"]])

    def test_both_empty_branches_return_empty_nested_shape(self) -> None:
        result = run_hybrid(dense_result=empty_result(), sparse_result=empty_result())

        self.assertEqual(result, empty_result())

    def test_output_has_ids_documents_and_metadatas_shape(self) -> None:
        result = run_hybrid(dense_result=raw_result([("doc", "Document", {})]), sparse_result=empty_result())

        self.assertEqual(set(result), {"ids", "documents", "metadatas"})
        self.assertIsInstance(result["ids"][0], list)
        self.assertIsInstance(result["documents"][0], list)
        self.assertIsInstance(result["metadatas"][0], list)

    def test_operational_retrieval_errors_are_propagated(self) -> None:
        with patch.object(
            hybrid_retrieval.chroma_retrieval,
            "query_top_k",
            side_effect=RuntimeError("dense unavailable"),
        ):
            retriever = hybrid_retrieval.hybrid_retriever(
                "collection",
                "index",
                candidate_top_k=10,
                rrf_k=60,
            )

            with self.assertRaisesRegex(RuntimeError, "dense unavailable"):
                retriever("consulta", 5)

    def test_sparse_operational_retrieval_errors_are_propagated(self) -> None:
        with patch.object(hybrid_retrieval.chroma_retrieval, "query_top_k", return_value=empty_result()), patch.object(
            hybrid_retrieval.bm25_retrieval,
            "query_top_k",
            side_effect=RuntimeError("sparse unavailable"),
        ):
            retriever = hybrid_retrieval.hybrid_retriever(
                "collection",
                "index",
                candidate_top_k=10,
                rrf_k=60,
            )

            with self.assertRaisesRegex(RuntimeError, "sparse unavailable"):
                retriever("consulta", 5)


def run_hybrid(
    *,
    dense_result: dict[str, object],
    sparse_result: dict[str, object],
    requested_top_k: int = 5,
) -> dict[str, object]:
    with patch.object(hybrid_retrieval.chroma_retrieval, "query_top_k", return_value=dense_result), patch.object(
        hybrid_retrieval.bm25_retrieval,
        "query_top_k",
        return_value=sparse_result,
    ):
        retriever = hybrid_retrieval.hybrid_retriever(
            "collection",
            "index",
            candidate_top_k=10,
            rrf_k=60,
        )
        return retriever("consulta", requested_top_k)


def raw_result(
    records: list[tuple[str, str, dict[str, object]]],
    *,
    distances: list[float] | None = None,
    scores: list[float] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "ids": [[record_id for record_id, _, _ in records]],
        "documents": [[document for _, document, _ in records]],
        "metadatas": [[metadata for _, _, metadata in records]],
    }
    if distances is not None:
        result["distances"] = [distances]
    if scores is not None:
        result["scores"] = [scores]
    return result


def empty_result() -> dict[str, object]:
    return {"ids": [[]], "documents": [[]], "metadatas": [[]]}


def traceability_metadata(metadata: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in metadata.items()
        if key.startswith("_retrieval") or key.startswith("_retrieved")
    }


if __name__ == "__main__":
    unittest.main()
