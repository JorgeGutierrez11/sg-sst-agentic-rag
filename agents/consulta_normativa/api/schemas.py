from typing import Annotated

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    question: Annotated[str, Field(min_length=1)]
    conversation_id: str | None = None

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value.strip()


class QueryResponse(BaseModel):
    answer: str
    references: list[str]
    conversation_id: str


class HealthResponse(BaseModel):
    status: str
