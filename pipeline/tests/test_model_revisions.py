"""Tests for pinned Hugging Face model revisions in the offline pipeline."""

import sys
import types
import unittest
from unittest.mock import patch

from pipeline.chunking.config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_MODEL_REVISION,
)
from pipeline.chunking.hierarchical_splitter import tokenization
from pipeline.chunking.hierarchical_splitter.child_splitter.shared import embedding_kwargs_for_model
from pipeline.vectorization import chroma_store


class PipelineModelRevisionTest(unittest.TestCase):
    def setUp(self) -> None:
        tokenization.get_tokenizer.cache_clear()

    def tearDown(self) -> None:
        tokenization.get_tokenizer.cache_clear()

    def test_default_embedding_revision_is_a_full_commit_hash(self) -> None:
        self.assertRegex(DEFAULT_EMBEDDING_MODEL_REVISION, r"^[0-9a-f]{40}$")

    def test_default_tokenizer_loads_pinned_revision(self) -> None:
        fake_auto_tokenizer = RecordingAutoTokenizer()

        with patch.object(tokenization, "AutoTokenizer", fake_auto_tokenizer):
            tokenization.get_tokenizer()

        self.assertEqual(
            fake_auto_tokenizer.calls,
            [(DEFAULT_EMBEDDING_MODEL, DEFAULT_EMBEDDING_MODEL_REVISION)],
        )

    def test_other_tokenizer_model_keeps_unpinned_revision(self) -> None:
        fake_auto_tokenizer = RecordingAutoTokenizer()

        with patch.object(tokenization, "AutoTokenizer", fake_auto_tokenizer):
            tokenization.get_tokenizer("intfloat/multilingual-e5-small")

        self.assertEqual(fake_auto_tokenizer.calls, [("intfloat/multilingual-e5-small", None)])

    def test_semantic_embeddings_load_pinned_revision_for_default_model(self) -> None:
        kwargs = embedding_kwargs_for_model(DEFAULT_EMBEDDING_MODEL)

        self.assertEqual(kwargs["model_kwargs"], {"revision": DEFAULT_EMBEDDING_MODEL_REVISION})
        self.assertEqual(kwargs["encode_kwargs"], {"normalize_embeddings": True})
        self.assertEqual(kwargs["query_encode_kwargs"], {"normalize_embeddings": True})

    def test_semantic_embeddings_for_other_models_keep_previous_options(self) -> None:
        kwargs = embedding_kwargs_for_model("intfloat/multilingual-e5-small")

        self.assertEqual(
            kwargs,
            {
                "encode_kwargs": {"normalize_embeddings": True, "prompt": "passage: "},
                "query_encode_kwargs": {"normalize_embeddings": True, "prompt": "query: "},
            },
        )

    def test_vectorization_embedding_function_loads_pinned_revision(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_embedding_function(**kwargs: object) -> object:
            calls.append(kwargs)
            return "embedding-function"

        fake_module = types.SimpleNamespace(SentenceTransformerEmbeddingFunction=fake_embedding_function)

        with patch.dict(sys.modules, {"chromadb.utils.embedding_functions": fake_module}):
            embedding_function = chroma_store.qwen_embedding_function()

        self.assertEqual(embedding_function, "embedding-function")
        self.assertEqual(
            calls,
            [{"model_name": DEFAULT_EMBEDDING_MODEL, "revision": DEFAULT_EMBEDDING_MODEL_REVISION}],
        )


class RecordingAutoTokenizer:
    """AutoTokenizer fake that records the requested model and revision."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def from_pretrained(self, model_name: str, revision: object = None, use_fast: bool = True) -> object:
        self.calls.append((model_name, revision))
        return object()


if __name__ == "__main__":
    unittest.main()
