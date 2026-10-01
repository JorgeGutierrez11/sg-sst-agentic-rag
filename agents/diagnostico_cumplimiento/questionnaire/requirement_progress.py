from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.catalog.schemas import (
    CatalogRequirementDefinition,
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


class RequirementCollectionStatus(StrEnum):
    """
    Estado general de recopilación de información de un requisito.
    """

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    NEEDS_RESOLUTION = "needs_resolution"
    ANSWERS_INTERPRETED = "answers_interpreted"


class RequirementProgress(BaseModel):
    """
    Estado de avance de un requisito.

    Ya no depende de condiciones internas. El progreso se determina
    directamente a partir de las preguntas activas y su routing.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

    status: RequirementCollectionStatus

    interpretations: list[AnswerInterpretation] = Field(
        default_factory=list,
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


def determine_requirement_progress(
    requirement: CatalogRequirementDefinition,
    answers: list[QuestionAnswer],
    *,
    llm: Any | None = None,
) -> RequirementProgress:
    """
    Determina el estado de recopilación de un requisito.

    Utiliza el routing definido mediante ``depends_on`` para distinguir
    entre preguntas:

    - activas;
    - pendientes;
    - no resueltas;
    - omitidas por routing;
    - bloqueadas por una dependencia aún no resuelta.

    No determina cumplimiento normativo ni asigna puntajes.
    """

    processing = process_requirement_answers(
        requirement,
        answers,
        llm=llm,
    )

    answered_question_ids = {
        interpretation.question_id
        for interpretation in processing.interpretations
    }

    # --------------------------------------------------------
    # 1. Hay una respuesta activa que todavía no pudo resolverse.
    # --------------------------------------------------------

    if processing.unresolved_question_ids:
        status = RequirementCollectionStatus.NEEDS_RESOLUTION

    # --------------------------------------------------------
    # 2. Todavía no se ha interpretado ninguna pregunta activa.
    #
    # Aunque existan preguntas dependientes bloqueadas, el requisito
    # sigue sin iniciarse si ninguna pregunta raíz ha sido respondida.
    # --------------------------------------------------------

    elif not answered_question_ids:
        status = RequirementCollectionStatus.NOT_STARTED

    # --------------------------------------------------------
    # 3. Quedan preguntas activas pendientes o preguntas bloqueadas.
    # --------------------------------------------------------

    elif (
        processing.unanswered_question_ids
        or processing.blocked_question_ids
    ):
        status = RequirementCollectionStatus.IN_PROGRESS

    # --------------------------------------------------------
    # 4. Todas las preguntas activas fueron interpretadas.
    #
    # Las preguntas skipped no cuentan como pendientes porque fueron
    # excluidas correctamente por el routing.
    # --------------------------------------------------------

    else:
        status = RequirementCollectionStatus.ANSWERS_INTERPRETED

    return RequirementProgress(
        requirement_id=requirement.id,
        status=status,
        interpretations=processing.interpretations,
        active_question_ids=processing.active_question_ids,
        unanswered_question_ids=processing.unanswered_question_ids,
        unresolved_question_ids=processing.unresolved_question_ids,
        skipped_question_ids=processing.skipped_question_ids,
        blocked_question_ids=processing.blocked_question_ids,
    )