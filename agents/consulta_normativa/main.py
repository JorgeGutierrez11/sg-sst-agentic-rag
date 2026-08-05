"""CLI entrypoint for the base SG-SST normative consultation RAG."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq

DEFAULT_TOP_K = 5
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 0
OPERATIONAL_ERROR_CODE = 2

Generator = Callable[[str], str]

# Se usa para errores operativos en el CLI - Como funciona???
class OperationalError(Exception):
    """Controlled error for missing runtime dependencies or configuration."""


@dataclass(frozen=True)
class RagDependencies:
    """Runtime dependencies for the CLI ask flow."""

    answer_question: Callable[..., Any]
    chroma_retriever: Callable[[Any], Callable[[str, int], dict[str, Any]]]
    open_collection: Callable[[Any, str], Any]
    chroma_path: Any
    collection_name: str


def build_default_generator() -> Generator:
    """Return the default Groq-backed generator for the base RAG."""

    if not os.environ.get("GROQ_API_KEY"):
        raise OperationalError("GROQ_API_KEY is not configured in the environment.")

    try:
        llm = ChatGroq(
            model=DEFAULT_GROQ_MODEL, 
            temperature=DEFAULT_TEMPERATURE
        )
    except Exception as error:  # noqa: BLE001 - CLI must convert provider setup failures to controlled errors.
        raise OperationalError("Could not build the Groq generator.") from error

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
        generator = build_lazy_default_generator()
        collection = dependencies.open_collection(dependencies.chroma_path, dependencies.collection_name)
        retriever = dependencies.chroma_retriever(collection)
        result = dependencies.answer_question(question, retriever, generator=generator, top_k=DEFAULT_TOP_K)
    except OperationalError as error:
        print(f"Error: {error}", file=sys.stderr)
        return OPERATIONAL_ERROR_CODE
    except Exception as error:  # noqa: BLE001 - CLI must report operational failures without traceback.
        print("Error: Could not run the normative consultation CLI.", file=sys.stderr)
        return OPERATIONAL_ERROR_CODE

    print_answer(result.answer, result.references)
    return 0


def load_rag_dependencies() -> RagDependencies:
    """Load RAG dependencies lazily so missing optional packages fail cleanly."""

    try:
        from agents.consulta_normativa.rag_base import answer_question, chroma_retriever
        from pipeline.vectorization.chroma_store import DEFAULT_COLLECTION_NAME, open_collection
        from pipeline.vectorization.ingest import DEFAULT_CHROMA_PATH
    except ModuleNotFoundError as error:
        raise OperationalError("Required runtime dependency is not installed.") from error

    return RagDependencies(
        answer_question=answer_question,
        chroma_retriever=chroma_retriever,
        open_collection=open_collection,
        chroma_path=DEFAULT_CHROMA_PATH,
        collection_name=DEFAULT_COLLECTION_NAME,
    )


def print_answer(answer: str, references: list[str]) -> None:
    """Print the base readable answer and references sections."""

    print("Answer:")
    print(answer)
    print()
    print("References:")
    for reference in references:
        print(f"- {reference}")


if __name__ == "__main__":
    raise SystemExit(main())
