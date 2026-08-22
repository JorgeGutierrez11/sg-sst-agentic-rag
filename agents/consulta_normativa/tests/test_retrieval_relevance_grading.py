from types import SimpleNamespace

from agents.consulta_normativa.langchain_rag.validation.retrieval_relevance_grading import (
    retrieval_relevance_grading_node,
)


class FakeGrader:
    def __init__(self, results):
        self.results = iter(results)

    def invoke(self, messages):
        result = next(self.results)

        if isinstance(result, Exception):
            raise result

        return result


class FakeLLM:
    def __init__(self, results):
        self.results = results

    def with_structured_output(self, schema):
        return FakeGrader(self.results)


def make_document(text: str, article: str):
    return SimpleNamespace(
        document=text,
        metadata={
            "source_stem": "Resolución de prueba",
            "article": article,
        },
    )


def test_filters_irrelevant_documents():
    documents = [
        make_document(
            "El empleador debe investigar los accidentes de trabajo.",
            "1",
        ),
        make_document(
            "El comité estará conformado por representantes.",
            "2",
        ),
    ]

    llm = FakeLLM(
        [
            {"relevant": True},
            {"relevant": False},
        ]
    )

    node = retrieval_relevance_grading_node(llm)

    result = node(
        {
            "question": "¿Quién debe investigar un accidente de trabajo?",
            "documents": documents,
        }
    )

    assert len(result["documents"]) == 1
    assert result["documents"][0].metadata["article"] == "1"

    trace = result["relevance_grading_trace"]

    assert trace["input_count"] == 2
    assert trace["relevant_count"] == 1
    assert trace["rejected_count"] == 1
    assert trace["fallback_count"] == 0


def test_grader_failure_keeps_document():
    document = make_document(
        "El empleador debe investigar los accidentes de trabajo.",
        "1",
    )

    llm = FakeLLM(
        [
            RuntimeError("grader unavailable"),
        ]
    )

    node = retrieval_relevance_grading_node(llm)

    result = node(
        {
            "question": "¿Quién investiga un accidente?",
            "documents": [document],
        }
    )

    assert len(result["documents"]) == 1

    trace = result["relevance_grading_trace"]

    assert trace["fallback_count"] == 1
    assert trace["documents"][0]["fallback"] is True


def test_empty_documents():
    llm = FakeLLM([])

    node = retrieval_relevance_grading_node(llm)

    result = node(
        {
            "question": "Pregunta cualquiera",
            "documents": [],
        }
    )

    assert result["documents"] == []
    assert result["relevance_grading_trace"]["input_count"] == 0