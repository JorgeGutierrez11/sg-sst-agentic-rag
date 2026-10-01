from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.domain.interpretation import (
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_snapshot import (
    RequirementSnapshot,
)


class DeclarationFindingStatus(StrEnum):
    """
    Estado declarativo general de un requisito.

    No representa todavía una conclusión normativa definitiva.
    """

    ALL_AFFIRMATIVE_DECLARED = "all_affirmative_declared"
    HAS_NEGATIVE_DECLARATION = "has_negative_declaration"
    INCOMPLETE = "incomplete"
    NEEDS_CLARIFICATION = "needs_clarification"


class RequirementDeclarativeFindings(BaseModel):
    """
    Hallazgo consolidado de un requisito a partir de las
    declaraciones realizadas por el usuario.

    No verifica documentos ni asigna cumplimiento normativo.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

    status: DeclarationFindingStatus

    negative_question_ids: list[str] = Field(
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

    evidence_verified: bool = False


def summarize_requirement_declarations(
    requirement: RequirementSnapshot,
) -> RequirementDeclarativeFindings:
    """
    Genera un hallazgo declarativo para un requisito completo.

    Solo considera como evaluables las preguntas activas.

    Las preguntas omitidas por routing no se consideran
    pendientes ni negativas.

    Las preguntas bloqueadas indican que una dependencia previa
    todavía no ha sido resuelta.

    No determina cumplimiento normativo ni asigna puntajes.
    """

    negative_question_ids: list[str] = []

    for question in requirement.questions:

        if question.question_id not in requirement.active_question_ids:
            continue

        interpretation = question.interpretation

        if interpretation is None:
            continue

        if interpretation.status == InterpretationStatus.NEGATIVE:
            negative_question_ids.append(
                question.question_id
            )

    # --------------------------------------------------------
    # Prioridad 1: existen respuestas que necesitan resolución.
    # --------------------------------------------------------

    if requirement.unresolved_question_ids:
        status = (
            DeclarationFindingStatus.NEEDS_CLARIFICATION
        )

    # --------------------------------------------------------
    # Prioridad 2: faltan respuestas activas o existen preguntas
    # bloqueadas por dependencias aún no resueltas.
    # --------------------------------------------------------

    elif (
        requirement.unanswered_question_ids
        or requirement.blocked_question_ids
    ):
        status = DeclarationFindingStatus.INCOMPLETE

    # --------------------------------------------------------
    # Prioridad 3: existe al menos una declaración negativa.
    # --------------------------------------------------------

    elif negative_question_ids:
        status = (
            DeclarationFindingStatus.HAS_NEGATIVE_DECLARATION
        )

    # --------------------------------------------------------
    # Todas las preguntas activas fueron resueltas afirmativamente.
    # Las preguntas skipped no afectan este resultado.
    # --------------------------------------------------------

    else:
        status = (
            DeclarationFindingStatus.ALL_AFFIRMATIVE_DECLARED
        )

    return RequirementDeclarativeFindings(
        requirement_id=requirement.requirement_id,
        status=status,
        negative_question_ids=negative_question_ids,
        unanswered_question_ids=(
            requirement.unanswered_question_ids
        ),
        unresolved_question_ids=(
            requirement.unresolved_question_ids
        ),
        skipped_question_ids=(
            requirement.skipped_question_ids
        ),
        blocked_question_ids=(
            requirement.blocked_question_ids
        ),
        evidence_verified=False,
    )