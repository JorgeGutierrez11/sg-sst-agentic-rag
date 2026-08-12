"""Direct executable entrypoint for the experimental LangChain RAG variant."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# pyrefly: ignore [missing-import]
from agents.consulta_normativa.config import DEFAULT_CHROMA_PATH, DEFAULT_COLLECTION_NAME, DEFAULT_TOP_K

OPERATIONAL_ERROR_CODE = 2

Retriever = Callable[[str, int], dict[str, Any]]


class OperationalError(Exception):
    """Controlled error for expected runtime setup and execution failures."""


@dataclass(frozen=True)
class RuntimeDependencies:
    """Lazy-loaded dependencies required by the executable RAG flow."""

    answer_with_langchain: Callable[[str, Retriever, Any, int], Any]
    build_groq_llm: Callable[[], Any]
    chroma_retriever: Callable[[Any], Retriever]
    open_existing_collection: Callable[[Any, str], Any]


@dataclass(frozen=True)
class RagRuntime:
    """Reusable runtime built once for direct or interactive execution."""

    answer_with_langchain: Callable[[str, Retriever, Any, int], Any]
    retriever: Retriever
    llm: Any


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
    """Build the Chroma retriever and Groq-backed LLM for the session."""

    dependencies = load_dependencies()

    try:
        llm = dependencies.build_groq_llm()
    except Exception as error:  # noqa: BLE001 - keep missing key/package/provider errors controlled.
        raise OperationalError(str(error)) from error

    try:
        collection = dependencies.open_existing_collection(DEFAULT_CHROMA_PATH, DEFAULT_COLLECTION_NAME)
        retriever = dependencies.chroma_retriever(collection)
    except Exception as error:  # noqa: BLE001 - Chroma path, package, and collection failures are operational.
        raise OperationalError(str(error)) from error

    return RagRuntime(
        answer_with_langchain=dependencies.answer_with_langchain,
        retriever=retriever,
        llm=llm,
    )


def load_dependencies() -> RuntimeDependencies:
    """Load optional runtime dependencies lazily so failures stay controlled."""

    try:
        # pyrefly: ignore [missing-import]
        from agents.consulta_normativa.rag_base import chroma_retriever
        from agents.consulta_normativa.langchain_rag.chain import answer_with_langchain, build_groq_llm
        from agents.shared.chroma_retrieval import open_existing_collection
    except ModuleNotFoundError as error:
        raise OperationalError(f"Required runtime dependency is not installed: {error}") from error

    return RuntimeDependencies(
        answer_with_langchain=answer_with_langchain,
        build_groq_llm=build_groq_llm,
        chroma_retriever=chroma_retriever,
        open_existing_collection=open_existing_collection,
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
        result = runtime.answer_with_langchain(question, runtime.retriever, runtime.llm, DEFAULT_TOP_K)
    except Exception as error:  # noqa: BLE001 - direct CLI should report RAG failures without traceback.
        return fail("RAG execution", OperationalError(str(error)))

    print_answer(result.answer, result.references)
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
