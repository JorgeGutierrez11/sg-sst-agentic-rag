"""Prompt helpers for the base normative consultation RAG agent."""


BASE_SYSTEM_INSTRUCTIONS = """You are an SG-SST normative consultation assistant.
Answer only with the recovered context provided below.
If the context is insufficient, say that the recovered evidence is insufficient.
Do not add legal sources, obligations, or recommendations that are not supported by the context.
Include concise references to the recovered sources."""


def build_base_prompt(question: str, context: str) -> str:
    """Build the base grounded-answer prompt."""

    return f"""{BASE_SYSTEM_INSTRUCTIONS}

    Recovered context:
    {context}

    Question:
    {question}

    Grounded answer:"""
