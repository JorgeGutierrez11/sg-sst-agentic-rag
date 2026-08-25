"""Direct executable entrypoint for the experimental LangChain RAG variant."""

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agents.consulta_normativa.langchain_rag.config import (
    DEFAULT_CHROMA_PATH,
    DEFAULT_COLLECTION_NAME,
    HYBRID_CANDIDATE_TOP_K,
    HYBRID_RRF_K,
    RETRIEVAL_TOP_K,
)
from agents.consulta_normativa.langchain_rag.models import LangChainRagResult
from agents.shared.bm25_retrieval import DEFAULT_BM25_PATH

OPERATIONAL_ERROR_CODE = 2

Retriever = Callable[[str, int], dict[str, Any]]


class OperationalError(Exception):
    """Controlled error for expected runtime setup and execution failures."""


@dataclass(frozen=True)
class RuntimeDependencies:
    """Lazy-loaded dependencies required by the executable RAG flow."""

    build_groq_llm: Callable[[], Any]
    build_langgraph_rag: Callable[..., Any]
    answer_with_langgraph: Callable[[str, Any], Any]
    hybrid_retriever: Callable[..., Retriever]
    open_existing_collection: Callable[[Any, str], Any]
    open_existing_index: Callable[[Any], Any]


@dataclass(frozen=True)
class RagRuntime:
    """Reusable runtime built once for direct or interactive execution."""

    answer_with_langgraph: Callable[[str, Any], Any]
    graph: Any


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


def build_runtime() -> RagRuntime:
    """Build the hybrid retriever and Groq-backed LLM for the session."""

    dependencies = load_dependencies()

    try:
        llm = dependencies.build_groq_llm()
    except Exception as error:  
        raise OperationalError(str(error)) from error

    try:
        # Cargar Chroma y el índice de BM25
        collection = dependencies.open_existing_collection(DEFAULT_CHROMA_PATH, DEFAULT_COLLECTION_NAME)
        sparse_index = dependencies.open_existing_index(DEFAULT_BM25_PATH)

        # Crear el retriever
        retriever = dependencies.hybrid_retriever(
            collection,
            sparse_index,
            candidate_top_k=HYBRID_CANDIDATE_TOP_K,
            rrf_k=HYBRID_RRF_K,
        )

        graph = dependencies.build_langgraph_rag(
            llm,
            retriever,
            top_k=RETRIEVAL_TOP_K,
        )

        # Guardar diagrama en disco
        png_bytes = graph.get_graph().draw_mermaid_png()
        with open("data/images/base_rag_graph.png", "wb") as f:
            f.write(png_bytes)
        print("Grafo guardado exitosamente como 'base_rag_graph.png'")

    except Exception as error:
        raise OperationalError(str(error)) from error

    return RagRuntime(
        answer_with_langgraph=dependencies.answer_with_langgraph,
        graph=graph,
    )


def load_dependencies() -> RuntimeDependencies:
    """Load optional runtime dependencies lazily so failures stay controlled."""

    try:
        from agents.consulta_normativa.langchain_rag.core.llm import build_groq_llm
        from agents.consulta_normativa.langchain_rag.graph import answer_with_langgraph, build_langgraph_rag
        from agents.shared.bm25_retrieval import open_existing_index
        from agents.shared.chroma_retrieval import open_existing_collection
        from agents.shared.hybrid_retrieval import hybrid_retriever
    except ModuleNotFoundError as error:
        raise OperationalError(f"Required runtime dependency is not installed: {error}") from error

    return RuntimeDependencies(
        build_groq_llm=build_groq_llm,
        build_langgraph_rag=build_langgraph_rag,
        answer_with_langgraph=answer_with_langgraph,

        # Aqui seleccionar el Retriever
        hybrid_retriever=hybrid_retriever,
        open_existing_collection=open_existing_collection,
        open_existing_index=open_existing_index,
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
        result = runtime.answer_with_langgraph(question, runtime.graph)
    except Exception as error:
        return fail("RAG execution", OperationalError(str(error)))

    print_answer(result)
    return 0


def print_answer(result: LangChainRagResult) -> None:
    print("-----------------------------------")
    print("Prompt sent to model:")
    print(result.prompt)
    print("-----------------------------------")
    print()
    print("Answer:")
    print(result.answer)
    print("-----------------------------------")
    if result.references:
        print()
        print("References:")
        for reference in result.references:
            print(f"- {reference}")


def fail(stage: str, error: Exception) -> int:
    """Print one controlled operational error and return the CLI error code."""

    print(f"Error during {stage}:", file=sys.stderr)
    print(str(error), file=sys.stderr)
    return OPERATIONAL_ERROR_CODE


if __name__ == "__main__":
    raise SystemExit(main())
