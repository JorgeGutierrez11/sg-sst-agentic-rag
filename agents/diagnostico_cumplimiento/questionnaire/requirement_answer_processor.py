from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.catalog.schemas import (
    CatalogRequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.enums import (
    QuestionType,
)
from agents.diagnostico_cumplimiento.domain.interpretation import (
    AnswerInterpretation,
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_collection import (
    collect_requirement_answers,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_interpreter import (
    interpret_boolean_answer_hybrid,
)


class RequirementAnswerProcessingResult(BaseModel):
    """
    Resultado del procesamiento de respuestas de un requisito.

    No determina cumplimiento normativo ni asigna puntajes.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

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


def process_requirement_answers(
    requirement: CatalogRequirementDefinition,
    answers: list[QuestionAnswer],
    *,
    llm: Any | None = None,
) -> RequirementAnswerProcessingResult:
    """
    Procesa las respuestas registradas para un requisito.

    El flujo es:

    1. Valida y organiza las respuestas.
    2. Interpreta las respuestas booleanas.
    3. Resuelve las dependencias ``depends_on``.
    4. Clasifica las preguntas como activas, omitidas o bloqueadas.
    5. Identifica preguntas activas pendientes o no resueltas.

    Una pregunta dependiente:

    - queda activa si la respuesta interpretada de la pregunta padre
      coincide con el valor esperado;
    - queda omitida si la dependencia fue resuelta y no coincide;
    - queda bloqueada si la pregunta padre todavía no tiene una
      interpretación resolutiva.

    Las preguntas omitidas por routing no se consideran pendientes.

    No evalúa cumplimiento normativo ni asigna puntajes.
    """

    collected = collect_requirement_answers(
        requirement,
        answers,
    )

    question_by_id = {
        question.id: question
        for question in requirement.questions
    }

    interpretations_by_id: dict[str, AnswerInterpretation] = {}

    # --------------------------------------------------------
    # 1. Interpretar todas las respuestas registradas
    # --------------------------------------------------------

    for question in requirement.questions:
        answer = collected.get(question.id)

        if answer is None:
            continue

        if question.type != QuestionType.BOOLEAN:
            raise NotImplementedError(
                "El procesamiento de respuestas para preguntas "
                f"de tipo '{question.type.value}' todavía "
                "no está implementado."
            )

        interpretation = interpret_boolean_answer_hybrid(
            requirement,
            answer,
            llm=llm,
        )

        interpretations_by_id[question.id] = interpretation

    unresolved_statuses = {
        InterpretationStatus.INSUFFICIENT_INFORMATION,
        InterpretationStatus.NEEDS_CLARIFICATION,
        InterpretationStatus.INVALID_FORMAT,
    }

    # --------------------------------------------------------
    # 2. Resolver routing
    # --------------------------------------------------------

    routing_cache: dict[str, str] = {}

    def resolve_question_state(
        question_id: str,
        visiting: set[str] | None = None,
    ) -> str:
        """
        Devuelve:

        - active
        - skipped
        - blocked
        """

        if question_id in routing_cache:
            return routing_cache[question_id]

        if visiting is None:
            visiting = set()

        if question_id in visiting:
            raise ValueError(
                "Se detectó una dependencia circular entre preguntas "
                f"en el requisito '{requirement.id}'."
            )

        visiting = set(visiting)
        visiting.add(question_id)

        question = question_by_id[question_id]
        dependency = question.depends_on

        if dependency is None:
            routing_cache[question_id] = "active"
            return "active"

        parent_id = dependency.question_id

        parent_state = resolve_question_state(
            parent_id,
            visiting,
        )

        # Si la propia pregunta padre quedó fuera de la ruta,
        # esta pregunta tampoco puede activarse.
        if parent_state == "skipped":
            routing_cache[question_id] = "skipped"
            return "skipped"

        # Si todavía no podemos resolver la pregunta padre,
        # la pregunta dependiente queda esperando.
        if parent_state == "blocked":
            routing_cache[question_id] = "blocked"
            return "blocked"

        parent_interpretation = interpretations_by_id.get(
            parent_id
        )

        if parent_interpretation is None:
            routing_cache[question_id] = "blocked"
            return "blocked"

        if (
            parent_interpretation.status in unresolved_statuses
            or parent_interpretation.interpreted_value is None
        ):
            routing_cache[question_id] = "blocked"
            return "blocked"

        if (
            parent_interpretation.interpreted_value
            == dependency.value
        ):
            routing_cache[question_id] = "active"
            return "active"

        routing_cache[question_id] = "skipped"
        return "skipped"

    # --------------------------------------------------------
    # 3. Clasificar preguntas
    # --------------------------------------------------------

    active_question_ids: list[str] = []
    unanswered_question_ids: list[str] = []
    unresolved_question_ids: list[str] = []
    skipped_question_ids: list[str] = []
    blocked_question_ids: list[str] = []

    for question in requirement.questions:
        state = resolve_question_state(question.id)

        if state == "skipped":
            skipped_question_ids.append(question.id)
            continue

        if state == "blocked":
            blocked_question_ids.append(question.id)
            continue

        active_question_ids.append(question.id)

        interpretation = interpretations_by_id.get(
            question.id
        )

        if interpretation is None:
            unanswered_question_ids.append(question.id)
            continue

        if interpretation.status in unresolved_statuses:
            unresolved_question_ids.append(question.id)

    # Solo las interpretaciones de preguntas actualmente activas
    # participan en el procesamiento del requisito.
    interpretations = [
        interpretations_by_id[question.id]
        for question in requirement.questions
        if (
            question.id in active_question_ids
            and question.id in interpretations_by_id
        )
    ]

    return RequirementAnswerProcessingResult(
        requirement_id=requirement.id,
        interpretations=interpretations,
        active_question_ids=active_question_ids,
        unanswered_question_ids=unanswered_question_ids,
        unresolved_question_ids=unresolved_question_ids,
        skipped_question_ids=skipped_question_ids,
        blocked_question_ids=blocked_question_ids,
    )