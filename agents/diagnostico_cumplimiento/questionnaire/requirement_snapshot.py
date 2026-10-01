from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.catalog.schemas import (
    CatalogRequirementDefinition,
    PhvaDefinition,
    QuestionDependency,
    QuestionRole,
    RequirementApplicability,
    RequirementScoring,
    RequirementSource,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.condition_evaluation import (
    ConditionEvaluation,
)
from agents.diagnostico_cumplimiento.domain.enums import (
    QuestionType,
)
from agents.diagnostico_cumplimiento.domain.interpretation import (
    AnswerInterpretation,
)
from agents.diagnostico_cumplimiento.questionnaire.condition_progress import (
    ConditionCollectionStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_progress import (
    RequirementCollectionStatus,
    determine_requirement_progress,
)


class QuestionRoutingState(StrEnum):
    """
    Estado de una pregunta dentro del routing del requisito.
    """

    ACTIVE = "active"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class QuestionSnapshot(BaseModel):
    """
    Estado consolidado de una pregunta del cuestionario.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1)

    role: QuestionRole

    text: str = Field(min_length=1)

    question_type: QuestionType

    source_type: str = Field(min_length=1)

    depends_on: QuestionDependency | None = None

    routing_state: QuestionRoutingState

    answer: QuestionAnswer | None = None

    interpretation: AnswerInterpretation | None = None


# ============================================================
# LEGACY
# ============================================================
#
# Se conserva temporalmente porque declarative_findings.py
# todavía importa ConditionSnapshot.
#
# El nuevo flujo ya no construye ConditionSnapshot.
# ============================================================


class ConditionSnapshot(BaseModel):
    """
    Modelo legado de condición.

    Se eliminará cuando termine la migración del reporting.
    """

    model_config = ConfigDict(extra="forbid")

    condition_id: str = Field(min_length=1)

    description: str = Field(min_length=1)

    collection_status: ConditionCollectionStatus

    evaluation: ConditionEvaluation

    questions: list[QuestionSnapshot] = Field(
        default_factory=list,
    )


class RequirementSnapshot(BaseModel):
    """
    Estado consolidado de un requisito normativo.

    Contiene la información normativa, clasificación PHVA,
    configuración de aplicabilidad, preguntas, respuestas,
    interpretaciones y estado de routing.

    No determina por sí mismo cumplimiento normativo.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

    official_item_id: str | None = None

    name: str = Field(min_length=1)

    phva: PhvaDefinition

    scoring: RequirementScoring

    official_criterion: str = Field(min_length=1)

    official_verification_method: str | None = None

    verification_method_source: str = Field(min_length=1)

    applicability: RequirementApplicability

    source: RequirementSource

    collection_status: RequirementCollectionStatus

    questions: list[QuestionSnapshot] = Field(
        min_length=1,
    )

    active_question_ids: list[str] = Field(
        default_factory=list,
    )

    unanswered_question_ids: list[str] = Field(
        default_factory=list,
    )

    unresolved_question_ids: list[str] = Field(
        default_factory=list,
    )

    skipped_question_ids: list[str] = Field(
        default_factory=list,
    )

    blocked_question_ids: list[str] = Field(
        default_factory=list,
    )

    # --------------------------------------------------------
    # Compatibilidad temporal
    # --------------------------------------------------------

    @property
    def criterion_name(self) -> str:
        """
        Alias temporal utilizado por código antiguo.
        """
        return self.name

    @property
    def criterion_official_text(self) -> str:
        """
        Alias temporal utilizado por código antiguo.
        """
        return self.official_criterion

    @property
    def verification_method(self) -> str | None:
        """
        Alias temporal utilizado por código antiguo.
        """
        return self.official_verification_method


def build_requirement_snapshot(
    requirement: CatalogRequirementDefinition,
    answers: list[QuestionAnswer],
    *,
    llm: Any | None = None,
) -> RequirementSnapshot:
    """
    Consolida el estado de un requisito.

    El snapshot conserva:

    - información normativa;
    - clasificación PHVA;
    - respuestas originales;
    - interpretaciones;
    - preguntas activas;
    - preguntas omitidas por routing;
    - preguntas bloqueadas;
    - preguntas pendientes o no resueltas.

    No asigna cumplimiento normativo ni puntajes.
    """

    progress = determine_requirement_progress(
        requirement,
        answers,
        llm=llm,
    )

    answers_by_id = {
        answer.question_id: answer
        for answer in answers
    }

    interpretations_by_id = {
        interpretation.question_id: interpretation
        for interpretation in progress.interpretations
    }

    active_ids = set(progress.active_question_ids)
    skipped_ids = set(progress.skipped_question_ids)
    blocked_ids = set(progress.blocked_question_ids)

    questions: list[QuestionSnapshot] = []

    for question in requirement.questions:

        if question.id in skipped_ids:
            routing_state = QuestionRoutingState.SKIPPED

        elif question.id in blocked_ids:
            routing_state = QuestionRoutingState.BLOCKED

        elif question.id in active_ids:
            routing_state = QuestionRoutingState.ACTIVE

        else:
            raise ValueError(
                f"No fue posible determinar el estado de routing "
                f"de la pregunta '{question.id}' del requisito "
                f"'{requirement.id}'."
            )

        questions.append(
            QuestionSnapshot(
                question_id=question.id,
                role=question.role,
                text=question.text,
                question_type=question.type,
                source_type=question.source_type,
                depends_on=question.depends_on,
                routing_state=routing_state,
                answer=answers_by_id.get(question.id),
                interpretation=interpretations_by_id.get(
                    question.id
                ),
            )
        )

    return RequirementSnapshot(
        requirement_id=requirement.id,
        official_item_id=requirement.official_item_id,
        name=requirement.name,
        phva=requirement.phva,
        scoring=requirement.scoring,
        official_criterion=requirement.official_criterion,
        official_verification_method=(
            requirement.official_verification_method
        ),
        verification_method_source=(
            requirement.verification_method_source
        ),
        applicability=requirement.applicability,
        source=requirement.source,
        collection_status=progress.status,
        questions=questions,
        active_question_ids=progress.active_question_ids,
        unanswered_question_ids=progress.unanswered_question_ids,
        unresolved_question_ids=progress.unresolved_question_ids,
        skipped_question_ids=progress.skipped_question_ids,
        blocked_question_ids=progress.blocked_question_ids,
    )