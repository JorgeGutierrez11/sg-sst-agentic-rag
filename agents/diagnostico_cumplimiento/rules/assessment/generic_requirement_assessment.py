from __future__ import annotations

from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    DeclarativeAssessmentStatus,
    RequirementDeclarativeAssessment,
)
from agents.diagnostico_cumplimiento.domain.interpretation import (
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.domain.requirement_applicability import (
    RequirementApplicabilityDecision,
    RequirementApplicabilityStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_snapshot import (
    QuestionRoutingState,
    RequirementSnapshot,
)


SCREENING_ROLES = {
    "applicability_screening",
    "event_screening",
}


UNRESOLVED_STATUSES = {
    InterpretationStatus.INSUFFICIENT_INFORMATION,
    InterpretationStatus.NEEDS_CLARIFICATION,
    InterpretationStatus.INVALID_FORMAT,
}


def determine_requirement_applicability(
    requirement: RequirementSnapshot,
) -> RequirementApplicabilityDecision:
    """
    Determina la aplicabilidad declarativa de un requisito.

    La selección inicial del paquete normativo ya determinó que el
    requisito pertenece al universo aplicable al perfil empresarial.

    Esta función únicamente resuelve excepciones explícitas definidas
    en ``requirement.applicability``.

    No evalúa cumplimiento.
    """

    applicability = requirement.applicability

    normative_basis = _build_normative_basis(requirement)

    # --------------------------------------------------------
    # ALWAYS
    # --------------------------------------------------------

    if applicability.mode == "always":
        return RequirementApplicabilityDecision(
            requirement_id=requirement.requirement_id,
            status=RequirementApplicabilityStatus.APPLICABLE,
            rule_id="catalog_requirement_always_applicable",
            reason=(
                "El requisito pertenece al paquete normativo "
                "seleccionado y no define una condición particular "
                "de exclusión."
            ),
            normative_basis=normative_basis,
        )

    # --------------------------------------------------------
    # EVENT DEPENDENT
    #
    # La ausencia del evento NO implica No aplica.
    # --------------------------------------------------------

    if applicability.mode == "event_dependent":
        return RequirementApplicabilityDecision(
            requirement_id=requirement.requirement_id,
            status=RequirementApplicabilityStatus.APPLICABLE,
            rule_id="catalog_event_dependent_requirement",
            reason=(
                "El requisito pertenece al paquete normativo "
                "seleccionado. Su evaluación puede depender de un "
                "evento o antecedente, pero la ausencia del evento "
                "no permite clasificarlo automáticamente como "
                "'No aplica'."
            ),
            normative_basis=normative_basis,
        )

    # --------------------------------------------------------
    # CONDITIONAL
    # --------------------------------------------------------

    if applicability.mode == "conditional":
        screening_question_id = (
            applicability.screening_question_id
        )

        if screening_question_id is None:
            raise ValueError(
                "Un requisito condicional debe definir "
                "screening_question_id."
            )

        screening_question = next(
            (
                question
                for question in requirement.questions
                if question.question_id == screening_question_id
            ),
            None,
        )

        if screening_question is None:
            raise ValueError(
                "La pregunta de aplicabilidad configurada no existe "
                f"en el requisito '{requirement.requirement_id}': "
                f"'{screening_question_id}'."
            )

        interpretation = screening_question.interpretation

        if (
            interpretation is None
            or interpretation.status in UNRESOLVED_STATUSES
            or interpretation.interpreted_value is None
        ):
            return RequirementApplicabilityDecision(
                requirement_id=requirement.requirement_id,
                status=RequirementApplicabilityStatus.UNDETERMINED,
                rule_id="conditional_applicability_unresolved",
                reason=(
                    "La información disponible todavía no permite "
                    "resolver la condición particular de aplicabilidad "
                    "del requisito."
                ),
                normative_basis=None,
                triggered_by=[screening_question_id],
                missing_information=[
                    screening_question.text,
                ],
            )

        interpreted_value = (
            interpretation.interpreted_value
        )

        if (
            applicability.not_applicable_allowed
            and applicability.not_applicable_when is not None
            and interpreted_value
            == applicability.not_applicable_when
        ):
            return RequirementApplicabilityDecision(
                requirement_id=requirement.requirement_id,
                status=(
                    RequirementApplicabilityStatus.NOT_APPLICABLE
                ),
                rule_id="catalog_conditional_not_applicable",
                reason=(
                    applicability.not_applicable_reason
                    or (
                        "La condición normativa configurada para "
                        "este requisito permite determinar que no "
                        "aplica al caso declarado."
                    )
                ),
                normative_basis=normative_basis,
                triggered_by=[screening_question_id],
            )

        if (
            applicability.applies_when is not None
            and interpreted_value == applicability.applies_when
        ):
            return RequirementApplicabilityDecision(
                requirement_id=requirement.requirement_id,
                status=RequirementApplicabilityStatus.APPLICABLE,
                rule_id="catalog_conditional_applicable",
                reason=(
                    "La condición declarada coincide con la regla "
                    "de aplicabilidad definida para el requisito."
                ),
                normative_basis=normative_basis,
                triggered_by=[screening_question_id],
            )

        # Si solo se definió cuándo NO aplica, cualquier otro valor
        # resuelto mantiene el requisito como aplicable.
        if (
            applicability.applies_when is None
            and applicability.not_applicable_when is not None
            and interpreted_value
            != applicability.not_applicable_when
        ):
            return RequirementApplicabilityDecision(
                requirement_id=requirement.requirement_id,
                status=RequirementApplicabilityStatus.APPLICABLE,
                rule_id="catalog_conditional_applicable",
                reason=(
                    "La condición declarada no coincide con la "
                    "excepción normativa configurada para excluir "
                    "el requisito."
                ),
                normative_basis=normative_basis,
                triggered_by=[screening_question_id],
            )

        return RequirementApplicabilityDecision(
            requirement_id=requirement.requirement_id,
            status=RequirementApplicabilityStatus.UNDETERMINED,
            rule_id="conditional_applicability_unresolved",
            reason=(
                "La respuesta obtenida no coincide de forma suficiente "
                "con las reglas de aplicabilidad configuradas para "
                "el requisito."
            ),
            normative_basis=None,
            triggered_by=[screening_question_id],
            missing_information=[
                screening_question.text,
            ],
        )

    raise ValueError(
        "Modo de aplicabilidad no soportado: "
        f"'{applicability.mode}'."
    )


def assess_requirement_as_declared(
    requirement: RequirementSnapshot,
    applicability: RequirementApplicabilityDecision | None = None,
) -> RequirementDeclarativeAssessment:
    """
    Evalúa genéricamente un requisito a partir de las declaraciones.

    Las preguntas son mecanismos de recopilación de información.
    La unidad evaluada continúa siendo el requisito normativo.

    No realiza verificación documental.
    """

    if applicability is None:
        applicability = determine_requirement_applicability(
            requirement
        )

    # --------------------------------------------------------
    # NO APLICA
    # --------------------------------------------------------

    if (
        applicability.status
        == RequirementApplicabilityStatus.NOT_APPLICABLE
    ):
        return RequirementDeclarativeAssessment(
            requirement_id=requirement.requirement_id,
            status=DeclarativeAssessmentStatus.NOT_APPLICABLE,
            explanation=(
                "El requisito fue determinado como no aplicable "
                "de acuerdo con la condición normativa configurada "
                "y la información declarada."
            ),
            applicability=applicability,
            supporting_question_ids=(
                applicability.triggered_by
            ),
            requires_expert_validation=True,
        )

    # --------------------------------------------------------
    # APLICABILIDAD NO RESUELTA
    # --------------------------------------------------------

    if (
        applicability.status
        == RequirementApplicabilityStatus.UNDETERMINED
    ):
        return RequirementDeclarativeAssessment(
            requirement_id=requirement.requirement_id,
            status=(
                DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            ),
            explanation=(
                "Todavía no existe información suficiente para "
                "determinar la aplicabilidad del requisito."
            ),
            applicability=applicability,
            supporting_question_ids=(
                applicability.triggered_by
            ),
            missing_information=(
                applicability.missing_information
            ),
            requires_expert_validation=True,
        )

    # --------------------------------------------------------
    # PREGUNTAS EVALUATIVAS ACTIVAS
    # --------------------------------------------------------

    evaluative_questions = [
        question
        for question in requirement.questions
        if (
            question.role not in SCREENING_ROLES
            and question.routing_state
            == QuestionRoutingState.ACTIVE
        )
    ]

    blocked_evaluative_questions = [
        question
        for question in requirement.questions
        if (
            question.role not in SCREENING_ROLES
            and question.routing_state
            == QuestionRoutingState.BLOCKED
        )
    ]

    missing_information: list[str] = []

    negative_question_ids: list[str] = []

    supporting_question_ids: list[str] = []

    for question in evaluative_questions:
        interpretation = question.interpretation

        if interpretation is None:
            missing_information.append(
                question.text
            )
            continue

        if interpretation.status in UNRESOLVED_STATUSES:
            missing_information.append(
                question.text
            )
            continue

        supporting_question_ids.append(
            question.question_id
        )

        if interpretation.status == InterpretationStatus.NEGATIVE:
            negative_question_ids.append(
                question.question_id
            )

    for question in blocked_evaluative_questions:
        missing_information.append(
            question.text
        )

    # --------------------------------------------------------
    # INFORMACIÓN INSUFICIENTE
    # --------------------------------------------------------

    if missing_information:
        return RequirementDeclarativeAssessment(
            requirement_id=requirement.requirement_id,
            status=(
                DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            ),
            explanation=(
                "No existe información declarada suficiente para "
                "evaluar completamente el requisito."
            ),
            applicability=applicability,
            supporting_question_ids=supporting_question_ids,
            missing_information=_unique_preserving_order(
                missing_information
            ),
            requires_expert_validation=True,
        )

    # Protección para no declarar cumplimiento cuando el routing
    # dejó al requisito sin ninguna pregunta evaluativa.
    if not evaluative_questions:
        return RequirementDeclarativeAssessment(
            requirement_id=requirement.requirement_id,
            status=(
                DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            ),
            explanation=(
                "El cuestionario no produjo preguntas evaluativas "
                "activas suficientes para emitir una conclusión "
                "declarativa sobre este requisito."
            ),
            applicability=applicability,
            missing_information=[
                (
                    "Se requiere información adicional para evaluar "
                    "el requisito."
                )
            ],
            requires_expert_validation=True,
        )

    # --------------------------------------------------------
    # DECLARACIÓN NEGATIVA
    # --------------------------------------------------------

    if negative_question_ids:
        return RequirementDeclarativeAssessment(
            requirement_id=requirement.requirement_id,
            status=(
                DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED
            ),
            explanation=(
                "Al menos una de las condiciones evaluativas "
                "derivadas del requisito fue declarada de forma "
                "negativa."
            ),
            applicability=applicability,
            supporting_question_ids=supporting_question_ids,
            requires_expert_validation=True,
        )

    # --------------------------------------------------------
    # TODAS LAS PREGUNTAS EVALUATIVAS ACTIVAS SON AFIRMATIVAS
    # --------------------------------------------------------

    return RequirementDeclarativeAssessment(
        requirement_id=requirement.requirement_id,
        status=DeclarativeAssessmentStatus.COMPLIES_AS_DECLARED,
        explanation=(
            "Todas las preguntas evaluativas activas del requisito "
            "fueron respondidas afirmativamente según la información "
            "declarada por la empresa."
        ),
        applicability=applicability,
        supporting_question_ids=supporting_question_ids,
        requires_expert_validation=True,
    )


def _build_normative_basis(
    requirement: RequirementSnapshot,
) -> str:
    source = requirement.source

    basis = (
        f"{source.norm}, "
        f"artículo {source.requirements_article}"
    )

    if requirement.official_item_id:
        basis += (
            f", ítem {requirement.official_item_id}"
        )

    return basis + "."


def _unique_preserving_order(
    values: list[str],
) -> list[str]:
    return list(
        dict.fromkeys(values)
    )