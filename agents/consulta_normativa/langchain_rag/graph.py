"""LangGraph RAG flow for normative consultation."""

from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.config import (
    DEFAULT_TOP_K,
    MULTI_QUERY_MAX_VARIANTS,
    MULTI_QUERY_TOP_K_PER_VARIANT,
    MULTIQUERY_RRF_TOP_K,
    RRF_K,
)
from agents.consulta_normativa.langchain_rag.core.instrumentation import record_retrieval_trace_node
from agents.consulta_normativa.langchain_rag.core.llm import invoke_llm_text
from agents.consulta_normativa.langchain_rag.core.routes import evidence_route
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.formatting import build_context, build_references, recovered_documents
from agents.consulta_normativa.langchain_rag.models import LangChainRagResult
from agents.consulta_normativa.langchain_rag.prompts import BASE_SYSTEM_INSTRUCTIONS, build_base_prompt, build_human_prompt
from agents.consulta_normativa.langchain_rag.query_understanding.multi_query import generate_query_variants_node
from agents.consulta_normativa.langchain_rag.query_understanding.rewrite_query import rewrite_query_node
from agents.consulta_normativa.langchain_rag.retrieval.fusion import (
    fanout_retrieve_variants,
    retrieve_variant_node,
    rrf_fuse_node,
)

Retriever = Callable[[str, int], dict[str, Any]]


def build_langgraph_rag(llm: Any, retriever: Retriever, top_k: int = DEFAULT_TOP_K) -> Any:
    """Build the LangGraph RAG pipeline with explicit evidence branching."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)
    
    # Rewrite Quety Node
    workflow.add_node("rewrite_query", rewrite_query_node(llm))

    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)
    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)
    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)
    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))
    workflow.add_node("format_result", format_result_node)

    # Construccion del grafo
    workflow.set_entry_point("rewrite_query")
    workflow.add_edge("rewrite_query", "retrieve")

    workflow.add_edge("retrieve", "normalize_documents")
    workflow.add_edge("normalize_documents", "record_retrieval_trace")
    workflow.add_conditional_edges(
        "record_retrieval_trace",
        evidence_route,
        {"with_evidence": "format_context", "without_evidence": "fallback_answer"},
    )
    workflow.add_edge("fallback_answer", "format_result")
    workflow.add_edge("format_context", "build_messages")
    workflow.add_edge("build_messages", "generate_answer")
    workflow.add_edge("generate_answer", "format_result")
    workflow.add_edge("format_result", END)
    return workflow.compile()


def build_langgraph_rag_multiquery_rrf(
    llm: Any,
    retriever: Retriever,
    top_k: int = MULTIQUERY_RRF_TOP_K,
    # Multi-Query parameters.
    max_variants: int = MULTI_QUERY_MAX_VARIANTS,
    top_k_per_variant: int = MULTI_QUERY_TOP_K_PER_VARIANT,
    # RRF parameters.
    rrf_k: int = RRF_K,
) -> Any:
    """Build the experimental Multi-Query + RRF LangGraph RAG pipeline."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)

    # Multi-Query implementation.
    workflow.add_node("generate_query_variants", generate_query_variants_node(llm, max_variants))
    workflow.add_node("retrieve_variant", retrieve_variant_node(retriever, top_k_per_variant))
    workflow.add_node("rrf_fuse", rrf_fuse_node(rrf_k, top_k))

    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)
    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)
    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))
    workflow.add_node("format_result", format_result_node)

    workflow.set_entry_point("generate_query_variants")
    workflow.add_conditional_edges("generate_query_variants", fanout_retrieve_variants, ["retrieve_variant"])
    workflow.add_edge("retrieve_variant", "rrf_fuse")
    workflow.add_edge("rrf_fuse", "record_retrieval_trace")
    workflow.add_conditional_edges(
        "record_retrieval_trace",
        evidence_route,
        {"with_evidence": "format_context", "without_evidence": "fallback_answer"},
    )
    workflow.add_edge("fallback_answer", "format_result")
    workflow.add_edge("format_context", "build_messages")
    workflow.add_edge("build_messages", "generate_answer")
    workflow.add_edge("generate_answer", "format_result")
    workflow.add_edge("format_result", END)
    return workflow.compile()


def answer_with_langgraph(question: str, graph: Any) -> LangChainRagResult:
    """Run a compiled LangGraph-like object and return its RAG result."""

    state = graph.invoke({"question": question})

    print("***********************************")
    print("Retrieval query:")
    print(state.get("query_variants"))
    print("***********************************")

    result = state.get("result") if isinstance(state, dict) else None
    if not isinstance(result, LangChainRagResult):
        raise ValueError("LangGraph execution did not produce a LangChainRagResult.")
    return result

# Estos son unificables
def retrieve_node(retriever: Retriever, top_k: int) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that retrieves raw Chroma-like results."""

    def run(state: RagGraphState) -> RagGraphState:
        retrieval_query = state.get("retrieval_query") or state["question"]
        return {"raw_results": retriever(retrieval_query, top_k)}

    return run

# Me puedo unir con el anterior
def normalize_documents_node(state: RagGraphState) -> RagGraphState:
    """Normalize raw retrieval output into retrieved documents."""

    return {"documents": recovered_documents(state.get("raw_results", {}))}


def fallback_answer_node(state: RagGraphState) -> RagGraphState:
    """Return the deterministic manual fallback without invoking the LLM."""
    context = "No se recuperó contexto."

    return {
        "context": context,
        "references": [],
        "prompt": build_base_prompt(state["question"], context),
        "answer": fallback_answer(context, []),
    }


def format_context_node(state: RagGraphState) -> RagGraphState:
    """Build context and references from retrieved documents."""

    documents = state.get("documents", [])
    return {
        "context": build_context(documents),
        "references": build_references(documents),
    }


def build_messages_node(state: RagGraphState) -> RagGraphState:
    """Build LangChain chat messages equivalent to the manual prompt input."""

    try:
        # pyrefly: ignore [missing-import]
        from langchain_core.messages import HumanMessage, SystemMessage
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langchain is not installed: {error}") from error

    context = state["context"]
    return {
        "messages": [
            SystemMessage(content=BASE_SYSTEM_INSTRUCTIONS),
            HumanMessage(content=build_human_prompt(state["question"], context)),
        ],
        "prompt": build_base_prompt(state["question"], context),
    }


def generate_answer_node(llm: Any) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that invokes the LLM with LangChain messages."""

    def run(state: RagGraphState) -> RagGraphState:
        return {"answer": invoke_llm_text(llm, state["messages"])}

    return run


def fallback_answer(context: str, references: list[str]) -> str:
    """Replicate the manual deterministic fallback answer exactly."""

    if context == "No se recuperó contexto.":
        return "La evidencia recuperada es insuficiente para responder la pregunta."
    return "\n".join(["Borrador fundamentado solo en el contexto recuperado:", context, "Referencias:", *references])


def format_result_node(state: RagGraphState) -> RagGraphState:
    """Build the public result object from graph state."""

    return {
        "result": LangChainRagResult(
            answer=state["answer"],
            references=state.get("references", []),
            context=state["context"],
            prompt=state["prompt"],
        )
    }
