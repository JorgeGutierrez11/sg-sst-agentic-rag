"""Tests for the experimental LangGraph RAG flow."""

import sys
import types
import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.graph import (
    answer_with_langgraph,
    answer_with_linear_graph,
    build_langgraph_rag,
)


class FakeStateGraph:
    """Tiny LangGraph replacement that preserves node and edge behavior for tests."""

    def __init__(self, state_type: object) -> None:
        self.nodes: dict[str, object] = {}
        self.entry_point = ""

    def add_node(self, name: str, node: object) -> None:
        self.nodes[name] = node

    def set_entry_point(self, name: str) -> None:
        self.entry_point = name

    def add_edge(self, start: str, end: str) -> None:
        return None

    def compile(self) -> object:
        nodes = self.nodes

        class CompiledGraph:
            def invoke(self, state: dict[str, object]) -> dict[str, object]:
                for name in ("retrieve", "format_context", "generate", "format_result"):
                    state.update(nodes[name](state))
                return state

        return CompiledGraph()


class LangGraphRagTest(unittest.TestCase):
    """Verify graph orchestration without real LangGraph, Groq, or Chroma calls."""

    def test_answer_with_linear_graph_runs_minimal_node_sequence(self) -> None:
        result = answer_with_linear_graph(
            "¿Qué exige la norma?",
            self.fake_retriever,
            lambda prompt: "Graph answer.",
            top_k=1,
        )

        self.assertEqual(result.answer, "Graph answer.")
        self.assertIn("Contenido:\nContexto normativo", result.context)
        self.assertEqual(result.references, ["Resolución 0312 de 2019, tabla 1 (table)"])

    def test_build_langgraph_rag_uses_lazy_import_and_compiled_graph(self) -> None:
        fake_graph_module = types.SimpleNamespace(StateGraph=FakeStateGraph, END="__end__")

        with patch.dict(sys.modules, {"langgraph": types.SimpleNamespace(), "langgraph.graph": fake_graph_module}):
            graph = build_langgraph_rag(lambda prompt: "Compiled graph answer.", self.fake_retriever, top_k=1)

        result = answer_with_langgraph("¿Qué exige la norma?", graph)

        self.assertEqual(result.answer, "Compiled graph answer.")
        self.assertIn("Resolución 0312 de 2019", result.context)

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


if __name__ == "__main__":
    unittest.main()
