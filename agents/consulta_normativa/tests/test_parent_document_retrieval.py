"""Tests for runtime parent-document retrieval expansion."""

import json
import tempfile
import unittest
from pathlib import Path

from agents.consulta_normativa.langchain_rag.models import RetrievedDocument
from agents.consulta_normativa.langchain_rag.retrieval.parent_document_retrieval import (
    build_parent_lookup,
    expand_parent_documents,
    load_parent_documents,
    parent_child_consistency_report,
)


class ParentDocumentRetrievalTest(unittest.TestCase):
    """Verify parent loading, expansion, deduplication, and fallback behavior."""

    def test_loader_missing_file_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "Parent chunks JSONL not found"):
            load_parent_documents(Path("/tmp/missing-parent-chunks.jsonl"))

    def test_loader_builds_lookup_by_chunk_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            parents_path = Path(temporary_directory) / "parents.jsonl"
            self.write_jsonl(parents_path, [self.parent_record("parent-1", "Full parent text")])

            lookup = load_parent_documents(parents_path)

        self.assertEqual(list(lookup), ["parent-1"])
        self.assertEqual(lookup["parent-1"].document, "Full parent text")
        self.assertEqual(lookup["parent-1"].metadata["document_id"], "parent-1")
        self.assertEqual(lookup["parent-1"].metadata["document_type"], "parent_chunk")
        self.assertEqual(lookup["parent-1"].metadata["source_stem"], "Resolución 0312 de 2019")
        self.assertEqual(lookup["parent-1"].metadata["normative_document_type"], "resolución")
        self.assertEqual(lookup["parent-1"].metadata["year"], 2019)
        self.assertEqual(lookup["parent-1"].metadata["chapter"], "I")
        self.assertEqual(lookup["parent-1"].metadata["article"], "1")
        self.assertEqual(lookup["parent-1"].metadata["parent_strategy"], "regex_constrained_semantic")
        self.assertTrue(lookup["parent-1"].metadata["has_tables"])
        self.assertEqual(lookup["parent-1"].metadata["table_keys"], "Resolución 0312 de 2019:0")

    def test_parent_child_consistency_report_counts_missing_parents(self) -> None:
        parent_lookup = build_parent_lookup([self.parent_record("parent-1", "Parent text")])
        report = parent_child_consistency_report(
            [
                {"chunk_id": "child-1", "parent_id": "parent-1"},
                {"chunk_id": "child-2", "parent_id": "parent-missing"},
                {"chunk_id": "child-3", "parent_id": ""},
            ],
            parent_lookup,
        )

        self.assertEqual(report.total_child_chunks, 3)
        self.assertEqual(report.children_with_parent_id, 2)
        self.assertEqual(report.children_with_missing_parent, 1)
        self.assertEqual(report.missing_parent_ratio, 0.5)

    def test_child_with_valid_parent_expands_to_full_parent_text(self) -> None:
        child = self.child_document("child-1", "parent-1", "Small child text")
        parent_lookup = {"parent-1": self.parent_document("parent-1", "Full parent text")}

        expanded = expand_parent_documents([child], parent_lookup)

        self.assertEqual([document.document for document in expanded], ["Full parent text"])
        self.assertTrue(expanded[0].metadata["parent_expansion_applied"])
        self.assertEqual(expanded[0].metadata["expanded_parent_id"], "parent-1")
        self.assertEqual(expanded[0].metadata["expanded_from_child_id"], "child-1")
        self.assertEqual(expanded[0].metadata["expanded_from_child_ids"], ["child-1"])
        self.assertEqual(expanded[0].metadata["expanded_from_document_type"], "child_chunk")

    def test_table_document_is_preserved_unchanged(self) -> None:
        table = RetrievedDocument("Table evidence", {"document_type": "table", "table_key": "source:0"})

        expanded = expand_parent_documents([table], {"parent-1": self.parent_document("parent-1", "Parent")})

        self.assertIs(expanded[0], table)

    def test_two_children_same_parent_produce_one_parent_with_all_child_ids(self) -> None:
        first_child = self.child_document("child-1", "parent-1", "First child")
        second_child = self.child_document("child-2", "parent-1", "Second child")

        expanded = expand_parent_documents(
            [first_child, second_child],
            {"parent-1": self.parent_document("parent-1", "Full parent text")},
        )

        self.assertEqual(len(expanded), 1)
        self.assertEqual(expanded[0].document, "Full parent text")
        self.assertEqual(expanded[0].metadata["expanded_from_child_id"], "child-1")
        self.assertEqual(expanded[0].metadata["expanded_from_child_ids"], ["child-1", "child-2"])

    def test_missing_parent_preserves_child_and_marks_fallback(self) -> None:
        child = self.child_document("child-1", "parent-missing", "Small child text")

        expanded = expand_parent_documents([child], {})

        self.assertEqual(expanded[0].document, "Small child text")
        self.assertEqual(expanded[0].metadata["parent_expansion_fallback"], "missing_parent")

    def test_ranking_order_is_preserved_after_expansion_and_deduplication(self) -> None:
        table = RetrievedDocument("Table evidence", {"document_type": "table"})
        first_child = self.child_document("child-1", "parent-1", "First child")
        second_child = self.child_document("child-2", "parent-2", "Second child")
        repeated_parent_child = self.child_document("child-3", "parent-1", "Repeated parent child")

        expanded = expand_parent_documents(
            [table, first_child, second_child, repeated_parent_child],
            {
                "parent-1": self.parent_document("parent-1", "First parent"),
                "parent-2": self.parent_document("parent-2", "Second parent"),
            },
        )

        self.assertEqual([document.document for document in expanded], ["Table evidence", "First parent", "Second parent"])
        self.assertEqual(expanded[1].metadata["expanded_from_child_ids"], ["child-1", "child-3"])

    def parent_record(self, chunk_id: str, text: str) -> dict[str, object]:
        return {
            "chunk_id": chunk_id,
            "source_document_id": "source-1",
            "source_path": "data/processed/Resolución 0312 de 2019.md",
            "parent_index": 0,
            "text": text,
            "start_char": 10,
            "end_char": 90,
            "token_count": 20,
            "metadata": {
                "inherited": {
                    "source_stem": "Resolución 0312 de 2019",
                    "document_type": "resolución",
                    "year": 2019,
                    "hierarchy": {"chapter": "I", "article": "1"},
                },
                "chunk": {
                    "strategy": "regex_constrained_semantic",
                    "tables": [{"source_stem": "Resolución 0312 de 2019", "table_index": 0}],
                },
            },
        }

    def parent_document(self, parent_id: str, text: str) -> RetrievedDocument:
        return RetrievedDocument(text, {"document_id": parent_id, "document_type": "parent_chunk", "source_stem": "Decreto"})

    def child_document(self, child_id: str, parent_id: str, text: str) -> RetrievedDocument:
        return RetrievedDocument(
            text,
            {
                "_document_id": child_id,
                "document_id": child_id,
                "document_type": "child_chunk",
                "parent_id": parent_id,
                "source_stem": "Decreto",
            },
        )

    def write_jsonl(self, path: Path, records: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8") as output_file:
            for record in records:
                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    unittest.main()
