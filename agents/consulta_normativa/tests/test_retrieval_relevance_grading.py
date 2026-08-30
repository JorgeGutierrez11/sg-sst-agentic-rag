"""Tests for retrieval relevance grading validation."""

import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.validation.retrieval_relevance_grading import (
    retrieval_relevance_grading_node,
)


class FakeGrader:
    """Structured-output fake that returns configured grades or errors."""

    def __init__(self, results: list[object]) -> None:
        self.results = iter(results)

    def invoke(self, messages: list[object]) -> object:
        result = next(self.results)

        if isinstance(result, Exception):
            raise result

        return result


class FakeLLM:
    """LLM fake for structured relevance grading."""

    def __init__(
        self,
        results: list[object],
        configuration_error: Exception | None = None,
    ) -> None:
        self.results = results
        self.configuration_error = configuration_error

    def with_structured_output(
        self,
        schema: object,
        **kwargs: object,
    ) -> object:
        if self.configuration_error is not None:
            raise self.configuration_error

        return FakeGrader(self.results)


class RetrievalRelevanceGradingTest(unittest.TestCase):
    """Verify relevance filtering and fail-open behavior."""

    def setUp(self) -> None:
        self.message_patch = patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()})
        self.message_patch.start()

    def tearDown(self) -> None:
        self.message_patch.stop()

    def test_empty_documents_returns_zero_counter_trace(self) -> None:
        node = retrieval_relevance_grading_node(FakeLLM([]))

        result = node({"question": "Pregunta cualquiera", "documents": []})

        self.assertEqual(result["documents"], [])
        self.assertEqual(
            result["relevance_grading_trace"],
            {
                "input_count": 0,
                "relevant_count": 0,
                "rejected_count": 0,
                "fallback_count": 0,
                "documents": [],
            },
        )

    def test_relevant_document_is_preserved(self) -> None:
        document = make_document("El empleador debe investigar los accidentes de trabajo.", "1")
        node = retrieval_relevance_grading_node(
            FakeLLM([{"relevant": True, "reason": "El documento contiene evidencia normativa directa."}])
        )

        result = node({"question": "¿Quién debe investigar un accidente de trabajo?", "documents": [document]})

        self.assertEqual(result["documents"], [document])
        trace = result["relevance_grading_trace"]
        self.assertEqual(trace["input_count"], 1)
        self.assertEqual(trace["relevant_count"], 1)
        self.assertEqual(trace["rejected_count"], 0)
        self.assertEqual(trace["fallback_count"], 0)
        self.assertFalse(trace["documents"][0]["fallback"])

    def test_irrelevant_document_is_filtered_but_top_one_is_conserved(self) -> None:
        document = make_document("El comité estará conformado por representantes.", "2")
        node = retrieval_relevance_grading_node(
            FakeLLM(
                [
                    {
                        "relevant": False,
                        "reason": "El documento solo comparte términos generales, sin aportar evidencia útil.",
                    }
                ]
            )
        )

        result = node({"question": "¿Quién debe investigar un accidente de trabajo?", "documents": [document]})

        self.assertEqual(result["documents"], [document])
        trace = result["relevance_grading_trace"]
        self.assertEqual(trace["relevant_count"], 0)
        self.assertEqual(trace["rejected_count"], 1)
        self.assertEqual(trace["fallback_count"], 1)
        self.assertFalse(trace["documents"][0]["relevant"])
        self.assertTrue(trace["documents"][0]["fallback"])
        self.assertIn("fallback conservador", trace["documents"][0]["reason"])

    def test_filters_irrelevant_documents_when_some_are_relevant(self) -> None:
        documents = [
            make_document("El empleador debe investigar los accidentes de trabajo.", "1"),
            make_document("El comité estará conformado por representantes.", "2"),
        ]
        node = retrieval_relevance_grading_node(
            FakeLLM(
                [
                    {"relevant": True, "reason": "El documento contiene evidencia normativa directa."},
                    {
                        "relevant": False,
                        "reason": "El documento solo comparte términos generales, sin aportar evidencia útil.",
                    },
                ]
            )
        )

        result = node({"question": "¿Quién debe investigar un accidente de trabajo?", "documents": documents})

        self.assertEqual(result["documents"], [documents[0]])
        trace = result["relevance_grading_trace"]
        self.assertEqual(trace["input_count"], 2)
        self.assertEqual(trace["relevant_count"], 1)
        self.assertEqual(trace["rejected_count"], 1)
        self.assertEqual(trace["fallback_count"], 0)

    def test_structured_output_configuration_error_preserves_all_documents(self) -> None:
        documents = [
            make_document("Primer documento normativo.", "1"),
            make_document("Segundo documento normativo.", "2"),
        ]
        node = retrieval_relevance_grading_node(FakeLLM([], configuration_error=RuntimeError("unavailable")))

        result = node({"question": "¿Qué exige la norma?", "documents": documents})

        self.assertEqual(result["documents"], documents)
        trace = result["relevance_grading_trace"]
        self.assertEqual(trace["input_count"], 2)
        self.assertEqual(trace["relevant_count"], 2)
        self.assertEqual(trace["rejected_count"], 0)
        self.assertEqual(trace["fallback_count"], 2)
        self.assertEqual(len(trace["documents"]), 2)
        self.assertEqual(trace["documents"][0]["error"], "RuntimeError")
        self.assertEqual(
            trace["documents"][0]["reason"],
            "Documento conservado por política fail-open porque el grader no pudo configurarse.",
        )

    def test_individual_grading_error_preserves_that_document(self) -> None:
        document = make_document("El empleador debe investigar los accidentes de trabajo.", "1")
        node = retrieval_relevance_grading_node(FakeLLM([RuntimeError("grader unavailable")]))

        result = node({"question": "¿Quién investiga un accidente?", "documents": [document]})

        self.assertEqual(result["documents"], [document])
        trace = result["relevance_grading_trace"]
        self.assertEqual(trace["fallback_count"], 1)
        self.assertTrue(trace["documents"][0]["fallback"])
        self.assertEqual(trace["documents"][0]["error"], "RuntimeError")


def make_document(text: str, article: str) -> SimpleNamespace:
    """Build a minimal RetrievedDocument-like object for tests."""

    return SimpleNamespace(
        document=text,
        metadata={
            "source_stem": "Resolución de prueba",
            "article": article,
        },
    )


def fake_message_module() -> object:
    """Return fake LangChain message classes for lazy-import tests."""

    class SystemMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class HumanMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    return SimpleNamespace(SystemMessage=SystemMessage, HumanMessage=HumanMessage)


if __name__ == "__main__":
    unittest.main()
