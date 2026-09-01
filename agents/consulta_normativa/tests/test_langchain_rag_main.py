"""Tests for the direct experimental LangChain RAG entrypoint."""

from __future__ import annotations

import io
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import mock_open, patch

from agents.consulta_normativa.langchain_rag import main as cli


class LangChainRagMainTest(unittest.TestCase):
    """Verify direct execution without real Chroma or DeepSeek calls."""

    def test_no_args_builds_runtime_and_runs_interactive_loop(self) -> None:
        runtime = self.build_runtime()

        with patch.object(cli, "build_runtime", return_value=runtime) as build_runtime, patch.object(
            cli, "run_interactive_loop", return_value=0
        ) as run_loop:
            exit_code = cli.main([])

        self.assertEqual(exit_code, 0)
        build_runtime.assert_called_once_with()
        run_loop.assert_called_once_with(runtime)

    def test_optional_positional_question_answers_once_without_subcommands(self) -> None:
        runtime = self.build_runtime()
        stdout = io.StringIO()

        with patch.object(cli, "build_runtime", return_value=runtime), redirect_stdout(stdout):
            exit_code = cli.main(["What does the employer need?"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(runtime.calls, ["What does the employer need?:graph"])
        self.assertIn("Answer:\nGenerated answer.", stdout.getvalue())
        self.assertIn("References:\n- Decreto 1072", stdout.getvalue())

    def test_parser_rejects_extra_arguments_instead_of_subcommands(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
            cli.main(["ask", "What does the employer need?"])

        self.assertEqual(context.exception.code, 2)
        self.assertIn("unrecognized arguments", stderr.getvalue())

    def test_interactive_loop_ignores_blank_input_and_exits(self) -> None:
        runtime = self.build_runtime()

        with patch("builtins.input", side_effect=["", "   ", "exit"]):
            exit_code = cli.run_interactive_loop(runtime)

        self.assertEqual(exit_code, 0)
        self.assertEqual(runtime.calls, [])

    def test_interactive_question_prints_controlled_rag_error_and_continues(self) -> None:
        runtime = self.build_runtime(fail_first=True)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("builtins.input", side_effect=["fail", "recover", "quit"]), redirect_stdout(stdout), redirect_stderr(
            stderr
        ):
            exit_code = cli.run_interactive_loop(runtime)

        self.assertEqual(exit_code, 0)
        self.assertEqual(runtime.calls, ["fail:graph", "recover:graph"])
        self.assertIn("Error during RAG execution", stderr.getvalue())
        self.assertIn("fake RAG failure", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertIn("Answer:\nGenerated answer.", stdout.getvalue())

    def test_missing_deepseek_api_key_returns_controlled_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        dependencies = self.build_dependencies(
            build_deepseek_llm=lambda: (_ for _ in ()).throw(ValueError("DEEPSEEK_API_KEY"))
        )

        with patch.object(cli, "load_dependencies", return_value=dependencies), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during initialization", stderr.getvalue())
        self.assertIn("DEEPSEEK_API_KEY", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_missing_chroma_path_or_collection_returns_controlled_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        dependencies = self.build_dependencies(
            open_existing_collection=lambda path, name: (_ for _ in ()).throw(
                ValueError("ChromaDB persist path does not exist")
            )
        )

        with patch.object(cli, "load_dependencies", return_value=dependencies), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during initialization", stderr.getvalue())
        self.assertIn("ChromaDB persist path does not exist", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_missing_dependency_returns_controlled_error_without_traceback(self) -> None:
        stderr = io.StringIO()

        with patch.object(
            cli,
            "load_dependencies",
            side_effect=cli.OperationalError("Required runtime dependency is not installed: langchain_openai"),
        ), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during initialization", stderr.getvalue())
        self.assertIn("langchain_openai", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_build_runtime_uses_deepseek_llm_builder(self) -> None:
        calls: list[str] = []
        dependencies = self.build_dependencies(
            build_deepseek_llm=lambda: calls.append("deepseek") or "llm",
            build_langgraph_rag=lambda llm, retriever, **kwargs: FakeDrawableGraph(),
        )

        with patch.object(cli, "load_dependencies", return_value=dependencies), patch("builtins.open", mock_open()):
            cli.build_runtime()

        self.assertEqual(calls, ["deepseek"])

    def test_build_runtime_can_skip_graph_image_output(self) -> None:
        graph = FakeDrawableGraph()
        dependencies = self.build_dependencies(
            build_langgraph_rag=lambda llm, retriever, **kwargs: graph,
        )

        with patch.object(cli, "load_dependencies", return_value=dependencies):
            runtime = cli.build_runtime(write_graph_image=False)

        self.assertIs(runtime.graph, graph)
        self.assertFalse(graph.draw_mermaid_png_called)

    def test_build_runtime_opens_dense_and_sparse_indexes_and_uses_hybrid_retriever_boundary(self) -> None:
        calls: list[str] = []

        def fake_open_existing_collection(path: object, collection_name: str) -> str:
            calls.append(f"collection:{path}:{collection_name}")
            return "collection"

        def fake_open_existing_index(path: object) -> str:
            calls.append(f"index:{path}")
            return "index"

        def fake_hybrid_retriever(
            collection: object,
            sparse_index: object,
            *,
            candidate_top_k: int,
            rrf_k: int,
        ) -> object:
            calls.append(f"retriever:{collection}:{sparse_index}:{candidate_top_k}:{rrf_k}")
            return "hybrid-retriever"

        graph = FakeDrawableGraph()
        dependencies = self.build_dependencies(
            build_deepseek_llm=lambda: "llm",
            build_langgraph_rag=lambda llm, retriever, *, top_k, parent_lookup: calls.append(
                f"graph:{llm}:{retriever}:{top_k}:{parent_lookup}"
            )
            or graph,
            load_parent_documents=lambda path: calls.append(f"parents:{path}") or {"parent-1": "parent"},
            open_existing_collection=fake_open_existing_collection,
            open_existing_index=fake_open_existing_index,
            hybrid_retriever=fake_hybrid_retriever,
        )

        with patch.object(cli, "load_dependencies", return_value=dependencies), patch("builtins.open", mock_open()):
            runtime = cli.build_runtime()

        self.assertEqual(
            calls,
            [
                f"collection:{cli.DEFAULT_CHROMA_PATH}:sg_sst_base_rag",
                f"index:{cli.DEFAULT_BM25_PATH}",
                f"parents:{cli.DEFAULT_PARENT_CHUNKS_PATH}",
                f"retriever:collection:index:{cli.HYBRID_CANDIDATE_TOP_K}:{cli.HYBRID_RRF_K}",
                f"graph:llm:hybrid-retriever:{cli.RETRIEVAL_TOP_K}:{{'parent-1': 'parent'}}",
            ],
        )
        self.assertIs(runtime.graph, graph)

    def build_runtime(self, fail_first: bool = False) -> object:
        calls: list[str] = []

        def fake_answer_with_langgraph(question: str, graph: object) -> object:
            calls.append(f"{question}:{graph}")
            if fail_first and question == "fail":
                raise RuntimeError("fake RAG failure")
            return types.SimpleNamespace(
                answer="Generated answer.",
                references=["Decreto 1072"],
                prompt="Prompt sent to model.",
            )

        runtime = cli.RagRuntime(
            answer_with_langgraph=fake_answer_with_langgraph,
            graph="graph",
        )
        return types.SimpleNamespace(**runtime.__dict__, calls=calls)

    def build_dependencies(
        self,
        build_deepseek_llm: object | None = None,
        build_langgraph_rag: object | None = None,
        answer_with_langgraph: object | None = None,
        hybrid_retriever: object | None = None,
        load_parent_documents: object | None = None,
        open_existing_collection: object | None = None,
        open_existing_index: object | None = None,
    ) -> cli.RuntimeDependencies:
        return cli.RuntimeDependencies(
            build_deepseek_llm=build_deepseek_llm or (lambda: object()),
            build_langgraph_rag=build_langgraph_rag or (lambda llm, retriever, **kwargs: object()),
            answer_with_langgraph=answer_with_langgraph or (lambda question, graph: object()),
            hybrid_retriever=hybrid_retriever or (lambda collection, sparse_index, **kwargs: lambda question, top_k: {}),
            load_parent_documents=load_parent_documents or (lambda path: {}),
            open_existing_collection=open_existing_collection or (lambda path, collection_name: object()),
            open_existing_index=open_existing_index or (lambda path: object()),
        )

class FakeDrawableGraph:
    """Small compiled-graph fake with drawing support for runtime construction tests."""

    def __init__(self) -> None:
        self.draw_mermaid_png_called = False

    def get_graph(self) -> object:
        return self

    def draw_mermaid_png(self) -> bytes:
        self.draw_mermaid_png_called = True
        return b"graph"


if __name__ == "__main__":
    unittest.main()
