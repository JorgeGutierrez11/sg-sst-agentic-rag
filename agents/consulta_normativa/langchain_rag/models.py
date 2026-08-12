"""Data models for the experimental LangChain/LangGraph RAG pipeline."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RetrievedDocument:
    """One document recovered from a retriever."""

    document: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LangChainRagResult:
    """Answer and evidence produced by the experimental RAG pipeline."""

    answer: str
    references: list[str]
    context: str
    prompt: str
