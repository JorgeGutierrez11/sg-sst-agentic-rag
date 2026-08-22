"""LangGraph RAG flow for normative consultation."""

from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.config import DEFAULT_TOP_K
from agents.consulta_normativa.langchain_rag.core.instrumentation import record_retrieval_trace_node
from agents.consulta_normativa.langchain_rag.core.llm import invoke_llm_text
from agents.consulta_normativa.langchain_rag.core.routes import evidence_route
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.formatting import build_context, build_references, recovered_documents
from agents.consulta_normativa.langchain_rag.models import LangChainRagResult
from agents.consulta_normativa.langchain_rag.prompts import BASE_SYSTEM_INSTRUCTIONS, build_base_prompt, build_human_prompt
from agents.consulta_normativa.langchain_rag.query_understanding.rewrite_query import rewrite_query_node

# ************ NELSON: SUFFICIENT-CONTEXT GATE
from agents.consulta_normativa.langchain_rag.core.routes import (sufficient_context_route)
from agents.consulta_normativa.langchain_rag.validation.sufficient_context_gate import (sufficient_context_gate_node)



Retriever = Callable[[str, int], dict[str, Any]]


def build_langgraph_rag(llm: Any, retriever: Retriever, top_k: int = DEFAULT_TOP_K) -> Any:
    """Build the LangGraph RAG pipeline with explicit evidence branching."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)
    


    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)
    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)

    
    

    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)

    # ************ NELSON: SUFFICIENT-CONTEXT GATE
    workflow.add_node("assess_sufficient_context",sufficient_context_gate_node(llm))

    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))
    workflow.add_node("format_result", format_result_node)

    # Construccion del grafo
    workflow.set_entry_point("retrieve")
    
    workflow.add_edge("retrieve", "normalize_documents")
    workflow.add_edge("normalize_documents", "record_retrieval_trace")

    
    workflow.add_conditional_edges(
        "record_retrieval_trace",
        evidence_route,
        {"with_evidence": "format_context", "without_evidence": "fallback_answer"},)
    
    workflow.add_edge("fallback_answer", "format_result")
    #workflow.add_edge("format_context", "build_messages")

    # ************ NELSON: SUFFICIENT-CONTEXT GATE
    workflow.add_edge(
        "format_context",
        "assess_sufficient_context",
    )

    workflow.add_conditional_edges(
        "assess_sufficient_context",
        sufficient_context_route,
        {
            "answerable": "build_messages",
            "insufficient": "fallback_answer",
        },
    )


    workflow.add_edge("build_messages", "generate_answer")
    workflow.add_edge("generate_answer", "format_result")
    workflow.add_edge("format_result", END)
    return workflow.compile()


def answer_with_langgraph(question: str, graph: Any) -> LangChainRagResult:
    """Run a compiled LangGraph-like object and return its RAG result."""

    state = graph.invoke({"question": question})
    result = state.get("result") if isinstance(state, dict) else None
    if not isinstance(result, LangChainRagResult):
        raise ValueError("LangGraph execution did not produce a LangChainRagResult.")
    return result


def retrieve_node(retriever: Retriever, top_k: int) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that retrieves raw Chroma-like results."""

    def run(state: RagGraphState) -> RagGraphState:
        retrieval_query = state.get("retrieval_query") or state["question"]
        return {"raw_results": retriever(retrieval_query, top_k)}

    return run


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
