"""Direct executable entrypoint for the experimental LangChain RAG variant."""

from __future__ import annotations
from uuid import uuid4 # nuevo import para generar un identificador único para cada hilo de conversación

import argparse
import sys
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from langchain_core.embeddings import Embeddings



from agents.consulta_normativa.langchain_rag.config import DEFAULT_CHROMA_PATH, DEFAULT_COLLECTION_NAME, HYBRID_CANDIDATE_TOP_K, HYBRID_RRF_K, RERANKER_MODEL_NAME, RERANKER_MAX_LENGTH, RERANKER_CANDIDATE_POOL_SIZE, RERANKER_FINAL_TOP_K, DEFAULT_PARENT_CHUNKS_PATH

logging.getLogger(
    "agents.consulta_normativa.langchain_rag.validation.retrieval_relevance_grading"
).setLevel(logging.WARNING)

OPERATIONAL_ERROR_CODE = 2

Retriever = Callable[[str, int], dict[str, Any]]


class OperationalError(Exception):
    """Controlled error for expected runtime setup and execution failures."""


@dataclass(frozen=True)
class RuntimeDependencies:
    """Lazy-loaded dependencies required by the executable RAG flow."""

    build_deepseek_llm: Callable[[], Any]
    #build_langgraph_rag: Callable[[Any, Retriever, int], Any]
    #answer_with_langgraph: Callable[[str, Any], Any]
    build_langgraph_rag: Callable[..., Any] # La firma anterior ya quedó obsoleta porque ahora ambas funciones aceptan parámetros adicionales.
    answer_with_langgraph: Callable[..., Any]
    open_existing_collection: Callable[[Any, str], Any]
    open_existing_bm25_index: Callable[..., Any]
    hybrid_retriever: Callable[..., Retriever]
    get_reranker: Callable[..., Any]
    load_parent_documents: Callable[..., Any]
    


@dataclass(frozen=True)
class RagRuntime:
    """Reusable runtime built once for direct or interactive execution."""

    #answer_with_langgraph: Callable[[str, Any], Any]
    answer_with_langgraph: Callable[..., Any]
    graph: Any
    thread_id: str

# nueva clase para adaptar los embeddings de Qwen a la memoria a largo plazo basada en recuperación
class QwenMemoryEmbeddings(Embeddings):
    """Qwen embeddings adapted for retrieval-based conversational memory."""

    def __init__(
        self,
        embedding_function: Any,
    ) -> None:
        # Reutilizamos el SentenceTransformer que Chroma ya cargó.
        self._model = embedding_function._model

        self._normalize_embeddings = (
            embedding_function.normalize_embeddings
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Embed stored conversation memories as documents."""

        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=self._normalize_embeddings,
        )

        return [
            vector.tolist()
            for vector in vectors
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        """Embed a memory-search query using Qwen's query prompt."""

        vector = self._model.encode(
            text,
            prompt_name="query",
            convert_to_numpy=True,
            normalize_embeddings=self._normalize_embeddings,
        )

        return vector.tolist()


def main(argv: list[str] | None = None) -> int:
    """Run the direct experimental LangChain RAG entrypoint."""

    parser = argparse.ArgumentParser(prog="python -m agents.consulta_normativa.langchain_rag.main")
    parser.add_argument("question", nargs="?", help="Optional question to answer once before exiting.")
    args = parser.parse_args(argv)

    try:
        runtime = build_runtime()
    except OperationalError as error:
        return fail("initialization", error)
    except Exception as error:  # noqa: BLE001 - CLI must never print traceback for operational setup failures.
        return fail("initialization", OperationalError(str(error)))

    if args.question:
        return run_once(runtime, args.question)
    return run_interactive_loop(runtime)


def build_runtime(write_graph_image: bool = True) -> RagRuntime:
    """Build the Chroma retriever and DeepSeek-backed LLM for the session.

    Args:
        write_graph_image: Whether to write the graph diagram used by the CLI.
    """

    dependencies = load_dependencies()

    try:
        llm = dependencies.build_deepseek_llm()
    except Exception as error:  # noqa: BLE001 - keep missing key/package/provider errors controlled.
        raise OperationalError(str(error)) from error

    try:
        from chromadb.utils.embedding_functions import (
            SentenceTransformerEmbeddingFunction,
        )
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.store.memory import InMemoryStore

        collection = dependencies.open_existing_collection(
            DEFAULT_CHROMA_PATH,
            DEFAULT_COLLECTION_NAME,
        )
        

        bm25_index = dependencies.open_existing_bm25_index()

        retriever = dependencies.hybrid_retriever(
            collection,
            bm25_index,
            candidate_top_k=HYBRID_CANDIDATE_TOP_K,
            rrf_k=HYBRID_RRF_K,
        )

        reranker = dependencies.get_reranker(
            RERANKER_MODEL_NAME,
            RERANKER_MAX_LENGTH,
        )

        parent_lookup = dependencies.load_parent_documents(
            DEFAULT_PARENT_CHUNKS_PATH
        )

        # Memoria de corto plazo asociada al thread.
        checkpointer = InMemorySaver()

        # Mismo modelo de embeddings utilizado por el RAG.
        memory_embedding_function = (
            SentenceTransformerEmbeddingFunction(
                model_name="Qwen/Qwen3-Embedding-0.6B",
                normalize_embeddings=True,
            )
        )

        memory_embeddings = QwenMemoryEmbeddings(
            memory_embedding_function
        )

        # Store independiente para Retrieval-Based
        # Long-Term Memory.
        memory_store = InMemoryStore(
            index={
                "dims": 1024,
                "embed": memory_embeddings,
                "fields": ["text"],
            }
        )

        graph = dependencies.build_langgraph_rag(
            llm,
            retriever,
            RERANKER_CANDIDATE_POOL_SIZE,
            checkpointer=checkpointer,
            store=memory_store,
            reranker=reranker,
            reranker_candidate_pool_size=RERANKER_CANDIDATE_POOL_SIZE,
            reranker_final_top_k=RERANKER_FINAL_TOP_K,
            parent_lookup=parent_lookup
        )

        if write_graph_image:
            png_bytes = graph.get_graph().draw_mermaid_png()

            with open(
                "data/images/base_rag_graph.png",
                "wb",
            ) as graph_image:
                graph_image.write(png_bytes)

            print(
                "Grafo guardado exitosamente "
                "como 'base_rag_graph.png'"
            )

    except Exception as error:
        raise OperationalError(
            str(error)
        ) from error
    
    thread_id = f"cli-session-{uuid4()}" # Generar un identificador único para cada hilo de conversación
    return RagRuntime(
        answer_with_langgraph=dependencies.answer_with_langgraph,
        graph=graph,
        thread_id=thread_id, # Agregar el identificador único al runtime para su uso en la conversación
    )


def load_dependencies() -> RuntimeDependencies:
    """Load optional runtime dependencies lazily so failures stay controlled."""

    try:
        from agents.consulta_normativa.langchain_rag.core.llm import build_deepseek_llm
        from agents.consulta_normativa.langchain_rag.graph import answer_with_langgraph, build_langgraph_rag
        from agents.consulta_normativa.langchain_rag.retrieval.chroma_retrieval import open_existing_collection
        from agents.consulta_normativa.langchain_rag.retrieval.bm25_retrieval import (open_existing_index as open_existing_bm25_index)
        from agents.consulta_normativa.langchain_rag.retrieval.hybrid_retrieval import (hybrid_retriever)
        from agents.consulta_normativa.langchain_rag.retrieval.reranking import (get_reranker)
        from agents.consulta_normativa.langchain_rag.retrieval.parent_document_retrieval import (load_parent_documents)
    except ModuleNotFoundError as error:
        raise OperationalError(f"Required runtime dependency is not installed: {error}") from error

    return RuntimeDependencies(
        build_deepseek_llm=build_deepseek_llm,
        build_langgraph_rag=build_langgraph_rag,
        answer_with_langgraph=answer_with_langgraph,
        open_existing_collection=open_existing_collection,
        open_existing_bm25_index=open_existing_bm25_index,
        hybrid_retriever=hybrid_retriever,
        get_reranker=get_reranker,
        load_parent_documents=load_parent_documents,
    )


def run_interactive_loop(runtime: RagRuntime) -> int:
    """Read questions until the user exits."""

    print("Experimental LangChain RAG ready. Type 'exit' or 'quit' to leave.")
    while True:
        try:
            question = input("Question> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            return 0

        run_once(runtime, question)


def run_once(runtime: RagRuntime, question: str) -> int:
    """Answer one question and keep expected failures controlled."""

    try:
        result = runtime.answer_with_langgraph(question, runtime.graph, thread_id=runtime.thread_id) # Pasar el thread_id al llamar a answer_with_langgraph
    except Exception as error:  # noqa: BLE001 - direct CLI should report RAG failures without traceback.
        return fail("RAG execution", OperationalError(str(error)))

    print_answer(result.answer, result.references)

    # DEBUG: mostrar current_context generado por la técnica
    snapshot = runtime.graph.get_state(
        {
            "configurable": {
                "thread_id": runtime.thread_id,
            }
        }
    )

    print("\n-------------------------- QUERY EXPANSION ---------------------------------------")
    print("Pregunta original:", snapshot.values.get("question"))
    print("Consulta usada para retrieval:", snapshot.values.get("retrieval_query"))
    print("Trace:", snapshot.values.get("query_expansion_trace"))
    print("-------------------------- END QUERY EXPANSION -----------------------------------\n")

    documents = snapshot.values.get(
        "documents",
        [],
    )

    reranking_trace = snapshot.values.get(
        "reranking_trace",
        {},
    )

    reranker_selected_count = reranking_trace.get(
        "selected_count",
        0,
    )

    expanded_parent_count = sum(
        1
        for document in documents
        if document.metadata.get("parent_expansion_applied")
    )

    missing_parent_fallback_count = sum(
        1
        for document in documents
        if document.metadata.get("parent_expansion_fallback") == "missing_parent"
    )

    deduplicated_count = sum(
        max(
            len(document.metadata.get("expanded_from_child_ids", [])) - 1,
            0,
        )
        for document in documents
    )

    relevance_trace = snapshot.values.get(
        "relevance_grading_trace",
        {},
    )

    print(
        "\n-------------------------- R3 HYBRID + RERANKING + PARENT ---------------------------------------"
    )

    print(
        f"Candidatos recibidos por reranker: "
        f"{reranking_trace.get('candidate_count', 0)}"
    )

    print(
        f"Documentos seleccionados por reranker: "
        f"{reranker_selected_count}"
    )

    print(
        f"Fallback reranker: "
        f"{reranking_trace.get('fallback', None)}"
    )

    print(
        f"Documentos entregados por R3 a Validation: "
        f"{relevance_trace.get('input_count', 0)}"
    )



    print(
        "-------------------------- END R3 HYBRID + RERANKING + PARENT -----------------------------------\n"
    )


    

    relevance_documents = relevance_trace.get(
        "documents",
        [],
    )

    final_documents = snapshot.values.get(
        "documents",
        [],
    )

    print(
        "\n-------------------------- RETRIEVAL RELEVANCE GRADING ---------------------------------------"
    )

    print(
        f"Documentos recibidos desde R3: "
        f"{relevance_trace.get('input_count', 0)}"
    )

    print(
        f"Marcados relevantes por el grader: "
        f"{relevance_trace.get('relevant_count', 0)}"
    )

    print(
        f"Marcados irrelevantes por el grader: "
        f"{relevance_trace.get('rejected_count', 0)}"
    )

    print(
        f"Conservados por fallback: "
        f"{relevance_trace.get('fallback_count', 0)}"
    )

    print(
        f"Documentos finales después de Validation: "
        f"{len(final_documents)}"
    )

    for document_trace in relevance_documents:
        relevant = document_trace.get("relevant", False)
        fallback = document_trace.get("fallback", False)

        if fallback:
            decision = "CONSERVADO POR FALLBACK"
        elif relevant:
            decision = "CONSERVADO"
        else:
            decision = "ELIMINADO"

        print(
            f"\nDocumento {document_trace.get('index', 0) + 1}"
        )
        print(
            f"Decisión: {decision}"
        )
        print(
            f"Fuente: {document_trace.get('source', '')}"
        )
        print(
            f"Artículo: {document_trace.get('article', '')}"
        )
        print(
            f"Chroma ID: {document_trace.get('chroma_id', '')}"
        )
        print(
            f"Razón: {document_trace.get('reason', '')}"
        )
        print(
            f"Fallback: {fallback}"
        )

        if document_trace.get("error"):
            print(
                f"Error: {document_trace.get('error')}"
            )

    print(
        "-------------------------- END RETRIEVAL RELEVANCE GRADING -----------------------------------\n"
    )

    business_context = snapshot.values.get(
        "business_context",
        {},
    )

    current_context = business_context.get(
        "current_context",
        "",
    )
    


    print("\n-------------------------- CURRENT BUSINESS CONTEXT ---------------------------------------")
    print(current_context or "[vacío]")
    print("-------------------------- END CURRENT BUSINESS CONTEXT ---------------------------------------\n")



    return 0


def print_answer(answer: str, references: list[str]) -> None:
    """Print the answer and its source references."""

    print("Answer:")
    print(answer)
    if references:
        print()
        print("References:")
        for reference in references:
            print(f"- {reference}")


def fail(stage: str, error: Exception) -> int:
    """Print one controlled operational error and return the CLI error code."""

    print(f"Error during {stage}:", file=sys.stderr)
    print(str(error), file=sys.stderr)
    return OPERATIONAL_ERROR_CODE


if __name__ == "__main__":
    raise SystemExit(main())
