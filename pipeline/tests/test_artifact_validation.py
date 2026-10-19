import json
import tempfile
import unittest
from pathlib import Path

from pipeline.artifact_validation import ArtifactValidationError, validate_corpus_artifacts


class ArtifactValidationTest(unittest.TestCase):
    def test_rejects_an_unresolved_child_parent_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._write_artifacts(root, parent_id="missing-parent")

            with self.assertRaisesRegex(ArtifactValidationError, "Missing parent chunks"):
                validate_corpus_artifacts(
                    **paths,
                    chroma_ids_reader=lambda _path: {"child-1", "table-1"},
                    bm25_records_reader=lambda _path: [{"id": "child-1"}, {"id": "table-1"}],
                )

    def test_rejects_mismatched_index_ids_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._write_artifacts(root)

            with self.assertRaisesRegex(ArtifactValidationError, "Index ID mismatch"):
                validate_corpus_artifacts(
                    **paths,
                    chroma_ids_reader=lambda _path: {"child-1"},
                    bm25_records_reader=lambda _path: [{"id": "table-1"}],
                )

    def test_rejects_an_index_missing_source_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._write_artifacts(Path(directory))

            with self.assertRaisesRegex(
                ArtifactValidationError,
                "Index record count mismatch: source has 2 records, Chroma has 1, BM25 has 2",
            ):
                validate_corpus_artifacts(
                    **paths,
                    chroma_ids_reader=lambda _path: {"child-1"},
                    bm25_records_reader=lambda _path: [{"id": "child-1"}, {"id": "table-1"}],
                )

    def test_rejects_duplicate_bm25_records_with_matching_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._write_artifacts(Path(directory))

            with self.assertRaisesRegex(ArtifactValidationError, "Duplicate BM25 record IDs"):
                validate_corpus_artifacts(
                    **paths,
                    chroma_ids_reader=lambda _path: {"child-1", "table-1"},
                    bm25_records_reader=lambda _path: [{"id": "child-1"}, {"id": "table-1"}, {"id": "table-1"}],
                )

    def test_accepts_a_consistent_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._write_artifacts(Path(directory))

            result = validate_corpus_artifacts(
                **paths,
                chroma_ids_reader=lambda _path: {"child-1", "table-1"},
                bm25_records_reader=lambda _path: [{"id": "child-1"}, {"id": "table-1"}],
            )

        self.assertEqual((result.parent_count, result.source_record_count), (1, 2))

    def test_rejects_missing_required_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._write_artifacts(root)
            paths["children_path"].unlink()

            with self.assertRaisesRegex(ArtifactValidationError, "Missing corpus artifact"):
                validate_corpus_artifacts(
                    **paths,
                    chroma_ids_reader=lambda _path: set(),
                    bm25_records_reader=lambda _path: [],
                )

    def _write_artifacts(self, root: Path, parent_id: str = "parent-1") -> dict[str, Path]:
        parents_path = root / "parents.jsonl"
        children_path = root / "children.jsonl"
        tables_path = root / "tables.jsonl"
        chroma_path = root / "chroma"
        bm25_path = root / "bm25"
        chroma_path.mkdir()
        bm25_path.mkdir()
        parents_path.write_text(json.dumps({"chunk_id": "parent-1", "text": "parent"}) + "\n", encoding="utf-8")
        children_path.write_text(
            json.dumps(
                {
                    "chunk_id": "child-1",
                    "parent_id": parent_id,
                    "text": "child",
                    "metadata": {"inherited": {"source_stem": "source"}},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        tables_path.write_text(
            json.dumps(
                {
                    "id": "table-1",
                    "text": "table",
                    "metadata": {"source_stem": "source", "table_index": 0},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "parents_path": parents_path,
            "children_path": children_path,
            "table_documents_path": tables_path,
            "chroma_path": chroma_path,
            "bm25_path": bm25_path,
        }


if __name__ == "__main__":
    unittest.main()
