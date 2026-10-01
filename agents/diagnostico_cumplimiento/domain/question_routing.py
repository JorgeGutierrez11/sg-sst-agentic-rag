from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class QuestionRoutingStatus(StrEnum):
    """
    Estado de una pregunta dentro del flujo dinámico.
    """

    ASK = "ask"
    ANSWERED = "answered"
    OMIT = "omit"


class QuestionRoutingDecision(BaseModel):
    """
    Registra la decisión tomada sobre una pregunta.

    ASK:
        La pregunta debe formularse.

    ANSWERED:
        La pregunta ya tiene una respuesta y permanece
        registrada en la traza.

    OMIT:
        La pregunta no debe formularse debido a una
        regla explícita del flujo.

    Este modelo no determina cumplimiento ni
    aplicabilidad normativa.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1)
    status: QuestionRoutingStatus

    rule_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    triggered_by: str | None = None


class QuestionRoutingTrace(BaseModel):
    """
    Traza completa de las decisiones de enrutamiento
    tomadas durante una parte del cuestionario.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

    decisions: list[QuestionRoutingDecision] = Field(
        default_factory=list,
    )

    @property
    def questions_to_ask(self) -> list[str]:
        return [
            decision.question_id
            for decision in self.decisions
            if decision.status == QuestionRoutingStatus.ASK
        ]

    @property
    def answered_questions(self) -> list[str]:
        return [
            decision.question_id
            for decision in self.decisions
            if decision.status == QuestionRoutingStatus.ANSWERED
        ]

    @property
    def omitted_questions(self) -> list[str]:
        return [
            decision.question_id
            for decision in self.decisions
            if decision.status == QuestionRoutingStatus.OMIT
        ]