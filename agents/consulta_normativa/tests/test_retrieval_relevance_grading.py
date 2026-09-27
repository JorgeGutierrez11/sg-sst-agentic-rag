"""Tests for retrieval relevance grading validation."""

import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.core.routes import evidence_route
from agents.consulta_normativa.langchain_rag.validation.retrieval_relevance_grading import (
    retrieval_relevance_grading_node,
)


class FakeGrader:
    """Structured-output fake that returns configured grades or errors."""

    def __init__(self, results: list[object]) -> None:
        self.results = iter(results)
        self.invoke_count = 0
        self.messages: list[object] = []

    def invoke(self, messages: list[object]) -> object:
        self.invoke_count += 1
        self.messages = messages
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
        self.grader: FakeGrader | None = None

    def with_structured_output(
        self,
        schema: object,
        **kwargs: object,
    ) -> object:
        if self.configuration_error is not None:
            raise self.configuration_error

        self.grader = FakeGrader(self.results)
        return self.grader


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
            FakeLLM(
                [
                    batch_result(
                        (0, True, "El documento contiene evidencia normativa directa."),
                    )
                ]
            )
        )

        result = node({"question": "¿Quién debe investigar un accidente de trabajo?", "documents": [document]})

        self.assertEqual(result["documents"], [document])
        trace = result["relevance_grading_trace"]
        self.assertEqual(trace["input_count"], 1)
        self.assertEqual(trace["relevant_count"], 1)
        self.assertEqual(trace["rejected_count"], 0)
        self.assertEqual(trace["fallback_count"], 0)
        self.assertFalse(trace["documents"][0]["fallback"])

    def test_valid_all_negative_batch_returns_empty_documents_and_routes_without_evidence(self) -> None:
        documents = [
            make_document("El comité estará conformado por representantes.", "2"),
            make_document("La elección se realizará por votación.", "3"),
        ]
        node = retrieval_relevance_grading_node(
            FakeLLM(
                [
                    batch_result(
                        (0, False, "No aporta evidencia útil."),
                        (1, False, "Trata un asunto diferente."),
                    )
                ]
            )
        )

        result = node({"question": "¿Quién debe investigar un accidente de trabajo?", "documents": documents})

        self.assertEqual(result["documents"], [])
        trace = result["relevance_grading_trace"]
        self.assertEqual(trace["relevant_count"], 0)
        self.assertEqual(trace["rejected_count"], 2)
        self.assertEqual(trace["fallback_count"], 0)
        self.assertFalse(trace["documents"][0]["relevant"])
        self.assertFalse(trace["documents"][0]["fallback"])
        self.assertEqual(evidence_route(result), "without_evidence")

    def test_batch_is_invoked_once_and_out_of_order_decisions_map_by_index(self) -> None:
        documents = [
            make_document("El empleador debe investigar los accidentes de trabajo.", "1"),
            make_document("El comité estará conformado por representantes.", "2"),
            make_document("La investigación debe documentarse.", "3"),
        ]
        llm = FakeLLM(
            [
                batch_result(
                    (2, True, "Aporta el procedimiento documental."),
                    (0, True, "Contiene la obligación principal."),
                    (1, False, "Trata un asunto diferente."),
                )
            ]
        )
        node = retrieval_relevance_grading_node(llm)

        result = node({"question": "¿Quién debe investigar un accidente de trabajo?", "documents": documents})

        self.assertEqual(result["documents"], [documents[0], documents[2]])
        self.assertIsNotNone(llm.grader)
        self.assertEqual(llm.grader.invoke_count, 1)
        prompt = llm.grader.messages[1].content
        self.assertIn("[DOCUMENTO 0]", prompt)
        self.assertIn("[DOCUMENTO 1]", prompt)
        self.assertIn("[DOCUMENTO 2]", prompt)
        trace = result["relevance_grading_trace"]
        self.assertEqual(trace["input_count"], 3)
        self.assertEqual(trace["relevant_count"], 2)
        self.assertEqual(trace["rejected_count"], 1)
        self.assertEqual(trace["fallback_count"], 0)
        self.assertEqual([item["index"] for item in trace["documents"]], [0, 1, 2])
        self.assertEqual([item["relevant"] for item in trace["documents"]], [True, False, True])

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

    def test_malformed_batch_indices_preserve_all_documents(self) -> None:
        documents = [
            make_document("Primer documento normativo.", "1"),
            make_document("Segundo documento normativo.", "2"),
        ]
        malformed_results = {
            "missing": batch_result((0, True, "Única decisión.")),
            "duplicate": batch_result((0, True, "Primera."), (0, False, "Duplicada.")),
            "out_of_range": batch_result((0, True, "Primera."), (2, False, "Fuera de rango.")),
        }

        for name, grader_result in malformed_results.items():
            with self.subTest(name=name):
                llm = FakeLLM([grader_result])
                node = retrieval_relevance_grading_node(llm)
                result = node({"question": "¿Qué exige la norma?", "documents": documents})

                self.assertEqual(result["documents"], documents)
                self.assertEqual(llm.grader.invoke_count, 1)
                trace = result["relevance_grading_trace"]
                self.assertEqual(trace["fallback_count"], 2)
                self.assertTrue(all(item["fallback"] for item in trace["documents"]))
                self.assertTrue(all(item["error"] == "ValueError" for item in trace["documents"]))

    def test_batch_invocation_error_preserves_all_documents(self) -> None:
        documents = [
            make_document("El empleador debe investigar los accidentes de trabajo.", "1"),
            make_document("La investigación debe documentarse.", "2"),
        ]
        llm = FakeLLM([RuntimeError("grader unavailable")])
        node = retrieval_relevance_grading_node(llm)

        result = node({"question": "¿Quién investiga un accidente?", "documents": documents})

        self.assertEqual(result["documents"], documents)
        self.assertEqual(llm.grader.invoke_count, 1)
        trace = result["relevance_grading_trace"]
        self.assertEqual(trace["fallback_count"], 2)
        self.assertTrue(all(item["fallback"] for item in trace["documents"]))
        self.assertTrue(all(item["error"] == "RuntimeError" for item in trace["documents"]))


def make_document(text: str, article: str) -> SimpleNamespace:
    """Build a minimal RetrievedDocument-like object for tests."""

    return SimpleNamespace(
        document=text,
        metadata={
            "source_stem": "Resolución de prueba",
            "article": article,
        },
    )


def batch_result(*decisions: tuple[int, bool, str]) -> dict[str, object]:
    """Build one structured batch relevance result."""

    return {
        "decisions": [
            {"index": index, "relevant": relevant, "reason": reason}
            for index, relevant, reason in decisions
        ]
    }


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
