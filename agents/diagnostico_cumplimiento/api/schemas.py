from typing import Annotated, Literal

# pyrefly: ignore [missing-import]
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class HealthResponse(BaseModel):
    status: str


class CreateDiagnosticRequest(BaseModel):
    worker_count: Annotated[int, Field(gt=0)]

    company_name: str | None = None


class QuestionResponse(BaseModel):
    requirement_id: str
    requirement_name: str

    question_id: str
    text: str
    role: str
    question_type: str

    requirement_number: int
    total_requirements: int


class DiagnosticProgressResponse(BaseModel):
    completed_requirements: int
    total_requirements: int

    current_requirement_number: int | None = None
    current_requirement_id: str | None = None

    completed: bool = False


class RequirementProgressResponse(BaseModel):
    requirement_id: str
    requirement_name: str
    requirement_number: int
    status: Literal["pending", "in_progress", "completed"]


class DiagnosticStateResponse(BaseModel):
    diagnosis_id: str
    revision: int = 0
    progress: DiagnosticProgressResponse
    next_question: QuestionResponse | None = None
    requirements: list[RequirementProgressResponse] = Field(default_factory=list)


class CreateDiagnosticResponse(DiagnosticStateResponse):
    catalog_id: str
    catalog_name: str



class SubmitAnswerRequest(BaseModel):
    requirement_id: str
    question_id: str

    answer: bool | str
    revision: Annotated[int, Field(ge=0)]

    @field_validator("answer")
    @classmethod
    def answer_must_not_be_blank(
        cls,
        value: bool | str,
    ) -> bool | str:
        if isinstance(value, str):
            value = value.strip()

            if not value:
                raise ValueError(
                    "answer must not be blank"
                )

        return value


class SubmitAnswerResponse(DiagnosticStateResponse):
    interpretation_status: str
    clarification_message: str | None = None


class RestartRequirementRequest(BaseModel):
    revision: Annotated[int, Field(ge=0)]


class RequirementAssessmentResponse(BaseModel):
    requirement_id: str
    requirement_name: str

    applicability_status: str
    assessment_status: str

    explanation: str
    missing_information: list[str] = Field(
        default_factory=list
    )


class DiagnosticSummaryResponse(BaseModel):
    total_requirements: int

    complies_as_declared: int = 0
    does_not_comply_as_declared: int = 0
    insufficient_information: int = 0
    not_applicable: int = 0


class CompleteDiagnosticResponse(BaseModel):
    diagnosis_id: str

    assessments: list[RequirementAssessmentResponse]

    summary: DiagnosticSummaryResponse

    scope_note: str


class ErrorResponse(BaseModel):
    detail: str
