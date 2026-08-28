"""Interactive CLI entrypoint for the base SG-SST normative consultation RAG."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agents.consulta_normativa.manual_implementation.config import (
    DEFAULT_CHROMA_PATH,
    DEFAULT_COLLECTION_NAME,
    DEFAULT_GROQ_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
)

OPERATIONAL_ERROR_CODE = 2

Generator = Callable[[str], str]

# Custom Application Exceptions 
class OperationalError(Exception):
    """Controlled error for missing runtime dependencies or configuration."""


class DependencyLoadError(OperationalError):
    """Controlled error raised when CLI runtime dependencies cannot be loaded."""


class GeneratorBuildError(OperationalError):
    """Controlled error raised when the default LLM generator cannot be built."""


class CollectionOpenError(OperationalError):
    """Controlled error raised when the Chroma collection cannot be opened."""


class RagExecutionError(OperationalError):
    """Controlled error raised when retrieval or generation fails."""

# Data structures 
@dataclass(frozen=True)
class RagDependencies:
    """Import-time dependencies for the interactive CLI flow."""

    answer_question: Callable[..., Any]
    chroma_retriever: Callable[[Any], Callable[[str, int], dict[str, Any]]]
    open_existing_collection: Callable[[Any, str], Any]
    chroma_path: Any
    collection_name: str


@dataclass(frozen=True)
class RagRuntime:
    """Ready-to-use RAG runtime reused for every interactive question."""

    answer_question: Callable[..., Any]
    retriever: Callable[[str, int], dict[str, Any]]
    generator: Generator

# Core build functions
def build_default_generator() -> Generator:
    """Return the default Groq-backed generator for the base RAG."""

    if not os.environ.get("GROQ_API_KEY"):
        raise GeneratorBuildError("GROQ_API_KEY is not configured in the environment.")

    try:
        # pyrefly: ignore [missing-import]
        from langchain_groq import ChatGroq

        llm = ChatGroq(
            model=DEFAULT_GROQ_MODEL,
            temperature=DEFAULT_TEMPERATURE,
        )
    except ModuleNotFoundError as error:
        raise GeneratorBuildError(f"langchain_groq is not installed: {error}") from error
    except Exception as error:  # noqa: BLE001 - CLI must convert provider setup failures to controlled errors.
        raise GeneratorBuildError(f"Could not build the Groq generator: {error}") from error

    def generate(prompt: str) -> str:
        response = llm.invoke(prompt)
        return str(response.content)

    return generate

# Main flow
def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = argparse.ArgumentParser(prog="python -m agents.consulta_normativa.main")
    parser.parse_args(argv)

    try:
        runtime = build_rag_runtime()
    except OperationalError as error:
        if isinstance(error, StagedOperationalError):
            return fail(error.stage, error)
        return fail("initialization", error)
    except Exception as error:  # noqa: BLE001 - CLI must report operational failures without traceback.
        return fail("initialization", OperationalError(str(error)))

    return run_interactive_loop(runtime)

# RAG builder
def build_rag_runtime() -> RagRuntime:
    """Build the reusable RAG runtime once for the interactive session."""

    try:
        # answer_question, chroma_retriever, open_existing_collection, chroma_path, collection_name 
        dependencies = load_rag_dependencies()
    except OperationalError as error:
        raise StagedOperationalError("dependency loading", str(error)) from error
    except Exception as error:  # noqa: BLE001 - CLI must report operational failures without traceback.
        raise StagedOperationalError("dependency loading", str(error)) from error

    try:
        # Carga el modelo LLM (Groq)
        generator = build_default_generator() 
    except OperationalError as error:
        raise StagedOperationalError("generator setup", str(error)) from error
    except Exception as error:  # noqa: BLE001 - CLI must report operational failures without traceback.
        raise StagedOperationalError("generator setup", str(error)) from error

    try:
        collection = dependencies.open_existing_collection(
            dependencies.chroma_path,
            dependencies.collection_name,
        )
        retriever = dependencies.chroma_retriever(collection)
    except Exception as error:  # noqa: BLE001 - CLI must report operational failures without traceback.
        raise StagedOperationalError("Chroma collection opening", str(error)) from error

    return RagRuntime(
        answer_question=dependencies.answer_question,
        retriever=retriever,
        generator=generator,
    )


def run_interactive_loop(runtime: RagRuntime) -> int:
    """Read questions until the user exits, keeping the runtime alive."""

    print("RAG normativo listo. Escribe 'exit' o 'quit' para salir.")

    while True:
        try:
            question = input("Pregunta> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            return 0

        try:
            answer_once(runtime, question)
        except OperationalError as error:
            stage = "generator setup" if isinstance(error, GeneratorBuildError) else "RAG execution"
            print_controlled_error(stage, error)
        except Exception as error:  # noqa: BLE001 - CLI must keep the session alive after one failed question.
            print_controlled_error("RAG execution", RagExecutionError(str(error)))


def answer_once(runtime: RagRuntime, question: str) -> None:
    """Answer one question with the already initialized RAG runtime."""

    result = runtime.answer_question(
        question,
        runtime.retriever,
        generator=runtime.generator,
        top_k=DEFAULT_TOP_K,
    )
    print_answer(result.answer, result.references, result.context)

# Error Handling
@dataclass(frozen=True)
class StagedOperationalError(OperationalError):
    """Controlled operational error that already knows its failing stage."""

    stage: str
    message: str

    def __str__(self) -> str:
        return self.message


def fail(stage: str, error: Exception) -> int:
    """Print a controlled full error message for one CLI pipeline stage."""

    print_controlled_error(stage, error)
    return OPERATIONAL_ERROR_CODE


def print_controlled_error(stage: str, error: Exception) -> None:
    """Print a controlled full error message for one CLI pipeline stage."""

    print(f"Error during {stage}:", file=sys.stderr)
    print(str(error), file=sys.stderr)


# Auxiliar Functions 
def load_rag_dependencies() -> RagDependencies:
    """Load RAG dependencies lazily so missing optional packages fail cleanly."""

    try:
        from agents.consulta_normativa.manual_implementation.rag_base import answer_question, chroma_retriever
        from agents.consulta_normativa.langchain_rag.retrieval.chroma_retrieval import open_existing_collection
    except ModuleNotFoundError as error:
        raise DependencyLoadError(f"Required runtime dependency is not installed: {error}") from error

    return RagDependencies(
        answer_question=answer_question,
        chroma_retriever=chroma_retriever,
        open_existing_collection=open_existing_collection,
        chroma_path=DEFAULT_CHROMA_PATH,
        collection_name=DEFAULT_COLLECTION_NAME,
    )


def print_answer(answer: str, references: list[str], context: str) -> None:
    """Print the base readable answer and references sections."""
    print("Contexto recuperado:")
    print(context)
    print()
    print("-----------------------------------------------------")
    print("Respuesta:")
    print(answer)
    print()
    print("-----------------------------------------------------")
    print("Referencias:")
    for reference in references:
        print(f"- {reference}")


if __name__ == "__main__":
    raise SystemExit(main())
