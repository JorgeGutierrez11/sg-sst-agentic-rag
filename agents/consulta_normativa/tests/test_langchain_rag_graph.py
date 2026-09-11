"""Tests for the final validation-branch LangGraph RAG flow."""

import sys
import types
import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.core.routes import evidence_route
from agents.consulta_normativa.langchain_rag.graph import (
    answer_with_langgraph,
    build_langgraph_rag,
    build_messages_node,
    fallback_answer,
    fallback_answer_node,
    format_result_node,
)
from agents.consulta_normativa.langchain_rag.models import LangChainRagResult, RetrievedDocument


class FakeStateGraph:
    """Small StateGraph replacement for inspecting the compiled topology."""

    latest: "FakeStateGraph | None" = None

    def __init__(self, state_type: object) -> None:
        FakeStateGraph.latest = self
        self.nodes: dict[str, object] = {}
        self.edges: dict[str, str] = {}
        self.conditional: dict[str, tuple[object, object]] = {}
        self.entry_point = ""
        self.compile_kwargs: dict[str, object] = {}

    def add_node(self, name: str, node: object) -> None:
        self.nodes[name] = node

    def set_entry_point(self, name: str) -> None:
        self.entry_point = name

    def add_edge(self, start: str, end: str) -> None:
        self.edges[start] = end

    def add_conditional_edges(self, start: str, router: object, routes: object) -> None:
        self.conditional[start] = (router, routes)

    def compile(self, **kwargs: object) -> object:
        self.compile_kwargs = kwargs
        return types.SimpleNamespace(workflow=self)


class CapturingGraph:
    """Graph fake that records invocation state and configuration."""

    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, object], dict[str, object] | None]] = []
        self.result = LangChainRagResult(
            answer="Respuesta",
            references=["Referencia"],
            chunks=["Fragmento"],
            context="Contexto",
            prompt="Prompt",
        )

    def invoke(
        self,
        state: dict[str, object],
        config: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self.calls.append((state, config))
        return {"result": self.result}


class LangGraphRagTest(unittest.TestCase):
    """Verify the final graph and invocation contracts without external services."""

    def test_build_langgraph_rag_preserves_validation_branch_topology(self) -> None:
        checkpointer = object()
        store = object()
        fake_graph_module = types.SimpleNamespace(StateGraph=FakeStateGraph, END="__end__")

        with patch.dict(
            sys.modules,
            {
                "langgraph": types.SimpleNamespace(),
                "langgraph.graph": fake_graph_module,
            },
        ):
            compiled = build_langgraph_rag(
                FakeLlm(),
                lambda question, top_k: {},
                checkpointer=checkpointer,
                store=store,
            )

        workflow = compiled.workflow
        self.assertEqual(workflow.entry_point, "business_profile")
        self.assertEqual(
            set(workflow.nodes),
            {
                "business_profile",
                "retrieval_long_term_memory",
                "save_conversation_turn",
                "store_long_term_memory",
                "expand_query",
                "retrieve",
                "normalize_documents",
                "rerank",
                "expand_parent_documents",
                "retrieval_relevance_grading",
                "record_retrieval_trace",
                "fallback_answer",
                "format_context",
                "build_messages",
                "generate_answer",
                "format_result",
            },
        )
        self.assertEqual(workflow.edges["business_profile"], "retrieval_long_term_memory")
        self.assertEqual(workflow.edges["expand_parent_documents"], "record_retrieval_trace")
        self.assertEqual(workflow.edges["record_retrieval_trace"], "retrieval_relevance_grading")
        self.assertEqual(workflow.edges["generate_answer"], "save_conversation_turn")
        self.assertEqual(workflow.edges["store_long_term_memory"], "format_result")
        router, routes = workflow.conditional["retrieval_relevance_grading"]
        self.assertIs(router, evidence_route)
        self.assertEqual(routes, {"with_evidence": "format_context", "without_evidence": "fallback_answer"})
        self.assertEqual(workflow.compile_kwargs, {"checkpointer": checkpointer, "store": store})
        self.assertNotIn("sufficient_context_gate", workflow.nodes)
        self.assertNotIn("self_refine", workflow.nodes)

    def test_answer_with_langgraph_uses_thread_id_as_langgraph_config(self) -> None:
        graph = CapturingGraph()

        result = answer_with_langgraph("Pregunta", graph, thread_id="conversation-a")

        self.assertIs(result, graph.result)
        self.assertEqual(
            graph.calls,
            [({"question": "Pregunta"}, {"configurable": {"thread_id": "conversation-a"}})],
        )

    def test_answer_with_langgraph_keeps_unconfigured_compatibility(self) -> None:
        graph = CapturingGraph()

        answer_with_langgraph("Pregunta", graph)

        self.assertEqual(graph.calls, [({"question": "Pregunta"}, None)])

    def test_build_messages_separates_business_and_normative_context(self) -> None:
        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}):
            update = build_messages_node(
                {
                    "question": "¿Qué exige la norma?",
                    "context": "[1] Evidencia normativa",
                    "business_context": {"current_context": "Empresa de riesgo I"},
                }
            )

        system_message, human_message = update["messages"]
        self.assertIn("CONTEXTO NORMATIVO RECUPERADO", system_message.content)
        self.assertIn("Empresa de riesgo I", human_message.content)
        self.assertIn("[1] Evidencia normativa", human_message.content)
        self.assertEqual(f"{system_message.content}\n\n{human_message.content}", update["prompt"])

    def test_fallback_answer_remains_deterministic(self) -> None:
        self.assertEqual(
            fallback_answer("No se recuperó contexto.", []),
            "La evidencia recuperada es insuficiente para responder la pregunta.",
        )
        update = fallback_answer_node({"question": "Pregunta", "documents": []})
        self.assertEqual(update["answer"], "La evidencia recuperada es insuficiente para responder la pregunta.")

    def test_format_result_exposes_retrieved_chunks_for_api(self) -> None:
        update = format_result_node(
            {
                "answer": "Respuesta",
                "references": ["Referencia"],
                "context": "Contexto",
                "prompt": "Prompt",
                "documents": [RetrievedDocument("Fragmento", {})],
            }
        )

        self.assertEqual(update["result"].chunks, ["Fragmento"])


class FakeLlm:
    """Minimal LLM fake used while graph nodes are assembled."""

    def with_structured_output(self, schema: object, method: str | None = None) -> object:
        return self

    def invoke(self, messages: list[object]) -> object:
        return types.SimpleNamespace(content="Respuesta")


def fake_message_module() -> object:
    """Return fake LangChain message classes for message-building tests."""

    class Message:
        def __init__(self, content: str) -> None:
            self.content = content

    return types.SimpleNamespace(SystemMessage=Message, HumanMessage=Message)


if __name__ == "__main__":
    unittest.main()
