"""Tests for SG-SST LLM-based query expansion before LangGraph retrieval."""

import sys
import types
import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.query_understanding import query_expansion


class LangChainRagQueryExpansionTest(unittest.TestCase):
    """Verify query expansion guardrails with fakes only."""

    def test_successful_expansion_writes_retrieval_query_and_trace(self) -> None:
        llm = FakeStructuredLlm(["COPASST", "Comité Paritario de Seguridad y Salud en el Trabajo"])

        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}):
            update = query_expansion.query_expansion_node(llm)({"question": "¿Cada cuánto toca capacitar al comité?"})

        self.assertEqual(llm.method, "function_calling")
        self.assertEqual(
            update["retrieval_query"],
            "¿Cada cuánto toca capacitar al comité? COPASST Comité Paritario de Seguridad y Salud en el Trabajo",
        )
        self.assertEqual(
            update["query_expansion_trace"],
            {
                "technique": "llm_query_expansion",
                "expansion_terms": ["COPASST", "Comité Paritario de Seguridad y Salud en el Trabajo"],
                "changed": True,
                "fallback": False,
                "error": None,
            },
        )

    def test_blank_original_question_falls_back_without_invocation(self) -> None:
        llm = FakeStructuredLlm(["COPASST"])
        update = query_expansion.query_expansion_node(llm)({"question": "   "})

        self.assertEqual(llm.invoke_count, 0)
        self.assertEqual(update["retrieval_query"], "   ")
        self.assertEqual(
            update["query_expansion_trace"],
            {
                "technique": "llm_query_expansion",
                "expansion_terms": [],
                "changed": False,
                "fallback": True,
                "error": "blank_question",
            },
        )

    def test_empty_structured_output_returns_original_question_without_fallback(self) -> None:
        llm = FakeStructuredLlm([])

        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}):
            update = query_expansion.query_expansion_node(llm)({"question": "Pregunta original"})

        self.assertEqual(update["retrieval_query"], "Pregunta original")
        self.assertEqual(update["query_expansion_trace"]["expansion_terms"], [])
        self.assertEqual(update["query_expansion_trace"]["fallback"], False)
        self.assertEqual(update["query_expansion_trace"]["changed"], False)
        self.assertIsNone(update["query_expansion_trace"]["error"])

    def test_invocation_exception_falls_back_to_original_question(self) -> None:
        llm = FakeStructuredLlm(RuntimeError("fake failure"))

        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}):
            update = query_expansion.query_expansion_node(llm)({"question": "Pregunta original"})

        self.assertEqual(update["retrieval_query"], "Pregunta original")
        self.assertEqual(update["query_expansion_trace"]["expansion_terms"], [])
        self.assertEqual(update["query_expansion_trace"]["fallback"], True)
        self.assertEqual(update["query_expansion_trace"]["error"], "RuntimeError")

    def test_duplicate_and_already_present_terms_are_removed(self) -> None:
        llm = FakeStructuredLlm([" SG-SST ", "sg-sst", "empleador", "COPASST"])

        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}):
            update = query_expansion.query_expansion_node(llm)({"question": "Obligaciones del empleador SG-SST"})

        self.assertEqual(update["retrieval_query"], "Obligaciones del empleador SG-SST COPASST")
        self.assertEqual(update["query_expansion_trace"]["expansion_terms"], ["COPASST"])

    def test_terms_that_introduce_normative_identifiers_are_removed(self) -> None:
        llm = FakeStructuredLlm(
            [
                "Decreto 1072 de 2015",
                "Ley 1562",
                "Resolución 0312 de 2019",
                "CIIU 6920",
                "artículo 2",
                "numeral 4.1",
                "literal a",
                "parágrafo 1",
                "tabla 1",
                "riesgo II",
                "COPASST",
            ]
        )

        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}):
            update = query_expansion.query_expansion_node(llm)({"question": "¿Qué debe hacer la empresa?"})

        self.assertEqual(update["retrieval_query"], "¿Qué debe hacer la empresa? COPASST")
        self.assertEqual(update["query_expansion_trace"]["expansion_terms"], ["COPASST"])

    def test_allows_identifiers_already_present_in_original_question(self) -> None:
        original = "CIIU 6920 numeral 4.1 literal a parágrafo 1"
        terms = query_expansion.clean_expansion_terms(original, ["código CIIU 6920", "numeral 4.1", "clase de riesgo"])

        self.assertEqual(terms, ["código CIIU 6920", "clase de riesgo"])

    def test_limits_expansion_terms(self) -> None:
        terms = query_expansion.clean_expansion_terms("Pregunta", [f"term {index}" for index in range(10)])

        self.assertEqual(terms, ["term 0", "term 1", "term 2", "term 3", "term 4", "term 5"])


class FakeStructuredLlm:
    """Small LangChain-like fake for structured query expansion."""

    def __init__(self, expansion_terms: list[str] | Exception) -> None:
        self.expansion_terms = expansion_terms
        self.invoke_count = 0
        self.method = None

    def with_structured_output(self, schema: object, method: str) -> object:
        self.schema = schema
        self.method = method
        return self

    def invoke(self, messages: list[object]) -> object:
        self.invoke_count += 1
        if isinstance(self.expansion_terms, Exception):
            raise self.expansion_terms
        return types.SimpleNamespace(expansion_terms=self.expansion_terms)


def fake_message_module() -> object:
    """Return fake LangChain message classes for lazy-import tests."""

    class SystemMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class HumanMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    return types.SimpleNamespace(SystemMessage=SystemMessage, HumanMessage=HumanMessage)


if __name__ == "__main__":
    unittest.main()
