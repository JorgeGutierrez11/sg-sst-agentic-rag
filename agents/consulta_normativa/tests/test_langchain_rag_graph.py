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
from agents.consulta_normativa.langchain_rag.models import RetrievedDocument
from agents.consulta_normativa.manual_implementation.prompts import build_base_prompt as build_manual_prompt
from agents.consulta_normativa.manual_implementation.rag_base import (
    build_context as build_manual_context,
    build_references as build_manual_references,
    recovered_documents as recovered_manual_documents,
)


class FakeStateGraph:
    """Tiny LangGraph replacement that preserves node and edge behavior for tests."""

    latest: "FakeStateGraph | None" = None

    def __init__(self, state_type: object) -> None:
        FakeStateGraph.latest = self
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
        self.assertEqual(len(llm.messages), 1)
        self.assertEqual(llm.answer_count, 1)
        system_message, human_message = llm.messages[-1]
        self.assertIn("Responde ÚNICAMENTE", system_message.content)
        self.assertIn("Contexto recuperado:", human_message.content)
        self.assertIn("¿Qué exige la norma?", human_message.content)
        self.assertIsNotNone(FakeStateGraph.latest)
        self.assertIn("retrieval_relevance_grading", FakeStateGraph.latest.nodes)
        self.assertNotIn("self_refine", FakeStateGraph.latest.nodes)
        self.assertEqual(FakeStateGraph.latest.edges["expand_parent_documents"], "retrieval_relevance_grading")
        self.assertEqual(FakeStateGraph.latest.edges["retrieval_relevance_grading"], "record_retrieval_trace")
        self.assertEqual(FakeStateGraph.latest.edges["generate_answer"], "format_result")

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
        self.assertIn("relevance_grading_trace", state)
        self.assertEqual(state["relevance_grading_trace"]["relevant_count"], 2)

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
        self.assertEqual(len(llm.messages), 0)

    def test_build_langgraph_rag_context_uses_parent_text_after_child_retrieval(self) -> None:
        fake_graph_module = types.SimpleNamespace(StateGraph=FakeStateGraph, END="__end__")
        llm = FakeLlm()
        parent_lookup = {
            "parent-1": RetrievedDocument(
                "Full parent context text",
                {"document_id": "parent-1", "document_type": "parent_chunk", "source_stem": "Decreto 1072"},
            )
        }

        def retriever(question: str, top_k: int) -> dict[str, object]:
            return {
                "ids": [["child-1"]],
                "documents": [["Small child text"]],
                "metadatas": [[{"document_type": "child_chunk", "parent_id": "parent-1", "source_stem": "Decreto 1072"}]],
            }

        with patch.dict(
            sys.modules,
            {
                "langgraph": types.SimpleNamespace(),
                "langgraph.graph": fake_graph_module,
                "langchain_core.messages": fake_message_module(),
            },
        ):
            graph = build_langgraph_rag(llm, retriever, top_k=1, parent_lookup=parent_lookup)
            result = answer_with_langgraph("¿Qué exige la norma?", graph)

        self.assertIn("Contenido:\nFull parent context text", result.context)
        self.assertNotIn("Small child text", result.context)

    def test_build_langgraph_rag_preserves_table_result_with_parent_lookup(self) -> None:
        fake_graph_module = types.SimpleNamespace(StateGraph=FakeStateGraph, END="__end__")
        llm = FakeLlm()
        parent_lookup = {"parent-1": RetrievedDocument("Parent text", {"document_type": "parent_chunk"})}

        with patch.dict(
            sys.modules,
            {
                "langgraph": types.SimpleNamespace(),
                "langgraph.graph": fake_graph_module,
                "langchain_core.messages": fake_message_module(),
            },
        ):
            graph = build_langgraph_rag(llm, self.fake_retriever, top_k=1, parent_lookup=parent_lookup)
            state = graph.invoke({"question": "¿Qué exige la norma?"})

        self.assertEqual(state["documents"][0].document, "Contexto normativo")
        self.assertEqual(state["documents"][0].metadata["document_type"], "table")

    def test_build_langgraph_rag_works_unchanged_without_parent_lookup(self) -> None:
        fake_graph_module = types.SimpleNamespace(StateGraph=FakeStateGraph, END="__end__")
        llm = FakeLlm()
        retrieved_queries: list[str] = []

        def retriever(question: str, top_k: int) -> dict[str, object]:
            retrieved_queries.append(question)
            return {
                "ids": [["child-1"]],
                "documents": [["Small child text"]],
                "metadatas": [[{"document_type": "child_chunk", "parent_id": "parent-1", "source_stem": "Decreto 1072"}]],
            }

        with patch.dict(
            sys.modules,
            {
                "langgraph": types.SimpleNamespace(),
                "langgraph.graph": fake_graph_module,
                "langchain_core.messages": fake_message_module(),
            },
        ):
            graph = build_langgraph_rag(llm, retriever, top_k=1)
            state = graph.invoke({"question": "¿Qué exige la norma?"})

        self.assertIn("Contenido:\nSmall child text", state["context"])
        self.assertEqual(retrieved_queries, ["¿Qué exige la norma?"])
        self.assertNotIn("query_expansion_trace", state)

    def test_build_langgraph_rag_filters_relevance_before_context_and_trace(self) -> None:
        fake_graph_module = types.SimpleNamespace(StateGraph=FakeStateGraph, END="__end__")
        llm = FakeLlm(
            relevance_grades=[
                {"relevant": False, "reason": "No aporta evidencia útil."},
                {"relevant": True, "reason": "Aporta evidencia normativa directa."},
            ]
        )

        def retriever(question: str, top_k: int) -> dict[str, object]:
            return {
                "documents": [["Documento no relevante", "Documento relevante"]],
                "metadatas": [[{"source_stem": "Fuente 1"}, {"source_stem": "Fuente 2"}]],
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
            state = graph.invoke({"question": "¿Qué exige la norma?"})

        self.assertEqual([document.document for document in state["documents"]], ["Documento relevante"])
        self.assertNotIn("Documento no relevante", state["context"])
        self.assertIn("Documento relevante", state["context"])
        self.assertEqual(state["retrieval_traces"], [{"document_count": 1}])
        self.assertEqual(state["relevance_grading_trace"]["rejected_count"], 1)

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

    def __init__(
        self,
        responses: list[str] | None = None,
        expansion_terms: list[str] | None = None,
        relevance_grades: list[object] | None = None,
    ) -> None:
        self.messages: list[list[object]] = []
        self.grade_messages: list[list[object]] = []
        self.responses = responses or ["Generated from fake LLM."]
        self.expansion_terms = expansion_terms or []
        self.relevance_grades = iter(relevance_grades or [])
        self.answer_count = 0

    def with_structured_output(self, schema: object, method: str | None = None) -> object:
        llm = self

        class StructuredLlm:
            def invoke(self, messages: list[object]) -> object:
                llm.grade_messages.append(messages)
                if getattr(schema, "__name__", "") == "RelevanceGrade":
                    return next(
                        llm.relevance_grades,
                        {"relevant": True, "reason": "El documento contiene evidencia normativa directa."},
                    )
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
