"""Direct executable entrypoint for the experimental LangChain RAG variant."""

from __future__ import annotations
from uuid import uuid4 # nuevo import para generar un identificador único para cada hilo de conversación

import argparse
import sys
import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from langchain_core.embeddings import Embeddings

from agents.consulta_normativa.langchain_rag.config import (
    DEFAULT_CHROMA_PATH,
    DEFAULT_COLLECTION_NAME,
    DEFAULT_PARENT_CHUNKS_PATH,
    HYBRID_RRF_K,
    HYBRID_RRF_OUTPUT_TOP_K,
    HYBRID_SOURCE_CANDIDATE_TOP_K,
    RERANKER_BATCH_SIZE,
    RERANKER_CANDIDATE_POOL_SIZE,
    RERANKER_DEVICE,
    RERANKER_FINAL_TOP_K,
    RERANKER_MAX_LENGTH,
    RERANKER_MODEL_NAME,
    RERANKER_MODEL_REVISION,
    get_chroma_working_root,
)
from agents.consulta_normativa.langchain_rag.retrieval.bm25_retrieval import (
    DEFAULT_BM25_PATH,
)
from agents.consulta_normativa.langchain_rag.retrieval.table_complement import (
    DEFAULT_TABLE_DOCUMENTS_PATH,
)

logging.getLogger(
    "agents.consulta_normativa.langchain_rag.validation.retrieval_relevance_grading"
).setLevel(logging.WARNING)

OPERATIONAL_ERROR_CODE = 2

Retriever = Callable[[str, int], dict[str, Any]]


class OperationalError(Exception):
    """Controlled error for expected runtime setup and execution failures."""


@dataclass(frozen=True)
class RuntimeArtifact:
    """Local file the runtime needs before opening indexes or loading models."""

    label: str
    path: Path
    allow_empty: bool = False


# Archivos que bm25s lee al cargar el índice; si falta corpus.jsonl lo omite sin avisar.
BM25_INDEX_FILES = (
    "params.index.json",
    "vocab.index.json",
    "data.csc.index.npy",
    "indices.csc.index.npy",
    "indptr.csc.index.npy",
    "corpus.jsonl",
)

RUNTIME_ARTIFACTS: tuple[RuntimeArtifact, ...] = (
    RuntimeArtifact("Chroma database", DEFAULT_CHROMA_PATH / "chroma.sqlite3"),
    *(RuntimeArtifact(f"BM25 index file {name}", DEFAULT_BM25_PATH / name) for name in BM25_INDEX_FILES),
    RuntimeArtifact("parent chunks", DEFAULT_PARENT_CHUNKS_PATH),
    # Puede estar vacío si el corpus no tiene tablas.
    RuntimeArtifact("table documents", DEFAULT_TABLE_DOCUMENTS_PATH, allow_empty=True),
)


def validate_runtime_artifacts(artifacts: Iterable[RuntimeArtifact] = RUNTIME_ARTIFACTS) -> None:
    """Fail with every missing or empty artifact before Chroma can create files."""

    problems: list[str] = []
    for artifact in artifacts:
        if not artifact.path.is_file():
            problems.append(f"Missing runtime artifact: {artifact.label} ({artifact.path})")
        elif not artifact.allow_empty and artifact.path.stat().st_size == 0:
            problems.append(f"Empty runtime artifact: {artifact.label} ({artifact.path})")

    if problems:
        raise OperationalError("; ".join(problems))


# Máximo de IDs de ejemplo por problema en el mensaje de error
INDEX_MISMATCH_SAMPLE_SIZE = 5


def validate_index_consistency(collection: Any, bm25_index: Any, parent_lookup: Mapping[str, Any]) -> None:
    """Fail when Chroma, BM25, and parent chunks come from different corpus builds."""

    from agents.consulta_normativa.langchain_rag.retrieval.parent_document_retrieval import (
        parent_child_consistency_report,
    )

    corpus = list(getattr(bm25_index, "corpus", None) or [])
    problems: list[str] = []

    chroma_count = collection.count()
    if chroma_count != len(corpus):
        problems.append(
            f"Index record count mismatch: Chroma has {chroma_count} records, BM25 has {len(corpus)}"
        )

    chroma_ids = {str(record_id) for record_id in collection.get(include=[])["ids"]}
    bm25_ids = {str(record["id"]) for record in corpus}
    if chroma_ids != bm25_ids:
        problems.append(
            "Index ID mismatch: "
            f"{describe_ids(chroma_ids - bm25_ids, 'Chroma')}; "
            f"{describe_ids(bm25_ids - chroma_ids, 'BM25')}"
        )

    # parent_id está en metadata; las tablas no tienen padre
    report = parent_child_consistency_report(
        [dict(record.get("metadata") or {}) for record in corpus],
        dict(parent_lookup),
    )
    if report.children_with_missing_parent:
        problems.append(
            f"Missing parent chunks: {report.children_with_missing_parent} of "
            f"{report.children_with_parent_id} child chunks reference a parent not found in parent chunks"
        )

    if problems:
        raise OperationalError("; ".join(problems))


def describe_ids(ids: set[str], index_name: str) -> str:
    """Return the ID count plus a short sorted sample for error messages."""

    description = f"{len(ids)} only in {index_name}"
    if not ids:
        return description
    sample = sorted(ids)[:INDEX_MISMATCH_SAMPLE_SIZE]
    if len(ids) > INDEX_MISMATCH_SAMPLE_SIZE:
        sample.append("...")
    return f"{description} ({', '.join(sample)})"


@dataclass(frozen=True)
class RuntimeDependencies:
    """Lazy-loaded dependencies required by the executable RAG flow."""

    validate_runtime_artifacts: Callable[[], None]
    build_deepseek_llm: Callable[[], Any]
    #build_langgraph_rag: Callable[[Any, Retriever, int], Any]
    #answer_with_langgraph: Callable[[str, Any], Any]
    build_langgraph_rag: Callable[..., Any] # La firma anterior ya quedó obsoleta porque ahora ambas funciones aceptan parámetros adicionales.
    answer_with_langgraph: Callable[..., Any]
    open_existing_collection: Callable[[Any, str, Any], Any]
    open_existing_bm25_index: Callable[..., Any]
    hybrid_retriever: Callable[..., Retriever]
    get_reranker: Callable[..., Any]
    load_parent_documents: Callable[..., Any]
    load_first_table_parts: Callable[..., Any]
    create_chroma_working_copy: Callable[[Path, Path | None], Any]
    validate_index_consistency: Callable[[Any, Any, Mapping[str, Any]], None]
    build_embedding_function: Callable[[], Any]
    


@dataclass(frozen=True)
class RagRuntime:
    """Reusable runtime built once for direct or interactive execution."""

    #answer_with_langgraph: Callable[[str, Any], Any]
    answer_with_langgraph: Callable[..., Any]
    graph: Any
    thread_id: str
    # Mantiene viva la copia de Chroma que consulta el grafo; se borra al salir.
    chroma_working_copy: Any = None

# nueva clase para adaptar los embeddings de Qwen a la memoria a largo plazo basada en recuperación
class QwenMemoryEmbeddings(Embeddings):
    """Qwen embeddings adapted for retrieval-based conversational memory."""

    def __init__(
        self,
        embedding_function: Any,
        normalize_embeddings: bool = True,
    ) -> None:
        # Modelo compartido con la función de embeddings de Chroma
        self._model = embedding_function._model

        # Normalización propia de la memoria, independiente de Chroma
        self._normalize_embeddings = normalize_embeddings

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
    dependencies.validate_runtime_artifacts()

    try:
        llm = dependencies.build_deepseek_llm()
    except Exception as error:  # noqa: BLE001 - keep missing key/package/provider errors controlled.
        raise OperationalError(f"{type(error).__name__}: {error}") from error

    try:
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.store.memory import InMemoryStore

        chroma_working_copy = dependencies.create_chroma_working_copy(
            DEFAULT_CHROMA_PATH,
            get_chroma_working_root(),
        )
        # Instancia única de Qwen compartida por Chroma y la memoria
        embedding_function = dependencies.build_embedding_function()
        collection = dependencies.open_existing_collection(
            chroma_working_copy.path,
            DEFAULT_COLLECTION_NAME,
            embedding_function,
        )

        bm25_index = dependencies.open_existing_bm25_index()

        parent_lookup = dependencies.load_parent_documents(
            DEFAULT_PARENT_CHUNKS_PATH
        )

        # Valida antes de cargar el reranker para fallar rápido
        dependencies.validate_index_consistency(
            collection,
            bm25_index,
            parent_lookup,
        )

        retriever = dependencies.hybrid_retriever(
            collection,
            bm25_index,
            candidate_top_k=HYBRID_SOURCE_CANDIDATE_TOP_K,
            rrf_k=HYBRID_RRF_K,
        )

        reranker = dependencies.get_reranker(
            model_name=RERANKER_MODEL_NAME,
            max_length=RERANKER_MAX_LENGTH,
            device=RERANKER_DEVICE,
            revision=RERANKER_MODEL_REVISION,
        )

        first_table_parts = dependencies.load_first_table_parts(
            DEFAULT_TABLE_DOCUMENTS_PATH
        )

        # Memoria de corto plazo asociada al thread.
        checkpointer = InMemorySaver()

        # Mismo modelo de embeddings utilizado por el RAG.
        memory_embeddings = QwenMemoryEmbeddings(
            embedding_function,
            normalize_embeddings=True,
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
            llm=llm,
            retriever=retriever,
            top_k=HYBRID_RRF_OUTPUT_TOP_K,
            checkpointer=checkpointer,
            store=memory_store,
            reranker=reranker,
            reranker_candidate_pool_size=RERANKER_CANDIDATE_POOL_SIZE,
            reranker_final_top_k=RERANKER_FINAL_TOP_K,
            reranker_batch_size=RERANKER_BATCH_SIZE,
            reranker_device=RERANKER_DEVICE,
            reranker_input_max_length=RERANKER_MAX_LENGTH,
            parent_lookup=parent_lookup,
            first_table_parts=first_table_parts,
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
            f"{type(error).__name__}: {error}"
        ) from error
    
    thread_id = f"cli-session-{uuid4()}" # Generar un identificador único para cada hilo de conversación
    return RagRuntime(
        answer_with_langgraph=dependencies.answer_with_langgraph,
        graph=graph,
        thread_id=thread_id, # Agregar el identificador único al runtime para su uso en la conversación
        chroma_working_copy=chroma_working_copy,
    )


def load_dependencies() -> RuntimeDependencies:
    """Load optional runtime dependencies lazily so failures stay controlled."""

    try:
        from agents.consulta_normativa.langchain_rag.core.llm import build_deepseek_llm
        from agents.consulta_normativa.langchain_rag.graph import answer_with_langgraph, build_langgraph_rag
        from agents.consulta_normativa.langchain_rag.retrieval.chroma_retrieval import (
            create_working_copy as create_chroma_working_copy,
            open_existing_collection,
            qwen_embedding_function,
        )
        from agents.consulta_normativa.langchain_rag.retrieval.bm25_retrieval import (open_existing_index as open_existing_bm25_index)
        from agents.consulta_normativa.langchain_rag.retrieval.hybrid_retrieval import (hybrid_retriever)
        from agents.consulta_normativa.langchain_rag.retrieval.reranking import (get_reranker)
        from agents.consulta_normativa.langchain_rag.retrieval.parent_document_retrieval import (load_parent_documents)
        from agents.consulta_normativa.langchain_rag.retrieval.table_complement import load_first_table_parts
    except ModuleNotFoundError as error:
        raise OperationalError(f"Required runtime dependency is not installed: {error}") from error

    return RuntimeDependencies(
        validate_runtime_artifacts=validate_runtime_artifacts,
        build_deepseek_llm=build_deepseek_llm,
        build_langgraph_rag=build_langgraph_rag,
        answer_with_langgraph=answer_with_langgraph,
        open_existing_collection=open_existing_collection,
        open_existing_bm25_index=open_existing_bm25_index,
        hybrid_retriever=hybrid_retriever,
        get_reranker=get_reranker,
        load_parent_documents=load_parent_documents,
        load_first_table_parts=load_first_table_parts,
        create_chroma_working_copy=create_chroma_working_copy,
        validate_index_consistency=validate_index_consistency,
        build_embedding_function=qwen_embedding_function,
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
