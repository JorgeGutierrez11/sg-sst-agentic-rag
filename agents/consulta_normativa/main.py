"""CLI entrypoint for the base SG-SST normative consultation RAG."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

DEFAULT_TOP_K = 5
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 0
OPERATIONAL_ERROR_CODE = 2

Generator = Callable[[str], str]


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


@dataclass(frozen=True)
class RagDependencies:
    """Runtime dependencies for the CLI ask flow."""

    answer_question: Callable[..., Any]
    chroma_retriever: Callable[[Any], Callable[[str, int], dict[str, Any]]]
    open_existing_collection: Callable[[Any, str], Any]
    chroma_path: Any
    collection_name: str


def build_default_generator() -> Generator:
    """Return the default Groq-backed generator for the base RAG."""

    if not os.environ.get("GROQ_API_KEY"):
        raise GeneratorBuildError("GROQ_API_KEY is not configured in the environment.")

    try:
        # pyrefly: ignore [missing-import]
        from langchain_groq import ChatGroq

        llm = ChatGroq(
            model=DEFAULT_GROQ_MODEL, 
            temperature=DEFAULT_TEMPERATURE
        )
    except ModuleNotFoundError as error:
        raise GeneratorBuildError(f"langchain_groq is not installed: {error}") from error
    except Exception as error:  # noqa: BLE001 - CLI must convert provider setup failures to controlled errors.
        raise GeneratorBuildError(f"Could not build the Groq generator: {error}") from error

    def generate(prompt: str) -> str:
        response = llm.invoke(prompt)
        return str(response.content)

    return generate


def build_lazy_default_generator() -> Generator:
    """Return a generator that initializes Groq only when generation is needed."""

    generator: Generator | None = None

    def generate(prompt: str) -> str:
        nonlocal generator
        if generator is None:
            generator = build_default_generator()
        return generator(prompt)

    return generate


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the base normative consultation RAG."""

    parser = argparse.ArgumentParser(prog="python -m agents.consulta_normativa.main")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask")
    ask_parser.add_argument("question")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ask":
        return ask(args.question)

    parser.error(f"Unknown command: {args.command}")
    return OPERATIONAL_ERROR_CODE


def ask(question: str) -> int:
    """Answer one normative question through the base RAG flow."""

    try:
        dependencies = load_rag_dependencies()
    except OperationalError as error:
        return fail("dependency loading", error)
    except Exception as error:  # noqa: BLE001 - CLI must report operational failures without traceback.
        return fail("dependency loading", DependencyLoadError(str(error)))

    try:
        generator = build_lazy_default_generator()
    except OperationalError as error:
        return fail("generator setup", error)
    except Exception as error:  # noqa: BLE001 - CLI must report operational failures without traceback.
        return fail("generator setup", GeneratorBuildError(str(error)))

    try:
        collection = dependencies.open_existing_collection(dependencies.chroma_path, dependencies.collection_name)
    except Exception as error:  # noqa: BLE001 - CLI must report operational failures without traceback.
        return fail("Chroma collection opening", CollectionOpenError(str(error)))

    try:
        retriever = dependencies.chroma_retriever(collection)
        result = dependencies.answer_question(question, retriever, generator=generator, top_k=DEFAULT_TOP_K)
    except OperationalError as error:
        stage = "generator setup" if isinstance(error, GeneratorBuildError) else "RAG execution"
        return fail(stage, error)
    except Exception as error:  # noqa: BLE001 - CLI must report operational failures without traceback.
        return fail("RAG execution", RagExecutionError(str(error)))

    print_answer(result.answer, result.references)
    return 0


def fail(stage: str, error: Exception) -> int:
    """Print a controlled full error message for one CLI pipeline stage."""

    print(f"Error during {stage}:", file=sys.stderr)
    print(str(error), file=sys.stderr)
    return OPERATIONAL_ERROR_CODE


def load_rag_dependencies() -> RagDependencies:
    """Load RAG dependencies lazily so missing optional packages fail cleanly."""

    try:
        from agents.consulta_normativa.rag_base import answer_question, chroma_retriever
        from pipeline.vectorization.chroma_store import DEFAULT_COLLECTION_NAME, open_existing_collection
        from pipeline.vectorization.ingest import DEFAULT_CHROMA_PATH
    except ModuleNotFoundError as error:
        raise DependencyLoadError(f"Required runtime dependency is not installed: {error}") from error

    return RagDependencies(
        answer_question=answer_question,
        chroma_retriever=chroma_retriever,
        open_existing_collection=open_existing_collection,
        chroma_path=DEFAULT_CHROMA_PATH,
        collection_name=DEFAULT_COLLECTION_NAME,
    )


def print_answer(answer: str, references: list[str]) -> None:
    """Print the base readable answer and references sections."""

    print("Respuesta:")
    print(answer)
    print()
    print("Referencias:")
    for reference in references:
        print(f"- {reference}")


if __name__ == "__main__":
    raise SystemExit(main())
