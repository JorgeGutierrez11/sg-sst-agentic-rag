"""Tests for the experimental LangChain-style linear RAG pipeline."""

import types
import unittest

from agents.consulta_normativa.langchain_rag.chain import answer_with_langchain, build_langchain_rag_chain


class FakeLlm:
    """Small LangChain-like fake for deterministic tests."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> object:
        self.prompts.append(prompt)
        return types.SimpleNamespace(content="Generated from fake LLM.")


class LangChainRagChainTest(unittest.TestCase):
    """Verify the linear pipeline without real Groq or Chroma calls."""

    def test_answer_with_langchain_retrieves_formats_prompts_and_invokes_llm(self) -> None:
        calls: list[tuple[str, int]] = []
        llm = FakeLlm()

        def fake_retriever(question: str, top_k: int) -> dict[str, object]:
            calls.append((question, top_k))
            return {
                "documents": [["El empleador debe implementar el SG-SST."]],
                "metadatas": [
                    [
                        {
                            "source_stem": "Decreto 1072 de 2015",
                            "document_type": "child_chunk",
                            "normative_document_type": "decreto",
                            "article": "2.2.4.6.1",
                        }
                    ]
                ],
            }

        result = answer_with_langchain("¿Qué debe hacer el empleador?", fake_retriever, llm, top_k=2)

        self.assertEqual(calls, [("¿Qué debe hacer el empleador?", 2)])
        self.assertEqual(result.answer, "Generated from fake LLM.")
        self.assertIn("El empleador debe implementar", result.context)
        self.assertIn("Responde ÚNICAMENTE con información", result.prompt)
        self.assertEqual(result.references, ["Decreto 1072 de 2015, artículo 2.2.4.6.1 (decreto)"])
        self.assertEqual(llm.prompts, [result.prompt])

    def test_empty_retrieval_does_not_invoke_llm(self) -> None:
        def unexpected_llm(prompt: str) -> str:
            raise AssertionError("LLM must not run without retrieved evidence")

        result = answer_with_langchain(
            "Pregunta",
            lambda question, top_k: {"documents": [[]], "metadatas": [[]]},
            unexpected_llm,
        )

        self.assertEqual(result.answer, "La evidencia recuperada es insuficiente para responder la pregunta.")
        self.assertEqual(result.references, [])

    def test_build_langchain_rag_chain_returns_callable_pipeline(self) -> None:
        chain = build_langchain_rag_chain(
            lambda question, top_k: {"documents": [["context"]], "metadatas": [[{}]]},
            lambda prompt: "callable answer",
            top_k=1,
        )

        result = chain("Pregunta")

        self.assertEqual(result.answer, "callable answer")
        self.assertIn("context", result.context)


if __name__ == "__main__":
    unittest.main()
