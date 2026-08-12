"""Minimal LangGraph RAG flow for normative consultation."""

from collections.abc import Callable
from typing import Any, TypedDict

from agents.consulta_normativa.manual_implementation.config import DEFAULT_TOP_K
from agents.consulta_normativa.langchain_rag.chain import generate_answer, invoke_llm, insufficient_evidence_answer
from agents.consulta_normativa.langchain_rag.formatting import build_context, build_references, recovered_documents
from agents.consulta_normativa.langchain_rag.models import LangChainRagResult, RetrievedDocument
from agents.consulta_normativa.manual_implementation.prompts import build_base_prompt

Retriever = Callable[[str, int], dict[str, Any]]


class RagGraphState(TypedDict, total=False):
    """State passed through the minimal LangGraph RAG flow."""

    question: str
    documents: list[RetrievedDocument]
    context: str
    references: list[str]
    prompt: str
    answer: str
    result: LangChainRagResult


def build_langgraph_rag(llm: Any, retriever: Retriever, top_k: int = DEFAULT_TOP_K) -> Any:
    """Build the minimal LangGraph equivalent of the linear RAG pipeline."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)
    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("format_context", format_context_node)
    workflow.add_node("generate", generate_node(llm))
    workflow.add_node("format_result", format_result_node)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "format_context")
    workflow.add_edge("format_context", "generate")
    workflow.add_edge("generate", "format_result")
    workflow.add_edge("format_result", END)
    return workflow.compile()


def answer_with_langgraph(question: str, graph: Any) -> LangChainRagResult:
    """Run a compiled LangGraph-like object and return its RAG result."""

    state = graph.invoke({"question": question})
    result = state.get("result") if isinstance(state, dict) else None
    if not isinstance(result, LangChainRagResult):
        raise ValueError("LangGraph execution did not produce a LangChainRagResult.")
    return result


def answer_with_linear_graph(question: str, retriever: Retriever, llm: Any, top_k: int = DEFAULT_TOP_K) -> LangChainRagResult:
    """Run the same node sequence without requiring LangGraph."""

    state: RagGraphState = {"question": question}
    state.update(retrieve_node(retriever, top_k)(state))
    state.update(format_context_node(state))
    state.update(generate_node(llm)(state))
    state.update(format_result_node(state))
    return state["result"]


def retrieve_node(retriever: Retriever, top_k: int) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that retrieves and normalizes documents."""

    def run(state: RagGraphState) -> RagGraphState:
        return {"documents": recovered_documents(retriever(state["question"], top_k))}

    return run



def format_context_node(state: RagGraphState) -> RagGraphState:
    """Build context, references, and prompt from retrieved documents."""

    documents = state.get("documents", [])
    context = build_context(documents)
    return {
        "context": context,
        "references": build_references(documents),
        "prompt": build_base_prompt(state["question"], context),
    }


def generate_node(llm: Any) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that invokes the LLM when evidence exists."""

    def run(state: RagGraphState) -> RagGraphState:
        documents = state.get("documents", [])
        answer = invoke_llm(llm, state["prompt"]) if documents else insufficient_evidence_answer()
        return {"answer": answer}

    return run



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
