from agents.consulta_normativa.langchain_rag.validation.sufficient_context_gate import (
    ContextSufficiency,
    sufficient_context_gate_node,
)


class FakeGrader:
    """Fake structured-output grader for deterministic tests."""

    def __init__(self, result):
        self.result = result

    def invoke(self, messages):
        if isinstance(self.result, Exception):
            raise self.result

        return self.result


class FakeLLM:
    """Fake LLM that returns a configured structured-output grader."""

    def __init__(self, result):
        self.result = result

    def with_structured_output(self, schema):
        return FakeGrader(self.result)


class BrokenStructuredOutputLLM:
    """Fake LLM that fails while configuring structured output."""

    def with_structured_output(self, schema):
        raise RuntimeError("structured output unavailable")


def test_sufficient_context():
    llm = FakeLLM(
        {
            "level": "sufficient",
            "reason": (
                "El contexto contiene la información necesaria "
                "para responder todos los componentes de la pregunta."
            ),
            "missing_information": [],
        }
    )

    node = sufficient_context_gate_node(llm)

    result = node(
        {
            "question": (
                "¿Quién debe investigar los accidentes de trabajo?"
            ),
            "context": (
                "El empleador debe conformar un equipo investigador "
                "para investigar los accidentes de trabajo."
            ),
        }
    )

    assert result["context_sufficiency"] == ContextSufficiency.SUFFICIENT.value

    trace = result["sufficient_context_trace"]

    assert trace["level"] == "sufficient"
    assert trace["missing_information"] == []
    assert trace["fallback"] is False
    assert trace["error"] is None


def test_partial_context():
    llm = FakeLLM(
        {
            "level": "partial",
            "reason": (
                "El contexto permite identificar quién debe realizar "
                "la investigación, pero no contiene el plazo solicitado."
            ),
            "missing_information": [
                "Plazo para realizar la investigación del accidente."
            ],
        }
    )

    node = sufficient_context_gate_node(llm)

    result = node(
        {
            "question": (
                "¿Quién debe investigar un accidente de trabajo "
                "y cuál es el plazo para hacerlo?"
            ),
            "context": (
                "El empleador debe conformar un equipo investigador "
                "para investigar el accidente."
            ),
        }
    )

    assert result["context_sufficiency"] == ContextSufficiency.PARTIAL.value

    trace = result["sufficient_context_trace"]

    assert trace["level"] == "partial"
    assert trace["fallback"] is False
    assert trace["error"] is None
    assert trace["missing_information"] == [
        "Plazo para realizar la investigación del accidente."
    ]


def test_insufficient_context():
    llm = FakeLLM(
        {
            "level": "insufficient",
            "reason": (
                "El contexto recuperado no contiene información "
                "que permita responder la pregunta."
            ),
            "missing_information": [
                "Evidencia normativa relacionada con la pregunta."
            ],
        }
    )

    node = sufficient_context_gate_node(llm)

    result = node(
        {
            "question": (
                "¿Cuáles son los requisitos para renovar "
                "un pasaporte colombiano?"
            ),
            "context": (
                "El empleador debe implementar el Sistema de Gestión "
                "de Seguridad y Salud en el Trabajo."
            ),
        }
    )

    assert (
        result["context_sufficiency"]
        == ContextSufficiency.INSUFFICIENT.value
    )

    trace = result["sufficient_context_trace"]

    assert trace["level"] == "insufficient"
    assert trace["fallback"] is False
    assert trace["error"] is None
    assert trace["missing_information"]


def test_empty_context_is_insufficient():
    llm = FakeLLM(
        {
            "level": "sufficient",
            "reason": "Este resultado no debería utilizarse.",
            "missing_information": [],
        }
    )

    node = sufficient_context_gate_node(llm)

    result = node(
        {
            "question": "Pregunta cualquiera",
            "context": "",
        }
    )

    assert (
        result["context_sufficiency"]
        == ContextSufficiency.INSUFFICIENT.value
    )

    trace = result["sufficient_context_trace"]

    assert trace["level"] == "insufficient"
    assert trace["fallback"] is False
    assert trace["error"] is None
    assert trace["missing_information"]


def test_grader_failure_uses_fail_open():
    llm = FakeLLM(
        RuntimeError("grader unavailable")
    )

    node = sufficient_context_gate_node(llm)

    result = node(
        {
            "question": "¿Quién debe investigar un accidente?",
            "context": (
                "El empleador debe conformar un equipo investigador."
            ),
        }
    )

    assert (
        result["context_sufficiency"]
        == ContextSufficiency.SUFFICIENT.value
    )

    trace = result["sufficient_context_trace"]

    assert trace["level"] is None
    assert trace["fallback"] is True
    assert trace["error"] == "RuntimeError"


def test_structured_output_failure_uses_fail_open():
    llm = BrokenStructuredOutputLLM()

    node = sufficient_context_gate_node(llm)

    result = node(
        {
            "question": "¿Quién debe investigar un accidente?",
            "context": (
                "El empleador debe conformar un equipo investigador."
            ),
        }
    )

    assert (
        result["context_sufficiency"]
        == ContextSufficiency.SUFFICIENT.value
    )

    trace = result["sufficient_context_trace"]

    assert trace["level"] is None
    assert trace["fallback"] is True
    assert trace["error"] == "RuntimeError"