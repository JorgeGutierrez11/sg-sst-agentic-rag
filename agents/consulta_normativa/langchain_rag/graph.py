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

# importar nodo de perfil de negocio y nodo de historial de conversación
from agents.consulta_normativa.langchain_rag.business_context.profile_node import (business_profile_node)
from agents.consulta_normativa.langchain_rag.business_context.history_node import (save_conversation_turn_node)

# Query_understanding - query expansion
from agents.consulta_normativa.langchain_rag.query_understanding.query_expansion import (query_expansion_node)
# retrieval - R3
from agents.consulta_normativa.langchain_rag.retrieval.reranking import rerank_node
from agents.consulta_normativa.langchain_rag.retrieval.parent_document_retrieval import (expand_parent_documents)
# business_context - long-term memory
from agents.consulta_normativa.langchain_rag.business_context.techniques.retrieval_long_term_memory import (retrieval_long_term_memory_node,store_latest_conversation_memory_node)
# validation - relevance grading
from agents.consulta_normativa.langchain_rag.validation.retrieval_relevance_grading import (retrieval_relevance_grading_node)

Retriever = Callable[[str, int], dict[str, Any]]

# se agregó checkpointer: Any | None = None, para permitir la integración con un sistema de checkpointing y store: Any | None = None, para permitir la integración con un sistema de almacenamiento de memoria a largo plazo.
def build_langgraph_rag(
    llm: Any,
    retriever: Retriever,
    top_k: int = DEFAULT_TOP_K,
    checkpointer: Any | None = None,
    store: Any | None = None,
    reranker: Any | None = None,
    reranker_candidate_pool_size: int = 40,
    reranker_final_top_k: int = DEFAULT_TOP_K,
    parent_lookup: dict[str, Any] | None = None,
) -> Any:
    """Build the LangGraph RAG pipeline with explicit evidence branching."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)


    workflow.add_node("business_profile", business_profile_node(llm)) # Agregar nodo de perfil de negocio
    workflow.add_node("retrieval_long_term_memory",retrieval_long_term_memory_node()) # Agregar node de long-term memory
    workflow.add_node("save_conversation_turn",save_conversation_turn_node)
    workflow.add_node("store_long_term_memory",store_latest_conversation_memory_node)
    workflow.add_node("expand_query",query_expansion_node(llm)) # Agrega nodo de query expansion
    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)

    workflow.add_node(
        "rerank",
        rerank_node(
            reranker,
            reranker_candidate_pool_size,
            reranker_final_top_k,
        ),
    )

    workflow.add_node(
        "expand_parent_documents",
        expand_parent_documents_node(parent_lookup or {}),
    )
    # Validation - Retrieval Relevance Grading
    workflow.add_node(
        "retrieval_relevance_grading",
        retrieval_relevance_grading_node(llm),
    )

    workflow.add_node("record_retrieval_trace",record_retrieval_trace_node)


    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)




    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))


    #workflow.add_node("save_conversation_turn", save_conversation_turn_node) # Agregar nodo de historial de conversación

    

    workflow.add_node("format_result", format_result_node)

    # Construccion del grafo
    workflow.set_entry_point("business_profile")

    workflow.add_edge("business_profile","retrieval_long_term_memory")
    workflow.add_edge("retrieval_long_term_memory","expand_query")
    workflow.add_edge("expand_query", "retrieve")
    workflow.add_edge("retrieve", "normalize_documents")
    workflow.add_edge("normalize_documents", "rerank")
    workflow.add_edge("rerank", "expand_parent_documents")
    workflow.add_edge(
        "expand_parent_documents",
        "record_retrieval_trace",
    )
    workflow.add_edge(
        "record_retrieval_trace",
        "retrieval_relevance_grading",
    )



    workflow.add_conditional_edges(
        "retrieval_relevance_grading",
        evidence_route,
        {"with_evidence": "format_context", "without_evidence": "fallback_answer"},)



    workflow.add_edge("format_context", "build_messages")
    workflow.add_edge("build_messages", "generate_answer")
    workflow.add_edge("fallback_answer","save_conversation_turn")
    workflow.add_edge("generate_answer","save_conversation_turn")
    workflow.add_edge("save_conversation_turn","store_long_term_memory")
    workflow.add_edge("store_long_term_memory","format_result")

    

    workflow.add_edge("format_result", END)
    return workflow.compile(checkpointer=checkpointer,store=store,) #se agregó checkpointer=checkpointer, y store=store, para permitir la integración con un sistema de checkpointing y almacenamiento de memoria a largo plazo.

def expand_parent_documents_node(
    parent_lookup: dict[str, Any],
) -> Callable[[RagGraphState], RagGraphState]:
    """Expand reranked child chunks to their parent documents."""

    def run(state: RagGraphState) -> RagGraphState:
        documents = state.get("documents", [])

        return {
            "documents": expand_parent_documents(
                documents,
                parent_lookup,
            )
        }

    return run


# se agregó thread_id: str | None = None,
def answer_with_langgraph(question: str, graph: Any, thread_id: str | None = None,) -> LangChainRagResult:
    """Run a compiled LangGraph-like object and return its RAG result."""

    if thread_id is None:
        state = graph.invoke({"question": question}) # si no hay un thread_id, se invoca el grafo sin configuración adicional
    else:
        state = graph.invoke({"question": question},{"configurable": {"thread_id": thread_id,}},) #se agrea por si hay un thread_id, se pasa como parte de la configuración del grafo

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
    """Build messages with separated normative and business context."""

    try:
        # pyrefly: ignore [missing-import]
        from langchain_core.messages import HumanMessage, SystemMessage
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langchain is not installed: {error}") from error

    # Evidencia normativa recuperada por R3.
    normative_context = state["context"]

    # Contexto empresarial y conversacional.
    business_context = state.get("business_context", {})
    current_context = business_context.get("current_context", "")

    return {
        "messages": [
            SystemMessage(content=BASE_SYSTEM_INSTRUCTIONS),
            HumanMessage(
                content=build_human_prompt(
                    state["question"],
                    normative_context,
                    current_context,
                )
            ),
        ],
        "prompt": build_base_prompt(
            state["question"],
            normative_context,
            current_context,
        ),
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
