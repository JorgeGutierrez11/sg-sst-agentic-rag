"""Tests for the base normative consultation RAG flow."""

import unittest

from agents.consulta_normativa.rag_base import answer_question, chroma_retriever


class ConsultaNormativaRagBaseTest(unittest.TestCase):
    """Verify prompt, context, references, and injectable generation behavior."""

    def test_answer_uses_recovered_context_and_basic_references(self) -> None:
        captured_prompt = ""

        def fake_retriever(question: str, top_k: int) -> dict[str, object]:
            self.assertEqual(question, "¿Qué exige el SG-SST?")
            self.assertEqual(top_k, 2)
            return {
                "documents": [["El SG-SST debe implementarse con mejora continua."]],
                "metadatas": [
                    [
                        {
                            "source_stem": "Decreto 1072 de 2015",
                            "article": "2.2.4.6.1",
                            "document_type": "child_chunk",
                        }
                    ]
                ],
                "distances": [[0.12]],
            }

        def fake_generator(prompt: str) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return "Respuesta generada desde contexto recuperado."

        result = answer_question("¿Qué exige el SG-SST?", fake_retriever, fake_generator, top_k=2)

        self.assertEqual(result.answer, "Respuesta generada desde contexto recuperado.")
        self.assertIn("El SG-SST debe implementarse", result.context)
        self.assertIn("Answer only with the recovered context", captured_prompt)
        self.assertEqual(result.references, ["Decreto 1072 de 2015, artículo 2.2.4.6.1 (child_chunk)"])

    def test_fallback_is_deterministic_without_generator(self) -> None:
        def fake_retriever(question: str, top_k: int) -> dict[str, object]:
            return {
                "documents": [["Tabla de estándares mínimos."]],
                "metadatas": [[{"source_stem": "Resolución 0312 de 2019", "document_type": "table"}]],
                "distances": [[0.2]],
            }

        result = answer_question("Pregunta", fake_retriever)

        self.assertIn("Borrador fundamentado solo en el contexto recuperado", result.answer)
        self.assertIn("Resolución 0312 de 2019 (table)", result.answer)

    def test_empty_retrieval_reports_insufficient_evidence(self) -> None:
        def unexpected_generator(prompt: str) -> str:
            raise AssertionError("Generator must not run without recovered evidence")

        result = answer_question(
            "Pregunta",
            lambda question, top_k: {"documents": [[]], "metadatas": [[]]},
            unexpected_generator,
        )

        self.assertEqual(result.answer, "La evidencia recuperada es insuficiente para responder la pregunta.")
        self.assertEqual(result.references, [])

    def test_chroma_retriever_uses_expected_query_shape(self) -> None:
        class FakeCollection:
            def query(self, **kwargs: object) -> dict[str, object]:
                self.kwargs = kwargs
                return {"documents": [["context"]], "metadatas": [[{}]], "distances": [[0.1]]}

        collection = FakeCollection()
        result = chroma_retriever(collection)("pregunta", 3)

        self.assertEqual(result["documents"], [["context"]])
        self.assertEqual(collection.kwargs["query_texts"], ["pregunta"])
        self.assertEqual(collection.kwargs["n_results"], 3)
        self.assertEqual(collection.kwargs["include"], ["documents", "metadatas", "distances"])


if __name__ == "__main__":
    unittest.main()
