"""Tests for the base normative consultation RAG CLI."""

from __future__ import annotations

import io
import os
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from agents.consulta_normativa import main as cli
from agents.consulta_normativa.rag_base import answer_question


class ConsultaNormativaCliTest(unittest.TestCase):
    """Verify CLI parsing, generation, orchestration, and controlled errors."""

    def test_parser_exposes_ask_command_with_question(self) -> None:
        parser = cli.build_parser()

        args = parser.parse_args(["ask", "¿Qué exige el SG-SST?"])

        self.assertEqual(args.command, "ask")
        self.assertEqual(args.question, "¿Qué exige el SG-SST?")

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

    def test_ask_opens_collection_uses_retriever_answer_flow_and_prints_sections(self) -> None:
        calls: dict[str, object] = {}

        def fake_open_collection(chroma_path: object, collection_name: str) -> object:
            calls["open_collection"] = (chroma_path, collection_name)
            return "collection"

        def fake_chroma_retriever(collection: object) -> object:
            calls["chroma_retriever"] = collection
            return "retriever"

        def fake_answer_question(question: str, retriever: object, **kwargs: object) -> object:
            calls["answer_question"] = (question, retriever, kwargs)
            return types.SimpleNamespace(answer="Generated answer.", references=["Decreto 1072 (child_chunk)"])

        dependencies = cli.RagDependencies(
            answer_question=fake_answer_question,
            chroma_retriever=fake_chroma_retriever,
            open_collection=fake_open_collection,
            chroma_path="data/processed/chroma",
            collection_name="sg_sst_base_rag",
        )

        stdout = io.StringIO()
        def fake_generator(prompt: str) -> str:
            return "Generated answer."

        with patch.object(cli, "load_rag_dependencies", return_value=dependencies), patch.object(
            cli, "build_lazy_default_generator", return_value=fake_generator
        ), redirect_stdout(stdout):
            exit_code = cli.main(["ask", "¿Qué debe incluir el plan anual?"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls["open_collection"], ("data/processed/chroma", "sg_sst_base_rag"))
        self.assertEqual(calls["chroma_retriever"], "collection")
        self.assertEqual(
            calls["answer_question"],
            ("¿Qué debe incluir el plan anual?", "retriever", {"generator": fake_generator, "top_k": 5}),
        )
        self.assertEqual(stdout.getvalue(), "Answer:\nGenerated answer.\n\nReferences:\n- Decreto 1072 (child_chunk)\n")

    def test_ask_empty_retrieval_returns_insufficient_evidence_without_building_groq(self) -> None:
        dependencies = cli.RagDependencies(
            answer_question=answer_question,
            chroma_retriever=lambda collection: lambda question, top_k: {"documents": [[]], "metadatas": [[]]},
            open_collection=lambda chroma_path, collection_name: object(),
            chroma_path="data/processed/chroma",
            collection_name="sg_sst_base_rag",
        )

        stdout = io.StringIO()
        with patch.object(cli, "load_rag_dependencies", return_value=dependencies), patch.object(
            cli, "build_default_generator", side_effect=AssertionError("Groq should not be initialized")
        ), redirect_stdout(stdout):
            exit_code = cli.main(["ask", "Pregunta sin evidencia"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout.getvalue(),
            "Answer:\nRecovered evidence is insufficient to answer the question.\n\nReferences:\n",
        )

    def test_missing_groq_api_key_returns_controlled_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        dependencies = cli.RagDependencies(
            answer_question=answer_question,
            chroma_retriever=lambda collection: lambda question, top_k: {
                "documents": [["Recovered context."]],
                "metadatas": [[{"source_stem": "Decreto 1072", "document_type": "child_chunk"}]],
            },
            open_collection=lambda chroma_path, collection_name: object(),
            chroma_path="data/processed/chroma",
            collection_name="sg_sst_base_rag",
        )

        with patch.object(cli, "load_rag_dependencies", return_value=dependencies), patch.dict(
            os.environ, {}, clear=True
        ), redirect_stderr(stderr):
            exit_code = cli.main(["ask", "Pregunta"])

        self.assertEqual(exit_code, 2)
        self.assertIn("GROQ_API_KEY", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_generator_construction_failure_returns_controlled_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        dependencies = cli.RagDependencies(
            answer_question=answer_question,
            chroma_retriever=lambda collection: lambda question, top_k: {
                "documents": [["Recovered context."]],
                "metadatas": [[{"source_stem": "Decreto 1072", "document_type": "child_chunk"}]],
            },
            open_collection=lambda chroma_path, collection_name: object(),
            chroma_path="data/processed/chroma",
            collection_name="sg_sst_base_rag",
        )

        with patch.object(cli, "load_rag_dependencies", return_value=dependencies), patch.object(
            cli, "build_lazy_default_generator", side_effect=cli.OperationalError("langchain_groq is not installed.")
        ), redirect_stderr(stderr):
            exit_code = cli.main(["ask", "Pregunta"])

        self.assertEqual(exit_code, 2)
        self.assertIn("langchain_groq is not installed", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_provider_setup_failure_does_not_print_raw_exception_details(self) -> None:
        class FakeChatGroq:
            def __init__(self, **kwargs: object) -> None:
                raise RuntimeError("secret provider detail")

        fake_module = types.SimpleNamespace(ChatGroq=FakeChatGroq)

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}), patch.dict(
            "sys.modules", {"langchain_groq": fake_module}
        ):
            with self.assertRaises(cli.OperationalError) as context:
                cli.build_default_generator()

        self.assertEqual(str(context.exception), "Could not build the Groq generator.")
        self.assertNotIn("secret provider detail", str(context.exception))

    def test_missing_langchain_groq_returns_controlled_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        dependencies = cli.RagDependencies(
            answer_question=answer_question,
            chroma_retriever=lambda collection: lambda question, top_k: {
                "documents": [["Recovered context."]],
                "metadatas": [[{"source_stem": "Decreto 1072", "document_type": "child_chunk"}]],
            },
            open_collection=lambda chroma_path, collection_name: object(),
            chroma_path="data/processed/chroma",
            collection_name="sg_sst_base_rag",
        )

        with patch.object(cli, "load_rag_dependencies", return_value=dependencies), patch.dict(
            os.environ, {"GROQ_API_KEY": "test-key"}
        ), patch.dict("sys.modules", {"langchain_groq": None}), redirect_stderr(stderr):
            exit_code = cli.main(["ask", "Pregunta"])

        self.assertEqual(exit_code, 2)
        self.assertIn("langchain_groq is not installed", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

if __name__ == "__main__":
    unittest.main()
