"""Tests for the interactive normative consultation RAG CLI."""

from __future__ import annotations

import io
import os
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from agents.consulta_normativa.manual_implementation import main as cli


class ConsultaNormativaCliTest(unittest.TestCase):
    """Verify interactive orchestration, generation, and controlled errors."""

    def test_parser_accepts_base_command_without_subcommands(self) -> None:
        with patch.object(cli, "build_rag_runtime", return_value=self.build_runtime()), patch.object(
            cli,
            "run_interactive_loop",
            return_value=0,
        ):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 0)

    def test_parser_rejects_removed_ask_subcommand(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
            cli.main(["ask", "¿Qué debe incluir el plan anual?"])

        self.assertEqual(context.exception.code, 2)
        self.assertIn("unrecognized arguments", stderr.getvalue())

    def test_build_default_generator_uses_groq_model_and_returns_content(self) -> None:
        captured: dict[str, object] = {}

        class FakeChatGroq:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

            def invoke(self, prompt: str) -> object:
                captured["prompt"] = prompt
                return types.SimpleNamespace(content="generated answer")

        fake_module = types.SimpleNamespace(ChatGroq=FakeChatGroq)

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}), patch.dict(
            "sys.modules", {"langchain_groq": fake_module}
        ):
            generator = cli.build_default_generator()

        self.assertEqual(captured["model"], "openai/gpt-oss-120b")
        self.assertEqual(captured["temperature"], 0)
        self.assertEqual(generator("prompt text"), "generated answer")
        self.assertEqual(captured["prompt"], "prompt text")

    def test_main_builds_runtime_once_and_enters_loop(self) -> None:
        runtime = self.build_runtime()

        with patch.object(cli, "build_rag_runtime", return_value=runtime) as build_runtime, patch.object(
            cli, "run_interactive_loop", return_value=0
        ) as run_loop:
            exit_code = cli.main([])

        self.assertEqual(exit_code, 0)
        build_runtime.assert_called_once_with()
        run_loop.assert_called_once_with(runtime)

    def test_build_rag_runtime_initializes_dependencies_once_for_reused_runtime(self) -> None:
        calls: list[str] = []

        def fake_answer_question(question: str, retriever: object, **kwargs: object) -> object:
            calls.append(f"answer:{question}:{retriever}:{kwargs['generator']('prompt')}")
            return types.SimpleNamespace(answer=f"answer for {question}", references=[], context="context")

        def fake_chroma_retriever(collection: object) -> object:
            calls.append(f"retriever:{collection}")
            return "runtime-retriever"

        def fake_open_existing_collection(chroma_path: object, collection_name: str) -> object:
            calls.append(f"collection:{chroma_path}:{collection_name}")
            return "opened-collection"

        dependencies = cli.RagDependencies(
            answer_question=fake_answer_question,
            chroma_retriever=fake_chroma_retriever,  # type: ignore[arg-type]
            open_existing_collection=fake_open_existing_collection,
            chroma_path="data/processed/chroma",
            collection_name="sg_sst_base_rag",
        )

        with patch.object(cli, "load_rag_dependencies", return_value=dependencies) as load_dependencies, patch.object(
            cli, "build_default_generator", return_value=lambda prompt: "generated"
        ) as build_generator:
            runtime = cli.build_rag_runtime()

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            cli.answer_once(runtime, "pregunta uno")
            cli.answer_once(runtime, "pregunta dos")

        load_dependencies.assert_called_once_with()
        build_generator.assert_called_once_with()
        self.assertEqual(
            calls,
            [
                "collection:data/processed/chroma:sg_sst_base_rag",
                "retriever:opened-collection",
                "answer:pregunta uno:runtime-retriever:generated",
                "answer:pregunta dos:runtime-retriever:generated",
            ],
        )

    def test_one_question_then_exit_calls_answer_once_and_prints_answer(self) -> None:
        calls: list[tuple[str, object, dict[str, object]]] = []

        def fake_answer_question(question: str, retriever: object, **kwargs: object) -> object:
            calls.append((question, retriever, kwargs))
            return types.SimpleNamespace(answer="Generated answer.", references=["Decreto 1072 (decreto)"], context="context")

        runtime = self.build_runtime(answer_question=fake_answer_question)
        stdout = io.StringIO()

        with patch("builtins.input", side_effect=["¿Qué debe incluir el plan anual?", "exit"]), redirect_stdout(stdout):
            exit_code = cli.run_interactive_loop(runtime)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            calls,
            [("¿Qué debe incluir el plan anual?", "retriever", {"generator": runtime.generator, "top_k": 5})],
        )
        self.assertIn("RAG normativo listo", stdout.getvalue())
        self.assertIn("Respuesta:\nGenerated answer.\n", stdout.getvalue())
        self.assertIn("Referencias:\n- Decreto 1072 (decreto)", stdout.getvalue())

    def test_blank_input_is_ignored(self) -> None:
        runtime = self.build_runtime(answer_question=lambda question, retriever, **kwargs: self.fail("Blank input ran RAG"))

        with patch("builtins.input", side_effect=["", "   ", "exit"]):
            exit_code = cli.run_interactive_loop(runtime)

        self.assertEqual(exit_code, 0)

    def test_per_question_exception_prints_controlled_error_and_continues(self) -> None:
        calls: list[str] = []

        def fake_answer_question(question: str, retriever: object, **kwargs: object) -> object:
            calls.append(question)
            if question == "falla":
                raise RuntimeError("provider rejected request")
            return types.SimpleNamespace(answer="Recovered answer.", references=[], context="context")

        runtime = self.build_runtime(answer_question=fake_answer_question)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("builtins.input", side_effect=["falla", "siguiente", "exit"]), redirect_stdout(stdout), redirect_stderr(
            stderr
        ):
            exit_code = cli.run_interactive_loop(runtime)

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, ["falla", "siguiente"])
        self.assertIn("Error during RAG execution", stderr.getvalue())
        self.assertIn("provider rejected request", stderr.getvalue())
        self.assertIn("Respuesta:\nRecovered answer.", stdout.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_exit_and_quit_exit_with_code_zero(self) -> None:
        runtime = self.build_runtime()

        for exit_text in ("exit", "quit", "EXIT", "QUIT"):
            with self.subTest(exit_text=exit_text), patch("builtins.input", side_effect=[exit_text]):
                self.assertEqual(cli.run_interactive_loop(runtime), 0)

    def test_dependency_loading_failure_prints_stage_and_original_error(self) -> None:
        stderr = io.StringIO()

        with patch.object(
            cli,
            "load_rag_dependencies",
            side_effect=cli.DependencyLoadError("missing dependency detail"),
        ), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during dependency loading", stderr.getvalue())
        self.assertIn("missing dependency detail", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_collection_open_failure_prints_stage_and_original_error(self) -> None:
        stderr = io.StringIO()
        dependencies = cli.RagDependencies(
            answer_question=lambda question, retriever, **kwargs: object(),
            chroma_retriever=lambda collection: lambda question, top_k: {},
            open_existing_collection=lambda chroma_path, collection_name: (_ for _ in ()).throw(
                RuntimeError("collection does not exist")
            ),
            chroma_path="data/processed/chroma",
            collection_name="sg_sst_base_rag",
        )

        with patch.object(cli, "load_rag_dependencies", return_value=dependencies), patch.object(
            cli, "build_default_generator", return_value=lambda prompt: "Generated answer."
        ), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during Chroma collection opening", stderr.getvalue())
        self.assertIn("collection does not exist", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_generator_construction_failure_returns_controlled_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        dependencies = cli.RagDependencies(
            answer_question=lambda question, retriever, **kwargs: object(),
            chroma_retriever=lambda collection: lambda question, top_k: {},
            open_existing_collection=lambda chroma_path, collection_name: object(),
            chroma_path="data/processed/chroma",
            collection_name="sg_sst_base_rag",
        )

        with patch.object(cli, "load_rag_dependencies", return_value=dependencies), patch.object(
            cli, "build_default_generator", side_effect=cli.GeneratorBuildError("langchain_groq is not installed.")
        ), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during generator setup", stderr.getvalue())
        self.assertIn("langchain_groq is not installed", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_provider_setup_failure_preserves_raw_exception_message(self) -> None:
        class FakeChatGroq:
            def __init__(self, **kwargs: object) -> None:
                raise RuntimeError("secret provider detail")

        fake_module = types.SimpleNamespace(ChatGroq=FakeChatGroq)

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}), patch.dict(
            "sys.modules", {"langchain_groq": fake_module}
        ):
            with self.assertRaises(cli.OperationalError) as context:
                cli.build_default_generator()

        self.assertEqual(str(context.exception), "Could not build the Groq generator: secret provider detail")

    def test_missing_groq_api_key_returns_controlled_initialization_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        dependencies = cli.RagDependencies(
            answer_question=lambda question, retriever, **kwargs: object(),
            chroma_retriever=lambda collection: lambda question, top_k: {},
            open_existing_collection=lambda chroma_path, collection_name: object(),
            chroma_path="data/processed/chroma",
            collection_name="sg_sst_base_rag",
        )

        with patch.object(cli, "load_rag_dependencies", return_value=dependencies), patch.dict(
            os.environ, {}, clear=True
        ), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during generator setup", stderr.getvalue())
        self.assertIn("GROQ_API_KEY", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_missing_langchain_groq_returns_controlled_initialization_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        dependencies = cli.RagDependencies(
            answer_question=lambda question, retriever, **kwargs: object(),
            chroma_retriever=lambda collection: lambda question, top_k: {},
            open_existing_collection=lambda chroma_path, collection_name: object(),
            chroma_path="data/processed/chroma",
            collection_name="sg_sst_base_rag",
        )

        with patch.object(cli, "load_rag_dependencies", return_value=dependencies), patch.dict(
            os.environ, {"GROQ_API_KEY": "test-key"}
        ), patch.dict("sys.modules", {"langchain_groq": None}), redirect_stderr(stderr):
            exit_code = cli.main([])

        self.assertEqual(exit_code, 2)
        self.assertIn("Error during generator setup", stderr.getvalue())
        self.assertIn("langchain_groq is not installed", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def build_runtime(self, answer_question: object | None = None) -> cli.RagRuntime:
        def default_answer_question(question: str, retriever: object, **kwargs: object) -> object:
            return types.SimpleNamespace(answer="Generated answer.", references=[], context="context")

        return cli.RagRuntime(
            answer_question=answer_question or default_answer_question,
            retriever="retriever",  # type: ignore[arg-type]
            generator=lambda prompt: "Generated answer.",
        )


if __name__ == "__main__":
    unittest.main()
