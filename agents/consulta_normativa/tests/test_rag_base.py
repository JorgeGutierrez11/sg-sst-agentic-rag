"""Tests for the base normative consultation RAG flow."""

import unittest

from agents.consulta_normativa.manual_implementation.rag_base import (
    answer_question,
    chroma_retriever,
    metadata_context,
    reference_from_metadata,
)


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
                            "normative_document_type": "decreto",
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
        self.assertIn("Responde ÚNICAMENTE con información que aparezca literalmente", captured_prompt)
        self.assertIn("Contenido:\nEl SG-SST debe implementarse", result.context)
        self.assertEqual(result.references, ["Decreto 1072 de 2015, artículo 2.2.4.6.1 (decreto)"])

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

    def test_child_chunk_full_metadata_includes_structured_context(self) -> None:
        metadata = {
            "document_type": "child_chunk",
            "source_document_id": "decreto_1072_2015",
            "source_stem": "Decreto 1072 de 2015",
            "normative_document_type": "decreto",
            "year": 2015,
            "parent_id": "parent-1",
            "title": "Decreto Único Reglamentario",
            "chapter": "Capítulo 6",
            "article": "2.2.4.6.1",
            "articles": "2.2.4.6.1-2.2.4.6.3",
            "paragraph": "1",
            "numeral": "2",
            "literal": "a",
            "start_char": 10,
            "end_char": 250,
            "has_tables": True,
            "table_keys": "Decreto 1072 de 2015:0",
        }

        context = metadata_context(metadata)

        self.assertIn("Información general:", context)
        self.assertIn("- Tipo de registro: child_chunk", context)
        self.assertIn("- Documento fuente: decreto_1072_2015", context)
        self.assertIn("- Tipo normativo: decreto", context)
        self.assertIn("Jerarquía normativa:", context)
        self.assertIn("- Artículo: 2.2.4.6.1", context)
        self.assertIn("- Parágrafo: 1", context)
        self.assertIn("- Numeral: 2", context)
        self.assertIn("- Literal: a", context)
        self.assertIn("Tablas:", context)
        self.assertIn("- Contiene tablas: sí", context)
        self.assertIn("Trazabilidad técnica:", context)
        self.assertIn("- Inicio: 10", context)
        self.assertIn("- Fin: 250", context)

    def test_child_reference_uses_normative_document_type(self) -> None:
        reference = reference_from_metadata(
            {
                "document_type": "child_chunk",
                "normative_document_type": "resolución",
                "source_stem": "Resolución 0312 de 2019",
                "article": "16",
                "paragraph": "1",
                "numeral": "3",
                "literal": "b",
            }
        )

        self.assertEqual(reference, "Resolución 0312 de 2019, artículo 16, parágrafo 1, numeral 3, literal b (resolución)")
        self.assertNotIn("child_chunk", reference)

    def test_table_metadata_includes_table_section_and_human_part(self) -> None:
        metadata = {
            "document_type": "table",
            "source_stem": "Resolución 0312 de 2019",
            "table_index": 0,
            "table_part_index": 0,
            "table_part_count": 3,
            "table_key": "Resolución 0312 de 2019:0",
            "linked_placeholder": "[TABLE:0]",
            "oversized_row": False,
        }

        context = metadata_context(metadata)
        reference = reference_from_metadata(metadata)

        self.assertEqual(reference, "Resolución 0312 de 2019, tabla 1, parte 1 de 3 (table)")
        self.assertIn("Tabla:", context)
        self.assertIn("- Índice: 0", context)
        self.assertIn("- Parte: 1 de 3", context)
        self.assertIn("- Clave lógica: Resolución 0312 de 2019:0", context)
        self.assertIn("- Marcador vinculado: [TABLE:0]", context)
        self.assertIn("- Fila sobredimensionada: no", context)

    def test_minimal_metadata_omits_empty_sections_and_does_not_crash(self) -> None:
        self.assertEqual(metadata_context({}), "")
        self.assertEqual(reference_from_metadata({}), "fuente desconocida (tipo desconocido)")

        context = metadata_context({"document_type": "child_chunk", "source_stem": "Decreto", "article": ""})

        self.assertIn("Información general:", context)
        self.assertNotIn("Jerarquía normativa:", context)
        self.assertNotIn("Artículo:", context)


if __name__ == "__main__":
    unittest.main()
