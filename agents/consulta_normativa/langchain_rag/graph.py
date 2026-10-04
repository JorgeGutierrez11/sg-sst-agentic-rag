"""LangGraph RAG flow for normative consultation."""

import json
import logging
from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.config import DEFAULT_TOP_K
from agents.consulta_normativa.langchain_rag.core.instrumentation import record_retrieval_trace_node
from agents.consulta_normativa.langchain_rag.core.llm import invoke_llm_text
from agents.consulta_normativa.langchain_rag.core.routes import evidence_route
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.formatting import build_context, build_references, recovered_documents
from agents.consulta_normativa.langchain_rag.models import LangChainRagResult, RetrievedDocument
from agents.consulta_normativa.langchain_rag.prompts import (
    BASE_SYSTEM_INSTRUCTIONS,
    FALLBACK_PROMPT,
    build_base_prompt,
    build_fallback_diagnostic_message,
    build_human_prompt,
)

# importar nodo de perfil de negocio y nodo de historial de conversación
from agents.consulta_normativa.langchain_rag.business_context.profile_node import (business_profile_node)
from agents.consulta_normativa.langchain_rag.business_context.history_node import (save_conversation_turn_node)

# Query_understanding - query expansion
from agents.consulta_normativa.langchain_rag.query_understanding.query_expansion import (query_expansion_node)
# retrieval - R3
from agents.consulta_normativa.langchain_rag.retrieval.reranking import rerank_node
from agents.consulta_normativa.langchain_rag.retrieval.parent_document_retrieval import (expand_parent_documents)
from agents.consulta_normativa.langchain_rag.retrieval.table_complement import complement_linked_tables_node
# business_context - long-term memory
from agents.consulta_normativa.langchain_rag.business_context.techniques.retrieval_long_term_memory import (retrieval_long_term_memory_node,store_latest_conversation_memory_node)
# validation - relevance grading
from agents.consulta_normativa.langchain_rag.validation.retrieval_relevance_grading import (retrieval_relevance_grading_node)

Retriever = Callable[[str, int], dict[str, Any]]
logger = logging.getLogger(__name__)

DETERMINISTIC_NO_EVIDENCE_ANSWER = "La evidencia recuperada es insuficiente para responder la pregunta."

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
    reranker_batch_size: int = 32,
    reranker_device: str = "cpu",
    reranker_input_max_length: int = 512,
    parent_lookup: dict[str, Any] | None = None,
    first_table_parts: dict[str, RetrievedDocument] | None = None,
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
            batch_size=reranker_batch_size,
            device=reranker_device,
            input_max_length=reranker_input_max_length,
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
    workflow.add_node(
        "complement_linked_tables",
        complement_linked_tables_node(first_table_parts or {}),
    )

    workflow.add_node("record_retrieval_trace",record_retrieval_trace_node)


    workflow.add_node("fallback_answer", fallback_answer_node(llm))
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



    workflow.add_edge(
        "retrieval_relevance_grading",
        "complement_linked_tables",
    )
    workflow.add_conditional_edges(
        "complement_linked_tables",
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


def fallback_answer_node(llm: Any) -> Callable[[RagGraphState], RagGraphState]:
    """Build a node that explains missing evidence with the configured LLM."""

    def run(state: RagGraphState) -> RagGraphState:
        context = "No se recuperó contexto."
        prompt = ""

        try:
            diagnostic_message = build_fallback_diagnostic_prompt(state)
            prompt = f"{FALLBACK_PROMPT}\n\n{diagnostic_message}"
            # pyrefly: ignore [missing-import]
            from langchain_core.messages import HumanMessage, SystemMessage

            answer = invoke_llm_text(
                llm,
                [
                    SystemMessage(content=FALLBACK_PROMPT),
                    HumanMessage(content=diagnostic_message),
                ],
            )
        except Exception as error:
            logger.error(
                "Fallback LLM generation failed; returning deterministic response | error=%s",
                type(error).__name__,
            )
            if not prompt:
                prompt = build_base_prompt(state.get("question", ""), context)
            answer = fallback_answer(context, [])

        return {
            "context": context,
            "references": [],
            "prompt": prompt,
            "answer": answer,
        }

    return run


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


def build_fallback_diagnostic_prompt(state: RagGraphState) -> str:
    """Build the untrusted fallback diagnostics message from allowed state fields."""

    trace = state.get("relevance_grading_trace", {})
    trace = trace if isinstance(trace, dict) else {}

    documents = trace.get("documents", [])
    documents = documents if isinstance(documents, list) else []

    graded_documents = [
        {
            "index": document.get("index"),
            "relevant": document.get("relevant"),
            "reason": document.get("reason", ""),
            "fallback": document.get("fallback", False),
            "error": document.get("error"),
        }
        for document in documents
        if isinstance(document, dict)
    ]

    query_expansion_trace = state.get("query_expansion_trace", {})
    query_expansion_trace = query_expansion_trace if isinstance(query_expansion_trace, dict) else {}
    
    business_context = state.get("business_context", {})
    business_context = business_context if isinstance(business_context, dict) else {}
    
    return build_fallback_diagnostic_message(
        question=str(state.get("question", "")),
        relevant_count=str(trace.get("relevant_count", 0)),
        rejected_count=str(trace.get("rejected_count", 0)),
        rejection_reasons=json.dumps(
            [document["reason"] for document in graded_documents],
            ensure_ascii=False,
            default=str,
        ),
        graded_documents=json.dumps(
            graded_documents, 
            ensure_ascii=False, 
            default=str
        ),
        query_expansion_error=str(query_expansion_trace.get("error") or ""),
        business_context=str(business_context.get("current_context") or ""),
    )


def fallback_answer(context: str, references: list[str]) -> str:
    """Return the deterministic response used only when fallback generation fails."""

    if context == "No se recuperó contexto.":
        return DETERMINISTIC_NO_EVIDENCE_ANSWER
    return "\n".join(["Borrador fundamentado solo en el contexto recuperado:", context, "Referencias:", *references])


def format_result_node(state: RagGraphState) -> RagGraphState:
    """Build the public result object from graph state."""

    return {
        "result": LangChainRagResult(
            answer=state["answer"],
            references=state.get("references", []),
            context=state["context"],
            prompt=state["prompt"],
            chunks=[document.document for document in state.get("documents", [])],
        )
    }
