"""Focused tests for normative prompt composition."""

import unittest

from agents.consulta_normativa.langchain_rag.prompts import BASE_SYSTEM_INSTRUCTIONS, build_base_prompt


class LangChainRagPromptTests(unittest.TestCase):
    """Verify the validation-branch prompt contract remains coherent."""

    def test_system_instructions_keep_separate_reference_contract(self) -> None:
        self.assertIn(
            'No incluyas una lista final de fragmentos o fuentes.',
            BASE_SYSTEM_INSTRUCTIONS,
        )
        self.assertIn(
            "Las referencias completas\n   se muestran por separado en la interfaz.",
            BASE_SYSTEM_INSTRUCTIONS,
        )

    def test_base_prompt_contains_one_instruction_block_and_both_contexts(self) -> None:
        prompt = build_base_prompt(
            "¿Qué debe hacer la empresa?",
            "[1] Evidencia normativa",
            "Empresa de riesgo I",
        )

        self.assertEqual(prompt.count("REGLAS:"), 1)
        self.assertIn("CONTEXTO EMPRESARIAL Y CONVERSACIONAL:", prompt)
        self.assertIn("CONTEXTO NORMATIVO RECUPERADO:", prompt)
        self.assertIn("PREGUNTA:", prompt)
        self.assertIn("Empresa de riesgo I", prompt)
        self.assertIn("[1] Evidencia normativa", prompt)


if __name__ == "__main__":
    unittest.main()
