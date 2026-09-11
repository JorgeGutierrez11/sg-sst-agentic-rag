"""Focused tests for normative prompt composition."""

import unittest

from agents.consulta_normativa.langchain_rag.prompts import BASE_SYSTEM_INSTRUCTIONS, build_base_prompt


class LangChainRagPromptTests(unittest.TestCase):
    """Verify the validation-branch prompt contract remains coherent."""

    def test_system_instructions_keep_reviewed_reference_list_contract(self) -> None:
        self.assertIn("lista de los\n   fragmentos normativos citados", BASE_SYSTEM_INSTRUCTIONS)
        self.assertNotIn('Sin sección final de "Fragmentos citados"', BASE_SYSTEM_INSTRUCTIONS)

    def test_base_prompt_contains_one_instruction_block_and_both_contexts(self) -> None:
        prompt = build_base_prompt(
            "¿Qué debe hacer la empresa?",
            "[1] Evidencia normativa",
            "Empresa de riesgo I",
        )

        self.assertEqual(prompt.count("Reglas estrictas:"), 1)
        self.assertIn("Empresa de riesgo I", prompt)
        self.assertIn("[1] Evidencia normativa", prompt)


if __name__ == "__main__":
    unittest.main()
