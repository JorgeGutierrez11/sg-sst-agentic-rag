"""Tests for the sufficient-context gate node."""

import sys
import types
import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.validation.sufficient_context_gate import (
    ContextSufficiency,
    sufficient_context_gate_node,
)


class FakeGrader:
    """Fake structured-output grader for deterministic tests."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.invoke_count = 0

    def invoke(self, messages: list[object]) -> object:
        self.invoke_count += 1
        if isinstance(self.result, Exception):
            raise self.result

        return self.result


class FakeLLM:
    """Fake LLM that returns a configured structured-output grader."""

    def __init__(self, result: object) -> None:
        self.grader = FakeGrader(result)
        self.structured_output_count = 0

    def with_structured_output(
        self,
        schema: object,
        **kwargs: object,
    ) -> FakeGrader:
        self.structured_output_count += 1
        return self.grader


class BrokenStructuredOutputLLM:
    """Fake LLM that fails while configuring structured output."""

    def with_structured_output(
        self,
        schema: object,
        **kwargs: object,
    ) -> object:
        raise RuntimeError("structured output unavailable")


class SufficientContextGateNodeTests(unittest.TestCase):
    """Validate gate outputs and fail-open technical fallback behavior."""

    def test_sufficient_context_writes_trace_without_fallback(self) -> None:
        result = self.run_gate(
            {
                "level": "sufficient",
                "reason": "El contexto contiene la información necesaria.",
                "missing_information": [],
            }
        )

        self.assertEqual(result["context_sufficiency"], ContextSufficiency.SUFFICIENT.value)
        trace = result["sufficient_context_trace"]
        self.assertEqual(trace["level"], "sufficient")
        self.assertEqual(trace["missing_information"], [])
        self.assertFalse(trace["fallback"])
        self.assertIsNone(trace["error"])

    def test_partial_context_writes_trace_and_preserves_missing_information(self) -> None:
        result = self.run_gate(
            {
                "level": "partial",
                "reason": "Falta el plazo solicitado.",
                "missing_information": ["Plazo para realizar la investigación del accidente."],
            }
        )

        self.assertEqual(result["context_sufficiency"], ContextSufficiency.PARTIAL.value)
        trace = result["sufficient_context_trace"]
        self.assertEqual(trace["level"], "partial")
        self.assertEqual(trace["missing_information"], ["Plazo para realizar la investigación del accidente."])
        self.assertFalse(trace["fallback"])
        self.assertIsNone(trace["error"])

    def test_insufficient_context_writes_insufficient(self) -> None:
        result = self.run_gate(
            {
                "level": "insufficient",
                "reason": "El contexto no permite responder la pregunta.",
                "missing_information": ["Evidencia normativa relacionada con la pregunta."],
            }
        )

        self.assertEqual(result["context_sufficiency"], ContextSufficiency.INSUFFICIENT.value)
        trace = result["sufficient_context_trace"]
        self.assertEqual(trace["level"], "insufficient")
        self.assertTrue(trace["missing_information"])
        self.assertFalse(trace["fallback"])
        self.assertIsNone(trace["error"])

    def test_empty_context_is_insufficient_without_invoking_llm(self) -> None:
        llm = FakeLLM(
            {
                "level": "sufficient",
                "reason": "Este resultado no debería utilizarse.",
                "missing_information": [],
            }
        )
        node = sufficient_context_gate_node(llm)

        result = node({"question": "Pregunta cualquiera", "context": ""})

        self.assertEqual(result["context_sufficiency"], ContextSufficiency.INSUFFICIENT.value)
        self.assertEqual(llm.structured_output_count, 0)
        self.assertEqual(llm.grader.invoke_count, 0)
        trace = result["sufficient_context_trace"]
        self.assertEqual(trace["level"], "insufficient")
        self.assertFalse(trace["fallback"])
        self.assertIsNone(trace["error"])
        self.assertTrue(trace["missing_information"])

    def test_structured_output_failure_uses_technical_fallback(self) -> None:
        node = sufficient_context_gate_node(BrokenStructuredOutputLLM())

        result = node(self.answerable_state())

        self.assert_technical_fallback(result, "RuntimeError")

    def test_grader_invoke_failure_uses_technical_fallback(self) -> None:
        result = self.run_gate(RuntimeError("grader unavailable"))

        self.assert_technical_fallback(result, "RuntimeError")

    def test_malformed_llm_output_uses_technical_fallback(self) -> None:
        result = self.run_gate({"level": "unknown", "reason": "bad", "missing_information": []})

        self.assert_technical_fallback(result, "ValidationError")

    def run_gate(self, llm_result: object) -> dict[str, object]:
        llm = FakeLLM(llm_result)
        node = sufficient_context_gate_node(llm)

        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}):
            return node(self.answerable_state())

    def answerable_state(self) -> dict[str, object]:
        return {
            "question": "¿Quién debe investigar un accidente de trabajo?",
            "context": "El empleador debe conformar un equipo investigador para investigar el accidente.",
        }

    def assert_technical_fallback(self, result: dict[str, object], error_type: str) -> None:
        self.assertEqual(result["context_sufficiency"], ContextSufficiency.SUFFICIENT.value)
        trace = result["sufficient_context_trace"]
        self.assertIsNone(trace["level"])
        self.assertEqual(trace["missing_information"], [])
        self.assertTrue(trace["fallback"])
        self.assertEqual(trace["error"], error_type)


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
