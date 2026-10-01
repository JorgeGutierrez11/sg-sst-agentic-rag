
from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.interpretation import (
    AnswerInterpretation,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_answer_processor import (
    process_requirement_answers,
)


class ConditionAnswerSummary(BaseModel):
    """
    Información recopilada para una condición de un requisito.

    No representa cumplimiento ni incumplimiento normativo.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)
    condition_id: str = Field(min_length=1)

    interpretations: list[AnswerInterpretation] = Field(
        default_factory=list,
    )

    unanswered_question_ids: list[str] = Field(
        default_factory=list,
    )

    unresolved_question_ids: list[str] = Field(
        default_factory=list,
    )


def summarize_condition_answers(
    requirement: RequirementDefinition,
    answers: list[QuestionAnswer],
) -> list[ConditionAnswerSummary]:
    """
    Organiza las respuestas por condición.

    Reutiliza el procesamiento del requisito y conserva
    el orden de las condiciones y preguntas del catálogo.

    No determina si una condición normativa se cumple.
    """

    processing = process_requirement_answers(
        requirement,
        answers,
    )

    interpretations_by_question = {
        interpretation.question_id: interpretation
        for interpretation in processing.interpretations
    }

    unanswered_ids = set(processing.unanswered_question_ids)
    unresolved_ids = set(processing.unresolved_question_ids)

    summaries: list[ConditionAnswerSummary] = []

    for condition in requirement.conditions:
        condition_question_ids = [
            question.id
            for question in requirement.questions
            if question.condition_id == condition.id
        ]

        summaries.append(
            ConditionAnswerSummary(
                requirement_id=requirement.id,
                condition_id=condition.id,
                interpretations=[
                    interpretations_by_question[question_id]
                    for question_id in condition_question_ids
                    if question_id in interpretations_by_question
                ],
                unanswered_question_ids=[
                    question_id
                    for question_id in condition_question_ids
                    if question_id in unanswered_ids
                ],
                unresolved_question_ids=[
                    question_id
                    for question_id in condition_question_ids
                    if question_id in unresolved_ids
                ],
            )
        )

    return summaries
