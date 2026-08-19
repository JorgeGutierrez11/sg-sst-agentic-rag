"""Tests for SG-SST query rewriting before LangGraph retrieval."""

import sys
import types
import unittest
from unittest.mock import patch

from agents.consulta_normativa.langchain_rag.query_understanding import rewrite_query


class LangChainRagQueryRewriteTest(unittest.TestCase):
    """Verify query rewriting with fakes only."""

    def test_build_query_rewrite_messages_uses_lazy_message_import(self) -> None:
        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}):
            messages = rewrite_query.build_query_rewrite_messages("¿Qué exige la norma?")

        system_message, human_message = messages
        self.assertIn("SG-SST", system_message.content)
        self.assertIn("No respondas", system_message.content)
        self.assertIn("No inventes normas", system_message.content)
        self.assertEqual(human_message.content, "¿Qué exige la norma?")

    def test_successful_rewrite_uses_llm_text_invocation(self) -> None:
        llm = object()

        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}), patch.object(
            rewrite_query,
            "invoke_llm_text",
            return_value=" obligaciones del empleador en SG-SST ",
        ) as invoke_llm_text:
            update = rewrite_query.rewrite_query_node(llm)({"question": "¿Qué tiene que hacer el empleador?"})

        invoke_llm_text.assert_called_once()
        self.assertIs(invoke_llm_text.call_args.args[0], llm)
        self.assertEqual(update["retrieval_query"], "obligaciones del empleador en SG-SST")
        self.assertEqual(update["query_rewrite_trace"], {"changed": True, "fallback": False, "error": None})

    def test_blank_original_question_falls_back_without_invocation(self) -> None:
        with patch.object(rewrite_query, "invoke_llm_text") as invoke_llm_text:
            update = rewrite_query.rewrite_query_node(object())({"question": "   "})

        invoke_llm_text.assert_not_called()
        self.assertEqual(update["retrieval_query"], "   ")
        self.assertEqual(update["query_rewrite_trace"], {"changed": False, "fallback": True, "error": "blank_question"})

    def test_blank_model_output_falls_back_to_original_question(self) -> None:
        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}), patch.object(
            rewrite_query,
            "invoke_llm_text",
            return_value="  ",
        ):
            update = rewrite_query.rewrite_query_node(object())({"question": "Pregunta original"})

        self.assertEqual(update["retrieval_query"], "Pregunta original")
        self.assertEqual(
            update["query_rewrite_trace"],
            {"changed": False, "fallback": True, "error": "blank_model_output"},
        )

    def test_invocation_exception_falls_back_to_original_question(self) -> None:
        with patch.dict(sys.modules, {"langchain_core.messages": fake_message_module()}), patch.object(
            rewrite_query,
            "invoke_llm_text",
            side_effect=RuntimeError("fake failure"),
        ):
            update = rewrite_query.rewrite_query_node(object())({"question": "Pregunta original"})

        self.assertEqual(update["retrieval_query"], "Pregunta original")
        self.assertEqual(update["query_rewrite_trace"], {"changed": False, "fallback": True, "error": "RuntimeError"})


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
