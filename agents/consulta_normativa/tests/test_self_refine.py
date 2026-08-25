from types import SimpleNamespace

from agents.consulta_normativa.langchain_rag.validation.self_refine import (
    self_refine_node,
)


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


def test_answer_without_issues_is_preserved():
    llm = FakeLLM(
        feedback_result={
            "needs_refinement": False,
            "feedback": (
                "La respuesta está respaldada por el contexto y responde "
                "adecuadamente la pregunta."
            ),
            "issues": [],
        }
    )

    node = self_refine_node(llm)

    state = build_base_state()
    initial_answer = state["answer"]

    result = node(state)

    assert result["answer"] == initial_answer

    trace = result["self_refine_trace"]

    assert trace["initial_answer"] == initial_answer
    assert trace["needs_refinement"] is False
    assert trace["refined"] is False
    assert trace["issues"] == []
    assert trace["fallback"] is False
    assert trace["error_stage"] is None
    assert trace["error"] is None

    # Feedback is evaluated once.
    assert llm.grader.call_count == 1

    # Refinement must NOT be invoked when the answer is already acceptable.
    assert llm.refinement_call_count == 0


def test_answer_with_issues_is_refined():
    llm = FakeLLM(
        feedback_result={
            "needs_refinement": True,
            "feedback": (
                "La respuesta indica un plazo incorrecto. "
                "Debe corregirse utilizando el fragmento [1]."
            ),
            "issues": [
                "El plazo indicado no coincide con la evidencia recuperada."
            ],
        },
        refinement_result=(
            "La investigación debe realizarse dentro de los "
            "quince (15) días siguientes a la ocurrencia del evento [1]."
        ),
    )

    node = self_refine_node(llm)

    state = build_base_state()
    state["answer"] = (
        "La investigación debe realizarse dentro de treinta (30) días [1]."
    )

    initial_answer = state["answer"]

    result = node(state)

    expected_refined_answer = (
        "La investigación debe realizarse dentro de los "
        "quince (15) días siguientes a la ocurrencia del evento [1]."
    )

    assert result["answer"] == expected_refined_answer

    trace = result["self_refine_trace"]

    assert trace["initial_answer"] == initial_answer
    assert trace["needs_refinement"] is True
    assert trace["refined"] is True
    assert trace["feedback"]
    assert trace["issues"] == [
        "El plazo indicado no coincide con la evidencia recuperada."
    ]
    assert trace["fallback"] is False
    assert trace["error_stage"] is None
    assert trace["error"] is None

    assert llm.grader.call_count == 1
    assert llm.refinement_call_count == 1


def test_feedback_failure_preserves_initial_answer():
    llm = FakeLLM(
        feedback_result=RuntimeError("feedback unavailable")
    )

    node = self_refine_node(llm)

    state = build_base_state()
    initial_answer = state["answer"]

    result = node(state)

    assert result["answer"] == initial_answer

    trace = result["self_refine_trace"]

    assert trace["initial_answer"] == initial_answer
    assert trace["refined"] is False
    assert trace["fallback"] is True
    assert trace["error_stage"] == "feedback"
    assert trace["error"] == "RuntimeError"

    assert llm.refinement_call_count == 0


def test_structured_output_failure_preserves_initial_answer():
    llm = BrokenStructuredOutputLLM()

    node = self_refine_node(llm)

    state = build_base_state()
    initial_answer = state["answer"]

    result = node(state)

    assert result["answer"] == initial_answer

    trace = result["self_refine_trace"]

    assert trace["initial_answer"] == initial_answer
    assert trace["refined"] is False
    assert trace["fallback"] is True
    assert trace["error_stage"] == "feedback_configuration"
    assert trace["error"] == "RuntimeError"


def test_refinement_failure_preserves_initial_answer():
    llm = FakeLLM(
        feedback_result={
            "needs_refinement": True,
            "feedback": "La respuesta debe corregirse.",
            "issues": [
                "La respuesta contiene información incorrecta."
            ],
        },
        refinement_result=RuntimeError("refinement unavailable"),
    )

    node = self_refine_node(llm)

    state = build_base_state()
    initial_answer = state["answer"]

    result = node(state)

    assert result["answer"] == initial_answer

    trace = result["self_refine_trace"]

    assert trace["initial_answer"] == initial_answer
    assert trace["needs_refinement"] is True
    assert trace["refined"] is False
    assert trace["fallback"] is True
    assert trace["error_stage"] == "refinement"
    assert trace["error"] == "RuntimeError"

    assert trace["issues"] == [
        "La respuesta contiene información incorrecta."
    ]

    assert llm.refinement_call_count == 1


def test_empty_initial_answer_does_not_call_llm():
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

    assert "answer" not in result
    assert trace["needs_refinement"] is False
    assert trace["refined"] is False
    assert trace["fallback"] is True
    assert trace["error_stage"] == "input"
    assert trace["error"] == "EmptyInitialAnswer"

    assert llm.structured_output_call_count == 0
    assert llm.grader.call_count == 0
    assert llm.refinement_call_count == 0


def test_empty_refined_answer_preserves_initial_answer():
    llm = FakeLLM(
        feedback_result={
            "needs_refinement": True,
            "feedback": "La respuesta debe corregirse.",
            "issues": [
                "Existe una afirmación no respaldada."
            ],
        },
        refinement_result="   ",
    )

    node = self_refine_node(llm)

    state = build_base_state()
    initial_answer = state["answer"]

    result = node(state)

    assert result["answer"] == initial_answer

    trace = result["self_refine_trace"]

    assert trace["initial_answer"] == initial_answer
    assert trace["needs_refinement"] is True
    assert trace["refined"] is False
    assert trace["fallback"] is True
    assert trace["error_stage"] == "refinement"
    assert trace["error"] == "ValueError"

    assert llm.refinement_call_count == 1