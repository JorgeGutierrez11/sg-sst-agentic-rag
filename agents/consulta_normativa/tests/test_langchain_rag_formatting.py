"""Tests for experimental LangChain RAG formatting helpers."""

import unittest

from agents.consulta_normativa.langchain_rag.formatting import (
    build_context,
    build_references,
    metadata_context,
    recovered_documents,
    reference_from_metadata,
)
from agents.consulta_normativa.langchain_rag.models import RetrievedDocument


class LangChainRagFormattingTest(unittest.TestCase):
    """Verify formatting parity with the base RAG metadata handling."""

    def test_empty_context_reports_no_retrieved_context(self) -> None:
        self.assertEqual(build_context([]), "No se recuperó contexto.")
        self.assertEqual(build_references([]), [])

    def test_child_chunk_reference_and_context_include_article_metadata(self) -> None:
        document = RetrievedDocument(
            document="El SG-SST debe aplicarse con mejora continua.",
            metadata={
                "source_stem": "Decreto 1072 de 2015",
                "document_type": "child_chunk",
                "normative_document_type": "decreto",
                "article": "2.2.4.6.1",
                "paragraph": "1",
                "numeral": "2",
                "literal": "a",
            },
        )

        context = build_context([document])

        self.assertIn("[1] Decreto 1072 de 2015, artículo 2.2.4.6.1", context)
        self.assertIn("Jerarquía normativa:", context)
        self.assertIn("- Artículo: 2.2.4.6.1", context)
        self.assertIn("Contenido:\nEl SG-SST debe aplicarse", context)
        self.assertEqual(
            build_references([document]),
            ["Decreto 1072 de 2015, artículo 2.2.4.6.1, parágrafo 1, numeral 2, literal a (decreto)"],
        )

    def test_table_reference_uses_one_based_table_and_part_indexes(self) -> None:
        metadata = {
            "source_stem": "Resolución 0312 de 2019",
            "document_type": "table",
            "table_index": 0,
            "table_part_index": 1,
            "table_part_count": 3,
            "table_key": "Resolución 0312 de 2019:0",
            "oversized_row": False,
        }

        self.assertEqual(reference_from_metadata(metadata), "Resolución 0312 de 2019, tabla 1, parte 2 de 3 (table)")
        self.assertIn("- Parte: 2 de 3", metadata_context(metadata))
        self.assertIn("- Fila sobredimensionada: no", metadata_context(metadata))

    def test_metadata_context_includes_useful_technical_traceability(self) -> None:
        context = metadata_context(
            {
                "document_type": "child_chunk",
                "source_document_id": "decreto_1072_2015",
                "parent_id": "parent-1",
                "_document_id": "doc-1",
                "start_char": 10,
                "end_char": 250,
                "has_tables": True,
            }
        )

        self.assertIn("Información general:", context)
        self.assertIn("- Documento fuente: decreto_1072_2015", context)
        self.assertIn("Tablas:", context)
        self.assertIn("- Contiene tablas: sí", context)
        self.assertIn("Trazabilidad técnica:", context)
        self.assertIn("- ID documento: doc-1", context)
        self.assertIn("- ID padre: parent-1", context)

    def test_recovered_documents_normalizes_chroma_result_shape(self) -> None:
        documents = recovered_documents(
            {
                "documents": [["contenido"]],
                "metadatas": [[{"source_stem": "Decreto"}]],
            }
        )

        self.assertEqual(documents, [RetrievedDocument(document="contenido", metadata={"source_stem": "Decreto"})])

    def test_recovered_documents_sets_document_id_from_raw_ids(self) -> None:
        documents = recovered_documents(
            {
                "ids": [["raw-id"]],
                "documents": [["contenido"]],
                "metadatas": [[{"source_stem": "Decreto"}]],
            }
        )

        self.assertEqual(documents[0].metadata["_document_id"], "raw-id")
        self.assertNotIn("_chroma_id", documents[0].metadata)

    def test_recovered_documents_preserves_existing_document_ids(self) -> None:
        documents = recovered_documents(
            {
                "ids": [["raw-id"]],
                "documents": [["contenido"]],
                "metadatas": [[{"document_id": "public-id", "_document_id": "existing-id", "_chroma_id": "existing-chroma"}]],
            }
        )

        self.assertEqual(documents[0].metadata["document_id"], "public-id")
        self.assertEqual(documents[0].metadata["_document_id"], "existing-id")
        self.assertEqual(documents[0].metadata["_chroma_id"], "existing-chroma")


if __name__ == "__main__":
    unittest.main()
