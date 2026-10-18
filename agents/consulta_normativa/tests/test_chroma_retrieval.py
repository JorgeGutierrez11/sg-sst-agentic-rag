"""Tests for runtime Chroma retrieval helpers."""

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
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


class ChromaWorkingCopyTest(unittest.TestCase):
    """Verify the runtime queries a disposable copy and never writes the published index."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source = self.root / "published" / "chroma"
        create_source_index(self.source)

    def tearDown(self) -> None:
        make_writable(self.root)
        self.directory.cleanup()

    def test_querying_working_copy_leaves_source_files_unchanged(self) -> None:
        before = file_hashes(self.source)

        working_copy = chroma_retrieval.create_working_copy(self.source)
        try:
            collection = open_collection(working_copy.path)
            self.assertEqual(collection.count(), 2)
            self.assertEqual(query_ids(collection), ["a"])
        finally:
            working_copy.cleanup()

        self.assertEqual(file_hashes(self.source), before)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores file permissions")
    def test_working_copy_of_read_only_source_can_be_queried(self) -> None:
        make_read_only(self.source)

        working_copy = chroma_retrieval.create_working_copy(self.source)
        try:
            self.assertEqual(query_ids(open_collection(working_copy.path)), ["a"])
        finally:
            working_copy.cleanup()

    def test_working_copy_is_created_under_configured_root(self) -> None:
        working_root = self.root / "working"

        working_copy = chroma_retrieval.create_working_copy(self.source, working_root)
        try:
            self.assertTrue(working_copy.path.is_relative_to(working_root.resolve()))
            self.assertTrue((working_copy.path / "chroma.sqlite3").is_file())
        finally:
            working_copy.cleanup()

    def test_working_root_inside_source_index_is_rejected(self) -> None:
        with self.assertRaises(ValueError) as raised:
            chroma_retrieval.create_working_copy(self.source, self.source / "working")

        self.assertIn("RAG_CHROMA_WORKING_DIR", str(raised.exception))
        self.assertFalse((self.source / "working").exists())

    def test_cleanup_removes_working_copy(self) -> None:
        working_copy = chroma_retrieval.create_working_copy(self.source)

        working_copy.cleanup()

        self.assertFalse(working_copy.path.exists())

    def test_working_copy_refuses_directories_it_did_not_create(self) -> None:
        with self.assertRaises(ValueError):
            chroma_retrieval.ChromaWorkingCopy(self.source.parent)

        self.assertTrue((self.source / "chroma.sqlite3").is_file())

    def test_missing_source_index_raises_error(self) -> None:
        missing = self.root / "missing"

        with self.assertRaises(ValueError) as raised:
            chroma_retrieval.create_working_copy(missing)

        self.assertEqual(str(raised.exception), f"ChromaDB persist path does not exist: {missing}")


def create_source_index(path: Path) -> None:
    """Create a two-record Chroma index with explicit embeddings and no model download."""

    import chromadb

    client = chromadb.PersistentClient(path=str(path))
    collection = client.create_collection(chroma_retrieval.DEFAULT_COLLECTION_NAME, embedding_function=None)
    collection.add(ids=["a", "b"], embeddings=[[1.0, 0.0], [0.0, 1.0]], documents=["x", "y"])


def open_collection(path: Path) -> object:
    with patch.object(chroma_retrieval, "qwen_embedding_function", return_value=None):
        return chroma_retrieval.open_existing_collection(path)


def query_ids(collection: object) -> list[str]:
    return collection.query(query_embeddings=[[1.0, 0.0]], n_results=1, include=[])["ids"][0]


def file_hashes(path: Path) -> dict[str, str]:
    return {
        str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def make_read_only(path: Path) -> None:
    for item in (path, *path.rglob("*")):
        item.chmod(item.stat().st_mode & ~0o222)


def make_writable(path: Path) -> None:
    for item in (path, *path.rglob("*")):
        item.chmod(item.stat().st_mode | 0o200)


if __name__ == "__main__":
    unittest.main()
