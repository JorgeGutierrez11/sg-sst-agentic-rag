"""LangChain-style linear RAG pipeline for normative consultation."""

import os
from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.manual_implementation.config import DEFAULT_GROQ_MODEL, DEFAULT_TEMPERATURE, DEFAULT_TOP_K
from agents.consulta_normativa.langchain_rag.formatting import build_context, build_references, recovered_documents
from agents.consulta_normativa.langchain_rag.models import LangChainRagResult, RetrievedDocument
from agents.consulta_normativa.manual_implementation.prompts import build_base_prompt

Retriever = Callable[[str, int], dict[str, Any]]


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


def build_langchain_rag_chain(retriever: Retriever, llm: Any, top_k: int = DEFAULT_TOP_K) -> Callable[[str], LangChainRagResult]:
    """Build a callable linear RAG chain from injectable retrieval and LLM boundaries."""

    def run(question: str) -> LangChainRagResult:
        return answer_with_langchain(question, retriever, llm, top_k=top_k)

    return run


def answer_with_langchain(
    question: str,
    retriever: Retriever,
    llm: Any,
    top_k: int = DEFAULT_TOP_K,
) -> LangChainRagResult:
    """Retrieve context, invoke an LLM-like object, and return a grounded RAG result."""

    documents = recovered_documents(retriever(question, top_k))
    context = build_context(documents)
    references = build_references(documents)
    prompt = build_base_prompt(question, context)
    answer = invoke_llm(llm, prompt) if documents else insufficient_evidence_answer()
    return LangChainRagResult(answer=answer, references=references, context=context, prompt=prompt)


def generate_answer(question: str, documents: list[RetrievedDocument], llm: Any) -> LangChainRagResult:
    """Generate an answer from already retrieved documents."""

    context = build_context(documents)
    references = build_references(documents)
    prompt = build_base_prompt(question, context)
    answer = invoke_llm(llm, prompt) if documents else insufficient_evidence_answer()
    return LangChainRagResult(answer=answer, references=references, context=context, prompt=prompt)


def invoke_llm(llm: Any, prompt: str) -> str:
    """Invoke a LangChain-like model or simple callable and return text content."""

    response = llm.invoke(prompt) if hasattr(llm, "invoke") else llm(prompt)
    return str(getattr(response, "content", response))


def insufficient_evidence_answer() -> str:
    """Return the deterministic answer used when retrieval returns no documents."""

    return "La evidencia recuperada es insuficiente para responder la pregunta."
