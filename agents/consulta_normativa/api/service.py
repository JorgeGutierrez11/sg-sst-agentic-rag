from typing import Any
from uuid import uuid4

from agents.consulta_normativa.api.schemas import QueryResponse


class QueryService:
    """Application boundary for asking the current LangGraph RAG runtime."""

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime

    def ask(self, question: str, conversation_id: str | None = None) -> QueryResponse:
        result = self.runtime.answer_with_langgraph(question, self.runtime.graph)
        return QueryResponse(
            answer=result.answer,
            references=list(result.references),
            chunks=list(result.chunks),
            conversation_id=conversation_id or str(uuid4()),
        )
