"""Tests for the experimental LangGraph RAG flow."""

import sys
import types
import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.core.instrumentation import record_retrieval_trace_node
from agents.consulta_normativa.langchain_rag.core.routes import evidence_route
from agents.consulta_normativa.langchain_rag.formatting import build_context, build_references, recovered_documents
from agents.consulta_normativa.langchain_rag.graph import (
    answer_with_langgraph,
    build_langgraph_rag,
    build_messages_node,
    fallback_answer,
    fallback_answer_node,
)
from agents.consulta_normativa.manual_implementation.prompts import build_base_prompt as build_manual_prompt
from agents.consulta_normativa.manual_implementation.rag_base import (
    build_context as build_manual_context,
    build_references as build_manual_references,
    recovered_documents as recovered_manual_documents,
)


class FakeStateGraph:
    """Tiny LangGraph replacement that preserves node and edge behavior for tests."""

    def __init__(self, state_type: object) -> None:
        self.nodes: dict[str, object] = {}
        self.edges: dict[str, str] = {}
        self.conditional: dict[str, tuple[object, object]] = {}
        self.entry_point = ""

    def add_node(self, name: str, node: object) -> None:
        self.nodes[name] = node

    def set_entry_point(self, name: str) -> None:
        self.entry_point = name

    def add_edge(self, start: str, end: str) -> None:
        self.edges[start] = end

    def add_conditional_edges(self, start: str, router: object, routes: object) -> None:
        self.conditional[start] = (router, routes)

    def compile(self) -> object:
        nodes = self.nodes
        edges = self.edges
        conditional = self.conditional
        entry_point = self.entry_point

        class CompiledGraph:
            def invoke(self, state: dict[str, object]) -> dict[str, object]:
                name = entry_point
                while name != "__end__":
                    state.update(nodes[name](state))
                    if name in conditional:
                        router, routes = conditional[name]
                        route = router(state)
                        if isinstance(route, list):
                            state = run_sends(nodes, edges, state, route)
                            name = edges[route[0].node] if route else "__end__"
                        elif isinstance(routes, dict):
                            name = routes[route]
                        else:
                            name = route
                    else:
                        name = edges[name]
                return state

        return CompiledGraph()


def run_sends(
    nodes: dict[str, object],
    edges: dict[str, str],
    state: dict[str, object],
    sends: list[object],
) -> dict[str, object]:
    """Run fake Send workers and concatenate reducer-style list writes."""

    for send in sends:
        update = nodes[send.node](send.arg)
        for key, value in update.items():
            if key == "retrieved_lists":
                state[key] = [*state.get(key, []), *value]
            else:
                state[key] = value
    return state


class LangGraphRagTest(unittest.TestCase):
    """Verify graph orchestration without real LangGraph, Groq, or Chroma calls."""

    def test_build_langgraph_rag_routes_evidence_through_messages_and_llm(self) -> None:
        fake_graph_module = types.SimpleNamespace(StateGraph=FakeStateGraph, END="__end__")
        llm = FakeLlm()

        with patch.dict(
            sys.modules,
            {
                "langgraph": types.SimpleNamespace(),
                "langgraph.graph": fake_graph_module,
                "langchain_core.messages": fake_message_module(),
            },
        ):
            graph = build_langgraph_rag(llm, self.fake_retriever, top_k=1)
            result = answer_with_langgraph("¿Qué exige la norma?", graph)

        self.assertEqual(result.answer, "Generated from fake LLM.")
        self.assertIn("Contenido:\nContexto normativo", result.context)
        self.assertEqual(result.references, ["Resolución 0312 de 2019, tabla 1 (table)"])
        self.assertEqual(len(llm.messages), 2)
        system_message, human_message = llm.messages[-1]
        self.assertIn("Responde ÚNICAMENTE", system_message.content)
        self.assertIn("Contexto recuperado:", human_message.content)
        self.assertIn("¿Qué exige la norma?", human_message.content)

    def test_build_langgraph_rag_retrieves_with_expanded_query(self) -> None:
        fake_graph_module = types.SimpleNamespace(StateGraph=FakeStateGraph, END="__end__")
        llm = FakeLlm(expansion_terms=["consulta normativa expandida SG-SST"])
        retrieved_queries: list[str] = []

        def retriever(question: str, top_k: int) -> dict[str, object]:
            retrieved_queries.append(question)
            return self.fake_retriever(question, top_k)

        with patch.dict(
            sys.modules,
            {
                "langgraph": types.SimpleNamespace(),
                "langgraph.graph": fake_graph_module,
                "langchain_core.messages": fake_message_module(),
            },
        ):
            graph = build_langgraph_rag(llm, retriever, top_k=1)
            state = graph.invoke({"question": "¿Qué tiene que hacer el empleador?"})

        self.assertEqual(state["answer"], "Generated from fake LLM.")
        self.assertEqual(retrieved_queries, ["¿Qué tiene que hacer el empleador? consulta normativa expandida SG-SST"])
        self.assertEqual(state["query_expansion_trace"]["technique"], "llm_query_expansion")
        self.assertEqual(state["query_expansion_trace"]["expansion_terms"], ["consulta normativa expandida SG-SST"])

    def test_build_langgraph_rag_base_does_not_enable_reranking_by_default(self) -> None:
        fake_graph_module = types.SimpleNamespace(StateGraph=FakeStateGraph, END="__end__")
        llm = FakeLlm()

        def retriever(question: str, top_k: int) -> dict[str, object]:
            self.assertEqual(top_k, 2)
            return {
                "documents": [["first document", "second document"]],
                "metadatas": [[{"source_stem": "first"}, {"source_stem": "second"}]],
            }

        with patch.dict(
            sys.modules,
            {
                "langgraph": types.SimpleNamespace(),
                "langgraph.graph": fake_graph_module,
                "langchain_core.messages": fake_message_module(),
            },
        ):
            graph = build_langgraph_rag(llm, retriever, top_k=2)
            state = graph.invoke({"question": "Pregunta original"})

        self.assertNotIn("reranking_trace", state)
        self.assertEqual(
            [document.document for document in state["documents"]],
            ["first document", "second document"],
        )

    def test_build_langgraph_rag_routes_no_evidence_to_manual_fallback_without_llm(self) -> None:
        fake_graph_module = types.SimpleNamespace(StateGraph=FakeStateGraph, END="__end__")
        llm = FakeLlm()

        with patch.dict(
            sys.modules,
            {
                "langgraph": types.SimpleNamespace(),
                "langgraph.graph": fake_graph_module,
                "langchain_core.messages": fake_message_module(),
            },
        ):
            graph = build_langgraph_rag(llm, lambda question, top_k: {"documents": [[]], "metadatas": [[]]}, top_k=1)
            result = answer_with_langgraph("¿Qué exige la norma?", graph)

        self.assertEqual(result.answer, "La evidencia recuperada es insuficiente para responder la pregunta.")
        self.assertEqual(result.context, "No se recuperó contexto.")
        self.assertEqual(result.references, [])
        self.assertEqual(len(llm.messages), 1)

    def test_context_references_and_generation_input_match_manual_for_fixture(self) -> None:
        raw_results = self.fake_retriever("¿Qué exige la norma?", 1)
        documents = recovered_documents(raw_results)
        manual_documents = recovered_manual_documents(raw_results)
        context = build_context(documents)
        references = build_references(documents)

        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}):
            message_state = build_messages_node({"question": "¿Qué exige la norma?", "context": context})

        self.assertEqual(context, build_manual_context(manual_documents))
        self.assertEqual(references, build_manual_references(manual_documents))
        self.assertEqual(message_state["prompt"], build_manual_prompt("¿Qué exige la norma?", context))
        system_message, human_message = message_state["messages"]
        self.assertEqual(f"{system_message.content}\n\n{human_message.content}", message_state["prompt"])

    def test_evidence_route_matches_manual_bool_documents_criterion(self) -> None:
        self.assertEqual(evidence_route({"documents": []}), "without_evidence")
        self.assertEqual(evidence_route({"documents": [object()]}), "with_evidence")

    def test_retrieval_trace_does_not_change_selected_documents(self) -> None:
        documents = [object()]

        update = record_retrieval_trace_node({"documents": documents})

        self.assertNotIn("documents", update)
        self.assertEqual(update, {"retrieval_traces": [{"document_count": 1}]})

    def test_fallback_answer_matches_manual_text_and_logic(self) -> None:
        self.assertEqual(
            fallback_answer("No se recuperó contexto.", []),
            "La evidencia recuperada es insuficiente para responder la pregunta.",
        )
        self.assertEqual(
            fallback_answer("context", ["ref"]),
            "Borrador fundamentado solo en el contexto recuperado:\ncontext\nReferencias:\nref",
        )
        self.assertEqual(
            fallback_answer_node({"question": "Pregunta", "documents": []})["answer"],
            "La evidencia recuperada es insuficiente para responder la pregunta.",
        )

    def test_missing_langgraph_reports_missing_optional_dependency(self) -> None:
        with patch.dict(sys.modules, {"langgraph": None, "langgraph.graph": None}):
            with self.assertRaises(ModuleNotFoundError) as context:
                build_langgraph_rag(lambda prompt: "answer", self.fake_retriever)

        self.assertIn("langgraph is not installed", str(context.exception))

    def test_answer_with_langgraph_rejects_missing_result(self) -> None:
        class BadGraph:
            def invoke(self, state: dict[str, object]) -> dict[str, object]:
                return state

        with self.assertRaises(ValueError):
            answer_with_langgraph("Pregunta", BadGraph())

    def fake_retriever(self, question: str, top_k: int) -> dict[str, object]:
        self.assertEqual(top_k, 1)
        return {
            "documents": [["Contexto normativo"]],
            "metadatas": [[{"source_stem": "Resolución 0312 de 2019", "document_type": "table", "table_index": 0}]],
        }


class FakeLlm:
    """Small LangChain-like fake that records message input."""

    def __init__(self, responses: list[str] | None = None, expansion_terms: list[str] | None = None) -> None:
        self.messages: list[list[object]] = []
        self.responses = responses or ["Generated from fake LLM."]
        self.expansion_terms = expansion_terms or []
        self.answer_count = 0

    def with_structured_output(self, schema: object, method: str) -> object:
        llm = self

        class StructuredLlm:
            def invoke(self, messages: list[object]) -> object:
                llm.messages.append(messages)
                return types.SimpleNamespace(expansion_terms=llm.expansion_terms)

        return StructuredLlm()

    def invoke(self, messages: list[object]) -> object:
        self.messages.append(messages)
        response = self.responses[min(self.answer_count, len(self.responses) - 1)]
        self.answer_count += 1
        return types.SimpleNamespace(content=response)


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
