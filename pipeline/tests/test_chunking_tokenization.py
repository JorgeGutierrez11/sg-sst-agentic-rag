"""Tests for Hugging Face tokenizer integration."""

import unittest
from unittest.mock import patch

from pipeline.chunking.hierarchical_splitter import tokenization


class ChunkingTokenizationTest(unittest.TestCase):
    def setUp(self) -> None:
        tokenization.get_tokenizer.cache_clear()

    def tearDown(self) -> None:
        tokenization.get_tokenizer.cache_clear()

    def test_estimate_token_count_uses_cached_auto_tokenizer_without_special_tokens(self) -> None:
        fake_auto_tokenizer = FakeAutoTokenizer()
        with patch.object(tokenization, "AutoTokenizer", fake_auto_tokenizer):
            self.assertEqual(tokenization.estimate_token_count("uno dos"), 2)
            self.assertEqual(tokenization.estimate_token_count("tres cuatro"), 2)

        self.assertEqual(fake_auto_tokenizer.load_count, 1)
        self.assertEqual(fake_auto_tokenizer.tokenizer.encode_calls, [False, False])

    def test_token_offsets_use_fast_offset_mapping_and_filter_empty_offsets(self) -> None:
        fake_auto_tokenizer = FakeAutoTokenizer(offsets=[(0, 3), (3, 3), (4, 7)])
        with patch.object(tokenization, "AutoTokenizer", fake_auto_tokenizer):
            self.assertEqual(tokenization.token_offsets("uno dos"), [(0, 3), (4, 7)])

        self.assertEqual(fake_auto_tokenizer.tokenizer.call_kwargs["add_special_tokens"], False)
        self.assertEqual(fake_auto_tokenizer.tokenizer.call_kwargs["return_offsets_mapping"], True)

    def test_missing_transformers_raises_controlled_runtime_error_when_tokenizer_is_needed(self) -> None:
        with patch.object(tokenization, "AutoTokenizer", None):
            with self.assertRaisesRegex(RuntimeError, "install 'transformers'"):
                tokenization.estimate_token_count("texto")

    def test_token_offsets_reject_non_fast_tokenizer_with_controlled_runtime_error(self) -> None:
        fake_auto_tokenizer = FakeAutoTokenizer(is_fast=False)
        with patch.object(tokenization, "AutoTokenizer", fake_auto_tokenizer):
            with self.assertRaisesRegex(RuntimeError, "requires a fast Hugging Face tokenizer"):
                tokenization.token_offsets("uno dos")


class FakeAutoTokenizer:
    def __init__(self, offsets: list[tuple[int, int]] | None = None, is_fast: bool = True) -> None:
        self.load_count = 0
        self.tokenizer = FakeTokenizer(offsets or [(0, 3), (4, 7)], is_fast)

    def from_pretrained(self, model_name: str, use_fast: bool = True) -> "FakeTokenizer":
        self.load_count += 1
        return self.tokenizer


class FakeTokenizer:
    def __init__(self, offsets: list[tuple[int, int]], is_fast: bool = True) -> None:
        self.offsets = offsets
        self.is_fast = is_fast
        self.encode_calls: list[bool] = []
        self.call_kwargs: dict[str, bool] = {}

    def encode(self, text: str, add_special_tokens: bool = False) -> list[str]:
        self.encode_calls.append(add_special_tokens)
        return text.split()

    def __call__(self, text: str, add_special_tokens: bool = False, return_offsets_mapping: bool = False) -> dict:
        self.call_kwargs = {
            "add_special_tokens": add_special_tokens,
            "return_offsets_mapping": return_offsets_mapping,
        }
        return {"offset_mapping": self.offsets}


if __name__ == "__main__":
    unittest.main()
