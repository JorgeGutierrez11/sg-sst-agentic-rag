import unittest
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.validation.self_refine import self_refine_node


EXPECTED_TRACE_KEYS = {
    "initial_answer",
    "needs_refinement",
    "refined",
    "feedback",
    "issues",
    "fallback",
    "error_stage",
    "error",
}


class FakeGrader:
    """Fake structured-output grader for deterministic Self-Refine tests."""

    def __init__(self, result):
        self.result = result
        self.call_count = 0

    def invoke(self, messages):
        self.call_count += 1

        if isinstance(self.result, Exception):
            raise self.result

        return self.result


class FakeLLM:
    """Fake LLM supporting both feedback and refinement calls."""

    def __init__(
        self,
        feedback_result,
        refinement_result="Respuesta refinada.",
    ):
        self.feedback_result = feedback_result
        self.refinement_result = refinement_result

        self.structured_output_call_count = 0
        self.refinement_call_count = 0

        self.grader = FakeGrader(feedback_result)

    def with_structured_output(self, schema):
        self.structured_output_call_count += 1
        return self.grader

    def invoke(self, messages):
        self.refinement_call_count += 1

        if isinstance(self.refinement_result, Exception):
            raise self.refinement_result

        return SimpleNamespace(content=self.refinement_result)


class BrokenStructuredOutputLLM:
    """Fake LLM that fails while configuring structured feedback."""

    def with_structured_output(self, schema):
        raise RuntimeError("structured output unavailable")


def build_base_state() -> dict:
    """Return a minimal graph state for Self-Refine tests."""

    return {
        "question": "¿Cuál es el plazo para investigar un accidente de trabajo?",
        "context": (
            "[1] La investigación deberá realizarse dentro de los "
            "quince (15) días siguientes a la ocurrencia del evento."
        ),
        "answer": "La investigación debe realizarse dentro de 15 días [1].",
    }


class SelfRefineNodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.messages_patch = patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()})
        self.messages_patch.start()

    def tearDown(self) -> None:
        self.messages_patch.stop()

    def assertCompleteTrace(self, trace: dict) -> None:
        self.assertEqual(set(trace), EXPECTED_TRACE_KEYS)

    def test_answer_without_issues_is_preserved(self):
        llm = FakeLLM(
            feedback_result={
                "needs_refinement": False,
                "feedback": "La respuesta está respaldada por el contexto y responde adecuadamente la pregunta.",
                "issues": [],
            }
        )

        node = self_refine_node(llm)

        state = build_base_state()
        initial_answer = state["answer"]

        result = node(state)

        self.assertEqual(result["answer"], initial_answer)

        trace = result["self_refine_trace"]
        self.assertCompleteTrace(trace)
        self.assertEqual(trace["initial_answer"], initial_answer)
        self.assertIs(trace["needs_refinement"], False)
        self.assertIs(trace["refined"], False)
        self.assertEqual(trace["issues"], [])
        self.assertIs(trace["fallback"], False)
        self.assertIsNone(trace["error_stage"])
        self.assertIsNone(trace["error"])

        self.assertEqual(llm.grader.call_count, 1)
        self.assertEqual(llm.refinement_call_count, 0)

    def test_answer_with_issues_is_refined(self):
        expected_refined_answer = (
            "La investigación debe realizarse dentro de los "
            "quince (15) días siguientes a la ocurrencia del evento [1]."
        )
        llm = FakeLLM(
            feedback_result={
                "needs_refinement": True,
                "feedback": "La respuesta indica un plazo incorrecto. Debe corregirse utilizando el fragmento [1].",
                "issues": ["El plazo indicado no coincide con la evidencia recuperada."],
            },
            refinement_result=expected_refined_answer,
        )

        node = self_refine_node(llm)

        state = build_base_state()
        state["answer"] = "La investigación debe realizarse dentro de treinta (30) días [1]."
        initial_answer = state["answer"]

        result = node(state)

        trace = result["self_refine_trace"]

        self.assertEqual(result["answer"], expected_refined_answer)
        self.assertCompleteTrace(trace)
        self.assertEqual(trace["initial_answer"], initial_answer)
        self.assertIs(trace["needs_refinement"], True)
        self.assertIs(trace["refined"], True)
        self.assertTrue(trace["feedback"])
        self.assertEqual(trace["issues"], ["El plazo indicado no coincide con la evidencia recuperada."])
        self.assertIs(trace["fallback"], False)
        self.assertIsNone(trace["error_stage"])
        self.assertIsNone(trace["error"])
        self.assertEqual(llm.grader.call_count, 1)
        self.assertEqual(llm.refinement_call_count, 1)

    def test_feedback_failure_preserves_initial_answer(self):
        llm = FakeLLM(feedback_result=RuntimeError("feedback unavailable"))

        node = self_refine_node(llm)

        state = build_base_state()
        initial_answer = state["answer"]

        result = node(state)
        trace = result["self_refine_trace"]

        self.assertEqual(result["answer"], initial_answer)
        self.assertCompleteTrace(trace)
        self.assertEqual(trace["initial_answer"], initial_answer)
        self.assertIs(trace["needs_refinement"], False)
        self.assertIs(trace["refined"], False)
        self.assertIs(trace["fallback"], True)
        self.assertEqual(trace["error_stage"], "feedback")
        self.assertEqual(trace["error"], "RuntimeError")
        self.assertEqual(llm.refinement_call_count, 0)

    def test_structured_output_failure_preserves_initial_answer(self):
        llm = BrokenStructuredOutputLLM()

        node = self_refine_node(llm)

        state = build_base_state()
        initial_answer = state["answer"]

        result = node(state)
        trace = result["self_refine_trace"]

        self.assertEqual(result["answer"], initial_answer)
        self.assertCompleteTrace(trace)
        self.assertEqual(trace["initial_answer"], initial_answer)
        self.assertIs(trace["needs_refinement"], False)
        self.assertIs(trace["refined"], False)
        self.assertIs(trace["fallback"], True)
        self.assertEqual(trace["error_stage"], "feedback_configuration")
        self.assertEqual(trace["error"], "RuntimeError")

    def test_refinement_failure_preserves_initial_answer(self):
        llm = FakeLLM(
            feedback_result={
                "needs_refinement": True,
                "feedback": "La respuesta debe corregirse.",
                "issues": ["La respuesta contiene información incorrecta."],
            },
            refinement_result=RuntimeError("refinement unavailable"),
        )

        node = self_refine_node(llm)
        state = build_base_state()
        initial_answer = state["answer"]

        result = node(state)
        trace = result["self_refine_trace"]

        self.assertEqual(result["answer"], initial_answer)
        self.assertCompleteTrace(trace)
        self.assertEqual(trace["initial_answer"], initial_answer)
        self.assertIs(trace["needs_refinement"], True)
        self.assertIs(trace["refined"], False)
        self.assertIs(trace["fallback"], True)
        self.assertEqual(trace["error_stage"], "refinement")
        self.assertEqual(trace["error"], "RuntimeError")
        self.assertEqual(trace["issues"], ["La respuesta contiene información incorrecta."])
        self.assertEqual(llm.refinement_call_count, 1)

    def test_empty_initial_answer_does_not_call_llm(self):
        llm = FakeLLM(
            feedback_result={
                "needs_refinement": False,
                "feedback": "No debería ejecutarse.",
                "issues": [],
            }
        )

        node = self_refine_node(llm)
        state = build_base_state()
        state["answer"] = ""

        result = node(state)
        trace = result["self_refine_trace"]

        self.assertEqual(result["answer"], "")
        self.assertCompleteTrace(trace)
        self.assertEqual(trace["initial_answer"], "")
        self.assertIs(trace["needs_refinement"], False)
        self.assertIs(trace["refined"], False)
        self.assertEqual(trace["feedback"], "")
        self.assertEqual(trace["issues"], [])
        self.assertIs(trace["fallback"], True)
        self.assertEqual(trace["error_stage"], "input")
        self.assertEqual(trace["error"], "EmptyInitialAnswer")
        self.assertEqual(llm.structured_output_call_count, 0)
        self.assertEqual(llm.grader.call_count, 0)
        self.assertEqual(llm.refinement_call_count, 0)

    def test_empty_refined_answer_preserves_initial_answer(self):
        llm = FakeLLM(
            feedback_result={
                "needs_refinement": True,
                "feedback": "La respuesta debe corregirse.",
                "issues": ["Existe una afirmación no respaldada."],
            },
            refinement_result="   ",
        )

        node = self_refine_node(llm)
        state = build_base_state()
        initial_answer = state["answer"]

        result = node(state)
        trace = result["self_refine_trace"]

        self.assertEqual(result["answer"], initial_answer)
        self.assertCompleteTrace(trace)
        self.assertEqual(trace["initial_answer"], initial_answer)
        self.assertIs(trace["needs_refinement"], True)
        self.assertIs(trace["refined"], False)
        self.assertIs(trace["fallback"], True)
        self.assertEqual(trace["error_stage"], "refinement")
        self.assertEqual(trace["error"], "ValueError")
        self.assertEqual(llm.refinement_call_count, 1)


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
