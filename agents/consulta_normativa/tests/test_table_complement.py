"""Tests for deterministic linked-table complementation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agents.consulta_normativa.langchain_rag.models import RetrievedDocument
from agents.consulta_normativa.langchain_rag.retrieval.table_complement import (
    complement_linked_tables,
    load_first_table_parts,
)


class TableComplementTest(unittest.TestCase):
    """Verify first-part lookup and relation-based document complementation."""

    def test_linked_key_appends_first_table_part_with_citation_metadata(self) -> None:
        source = RetrievedDocument("Relevant source", {"document_id": "parent-1", "table_keys": "source-a:0"})
        table = table_document("table-a-part-0", "source-a:0", "First table part")

        complemented = complement_linked_tables([source], {"source-a:0": table})

        self.assertEqual(complemented, [source, table])
        self.assertEqual(
            complemented[1].metadata,
            {
                "document_id": "table-a-part-0",
                "document_type": "table",
                "table_key": "source-a:0",
                "table_part_index": 0,
                "table_part_count": 2,
                "source_stem": "source-a",
                "table_index": 0,
            },
        )

    def test_repeated_keys_append_once_in_source_relation_order(self) -> None:
        sources = [
            RetrievedDocument("First", {"document_id": "parent-1", "table_keys": ["source-b:1", "source-a:0"]}),
            RetrievedDocument("Second", {"document_id": "parent-2", "table_keys": "source-a:0,source-c:2"}),
        ]
        lookup = {
            "source-a:0": table_document("table-a", "source-a:0", "Table A"),
            "source-b:1": table_document("table-b", "source-b:1", "Table B", table_index=1),
            "source-c:2": table_document("table-c", "source-c:2", "Table C", table_index=2),
        }

        complemented = complement_linked_tables(sources, lookup)

        self.assertEqual(complemented[:2], sources)
        self.assertEqual(
            [document.metadata["table_key"] for document in complemented[2:]],
            ["source-b:1", "source-a:0", "source-c:2"],
        )

    def test_globally_retrieved_table_part_is_not_duplicated(self) -> None:
        source = RetrievedDocument("Source", {"table_keys": "source-a:0"})
        globally_retrieved = table_document("table-a", "source-a:0", "Table A")
        globally_retrieved = RetrievedDocument(
            globally_retrieved.document,
            {**globally_retrieved.metadata, "_document_id": "table-a"},
        )
        lookup_copy = table_document("table-a", "source-a:0", "Table A")

        complemented = complement_linked_tables(
            [source, globally_retrieved],
            {"source-a:0": lookup_copy},
        )

        self.assertEqual(complemented, [source, globally_retrieved])

    def test_table_relation_deduplicates_when_document_ids_differ(self) -> None:
        source = RetrievedDocument("Source", {"table_keys": "source-a:0"})
        globally_retrieved = table_document("global-table-id", "source-a:0", "Table A")
        lookup_copy = table_document("lookup-table-id", "source-a:0", "Table A")

        complemented = complement_linked_tables(
            [source, globally_retrieved],
            {"source-a:0": lookup_copy},
        )

        self.assertEqual(complemented, [source, globally_retrieved])

    def test_missing_lookup_key_and_empty_documents_are_no_ops(self) -> None:
        source = RetrievedDocument("Source", {"table_keys": "missing:0"})
        source_without_key = RetrievedDocument("Source without table", {"document_id": "parent-2"})

        self.assertEqual(complement_linked_tables([source], {}), [source])
        self.assertEqual(
            complement_linked_tables(
                [source_without_key],
                {"missing:0": table_document("table", "missing:0", "Table")},
            ),
            [source_without_key],
        )
        self.assertEqual(
            complement_linked_tables([], {"missing:0": table_document("table", "missing:0", "Table")}),
            [],
        )

    def test_loader_keeps_only_part_zero_and_returns_empty_for_missing_file(self) -> None:
        records = [
            table_record("table-a-part-1", "source-a:0", 1, "Later part"),
            table_record("table-a-part-0", "source-a:0", 0, "  First part\n"),
            table_record("table-b-part-2", "source-b:1", 2, "Another later part", table_index=1),
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "table_documents.jsonl"
            path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

            lookup = load_first_table_parts(path)

            self.assertEqual(set(lookup), {"source-a:0"})
            loaded_table = lookup["source-a:0"]
            self.assertEqual(loaded_table.document, "  First part\n")
            self.assertEqual(loaded_table.metadata["document_id"], "table-a-part-0")
            self.assertEqual(loaded_table.metadata["document_type"], "table")
            self.assertEqual(loaded_table.metadata["table_key"], "source-a:0")
            self.assertEqual(loaded_table.metadata["table_part_index"], 0)
            self.assertEqual(loaded_table.metadata["table_part_count"], 3)
            self.assertEqual(loaded_table.metadata["source_stem"], "source-a")
            self.assertEqual(loaded_table.metadata["table_index"], 0)
            self.assertEqual(loaded_table.metadata["linked_placeholder"], "<!-- TABLE_0 -->")
            self.assertEqual(load_first_table_parts(path.with_name("missing.jsonl")), {})

    def test_loader_propagates_controlled_error_for_malformed_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "table_documents.jsonl"
            path.write_text("not-json", encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                rf"Invalid JSONL in {path} at line 1",
            ):
                load_first_table_parts(path)


def table_document(
    document_id: str,
    table_key: str,
    text: str,
    *,
    table_index: int = 0,
) -> RetrievedDocument:
    """Build a table document fixture."""

    return RetrievedDocument(
        text,
        {
            "document_id": document_id,
            "document_type": "table",
            "table_key": table_key,
            "table_part_index": 0,
            "table_part_count": 2,
            "source_stem": table_key.rsplit(":", maxsplit=1)[0],
            "table_index": table_index,
        },
    )


def table_record(
    document_id: str,
    table_key: str,
    part_index: int,
    text: str,
    *,
    table_index: int = 0,
) -> dict[str, object]:
    """Build a JSONL table record fixture."""

    return {
        "id": document_id,
        "text": text,
        "metadata": {
            "type": "table",
            "table_key": table_key,
            "table_part_index": part_index,
            "table_part_count": 3,
            "source_stem": table_key.rsplit(":", maxsplit=1)[0],
            "table_index": table_index,
            "linked_placeholder": "<!-- TABLE_0 -->",
        },
    }


if __name__ == "__main__":
    unittest.main()
