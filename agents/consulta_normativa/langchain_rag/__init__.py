"""Experimental LangChain/LangGraph RAG pipeline for normative consultation."""

__all__ = [
    "LangChainRagResult",
    "RetrievedDocument",
    "answer_with_langgraph",
    "build_deepseek_llm",
    "build_groq_llm",
    "build_langgraph_rag",
]


def __getattr__(name: str) -> object:
    """Load public LangChain RAG exports lazily so subpackage imports stay lightweight."""

    if name == "build_deepseek_llm":
        from agents.consulta_normativa.langchain_rag.core.llm import build_deepseek_llm

        return build_deepseek_llm
    if name == "build_groq_llm":
        from agents.consulta_normativa.langchain_rag.core.llm import build_groq_llm

        return build_groq_llm
    if name in {"answer_with_langgraph", "build_langgraph_rag"}:
        from agents.consulta_normativa.langchain_rag.graph import answer_with_langgraph, build_langgraph_rag

        return {"answer_with_langgraph": answer_with_langgraph, "build_langgraph_rag": build_langgraph_rag}[name]
    if name in {"LangChainRagResult", "RetrievedDocument"}:
        from agents.consulta_normativa.langchain_rag.models import LangChainRagResult, RetrievedDocument

        return {"LangChainRagResult": LangChainRagResult, "RetrievedDocument": RetrievedDocument}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
