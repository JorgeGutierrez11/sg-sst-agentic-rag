"""Tests for SG-SST Multi-Query generation."""

import sys
import types
import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.query_understanding import multi_query


class LangChainRagMultiQueryTest(unittest.TestCase):
    """Verify Multi-Query generation with fakes only."""

    def test_build_multi_query_messages_uses_lazy_message_import(self) -> None:
        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}):
            messages = multi_query.build_multi_query_messages("¿Qué exige la norma?", max_variants=3)

        system_message, human_message = messages
        self.assertIn("SG-SST colombiano", system_message.content)
        self.assertIn("No inventes normas", system_message.content)
        self.assertIn("máximo 3", human_message.content)
        self.assertIn("¿Qué exige la norma?", human_message.content)

    def test_parse_query_variants_cleans_lines_dedupes_and_excludes_original(self) -> None:
        raw_text = """
        1. obligaciones del empleador en SG-SST
        - evidencia documental SG-SST
        * "evidencia documental SG-SST"
        ¿Qué exige la norma?
        2) estándares mínimos aplicables
        procedimiento de cumplimiento
        """

        variants = multi_query.parse_query_variants(raw_text, "¿Qué exige la norma?", max_variants=3)

        self.assertEqual(
            variants,
            [
                "obligaciones del empleador en SG-SST",
                "evidencia documental SG-SST",
                "estándares mínimos aplicables",
            ],
        )

    def test_generate_query_variants_node_success_uses_llm_text_invocation(self) -> None:
        llm = object()

        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}), patch.object(
            multi_query,
            "invoke_llm_text",
            return_value="obligaciones SG-SST\nevidencia documental",
        ) as invoke_llm_text:
            update = multi_query.generate_query_variants_node(llm, max_variants=3)({"question": "Pregunta original"})

        invoke_llm_text.assert_called_once()
        self.assertIs(invoke_llm_text.call_args.args[0], llm)
        self.assertEqual(update["query_variants"], ["Pregunta original", "obligaciones SG-SST", "evidencia documental"])
        self.assertEqual(
            update["multi_query_trace"],
            {"variant_count": 3, "generated_count": 2, "fallback": False, "error": None},
        )

    def test_generate_query_variants_node_falls_back_on_blank_question_without_invocation(self) -> None:
        with patch.object(multi_query, "invoke_llm_text") as invoke_llm_text:
            update = multi_query.generate_query_variants_node(object(), max_variants=3)({"question": "   "})

        invoke_llm_text.assert_not_called()
        self.assertEqual(update["query_variants"], ["   "])
        self.assertEqual(update["multi_query_trace"]["fallback"], True)
        self.assertEqual(update["multi_query_trace"]["error"], "blank_question")

    def test_generate_query_variants_node_falls_back_on_error_or_no_valid_variants(self) -> None:
        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}), patch.object(
            multi_query,
            "invoke_llm_text",
            return_value="Pregunta original\n\n",
        ):
            blank_update = multi_query.generate_query_variants_node(object(), max_variants=3)({"question": "Pregunta original"})

        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}), patch.object(
            multi_query,
            "invoke_llm_text",
            side_effect=RuntimeError("fake failure"),
        ):
            error_update = multi_query.generate_query_variants_node(object(), max_variants=3)({"question": "Pregunta original"})

        self.assertEqual(blank_update["query_variants"], ["Pregunta original"])
        self.assertEqual(blank_update["multi_query_trace"]["error"], "blank_model_output")
        self.assertEqual(error_update["query_variants"], ["Pregunta original"])
        self.assertEqual(error_update["multi_query_trace"]["error"], "RuntimeError")


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
