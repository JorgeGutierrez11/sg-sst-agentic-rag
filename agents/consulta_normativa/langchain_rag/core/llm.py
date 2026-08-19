"""LLM helpers for the LangGraph RAG flow."""

import os
from typing import Any

from agents.consulta_normativa.langchain_rag.config import DEFAULT_GROQ_MODEL, DEFAULT_TEMPERATURE


def build_groq_llm() -> Any:
    """Build the default Groq LangChain chat model lazily."""

    if not os.environ.get("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is not configured in the environment.")

    try:
        # pyrefly: ignore [missing-import]
        from langchain_groq import ChatGroq
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langchain_groq is not installed: {error}") from error

    return ChatGroq(model=DEFAULT_GROQ_MODEL, temperature=DEFAULT_TEMPERATURE)


def invoke_llm_text(llm: Any, messages: list[Any]) -> str:
    """Invoke a LangChain-like LLM and return the response text."""

    return extract_response_content(llm.invoke(messages))


def extract_response_content(response: Any) -> str:
    """Extract text from an AIMessage-like response, with message-list protection."""

    content = getattr(response, "content", None)
    if content is not None:
        return str(content)
    if isinstance(response, list):
        for message in reversed(response):
            message_content = getattr(message, "content", None)
            if message_content:
                return str(message_content)
    return str(response)
