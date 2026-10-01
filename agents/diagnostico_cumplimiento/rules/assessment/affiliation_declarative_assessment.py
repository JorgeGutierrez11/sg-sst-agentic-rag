from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    DeclarativeAssessmentStatus,
    RequirementDeclarativeAssessment,
)
from agents.diagnostico_cumplimiento.domain.requirement_applicability import (
    RequirementApplicabilityDecision,
    RequirementApplicabilityStatus,
)
from agents.diagnostico_cumplimiento.rules.routing.affiliation_question_routing import (
    AFFILIATION_REQUIREMENT_ID,
)
from agents.diagnostico_cumplimiento.rules.decision_matrix import (
    DecisionRuleValidationStatus,
    RequirementDecisionRule,
    get_decision_rule,
)

from agents.diagnostico_cumplimiento.rules.routing.affiliation_question_routing import (
    AFFILIATION_REQUIREMENT_ID,
    build_affiliation_question_routing,
)

AFFILIATION_REGIME_ID = "res0312_art3_risk_i_1_10"


def get_affiliation_decision_rule() -> RequirementDecisionRule:
    """
    Obtiene la regla de afiliación desde la matriz de decisión.

    La matriz es la única fuente de verdad sobre:
    - las preguntas requeridas;
    - las reglas propuestas;
    - el estado de validación experta.
    """

    return get_decision_rule(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        regime_id=AFFILIATION_REGIME_ID,
    )


# Se conserva este nombre porque ya es utilizado por pruebas
# y otros componentes, pero ahora deriva directamente de la matriz.
AFFILIATION_QUESTION_IDS = list(
    get_affiliation_decision_rule().required_question_ids
)


def assess_affiliation_as_declared(
    *,
    answers: list[QuestionAnswer],
    applicability: RequirementApplicabilityDecision,
) -> RequirementDeclarativeAssessment:
    """
    Construye el resultado declarativo del requisito de afiliación.

    La lógica autorizada depende del estado de validación de la
    regla registrada en la matriz de decisión.

    Mientras la regla permanezca en DRAFT, esta función no puede
    emitir:

    - complies_as_declared
    - does_not_comply_as_declared
    """

    if applicability.requirement_id != AFFILIATION_REQUIREMENT_ID:
        raise ValueError(
            "La decisión de aplicabilidad no corresponde "
            "al requisito de afiliación."
        )

    decision_rule = get_affiliation_decision_rule()

    _validate_matrix_consistency(decision_rule)

    if (
        applicability.status
        == RequirementApplicabilityStatus.NOT_APPLICABLE
    ):
        return RequirementDeclarativeAssessment(
            requirement_id=AFFILIATION_REQUIREMENT_ID,
            status=DeclarativeAssessmentStatus.NOT_APPLICABLE,
            explanation=(
                "El requisito fue determinado como no aplicable "
                "mediante una regla de aplicabilidad fundamentada."
            ),
            applicability=applicability,
        )

    if (
        applicability.status
        == RequirementApplicabilityStatus.UNDETERMINED
    ):
        return RequirementDeclarativeAssessment(
            requirement_id=AFFILIATION_REQUIREMENT_ID,
            status=(
                DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            ),
            explanation=(
                "No existe información suficiente para determinar "
                "la aplicabilidad del requisito de afiliación."
            ),
            applicability=applicability,
            missing_information=list(
                applicability.missing_information
            ),
        )

    answers_by_id = _index_affiliation_answers(
        answers,
        question_ids=decision_rule.required_question_ids,
    )

    routing = build_affiliation_question_routing(answers)

    missing_question_ids = [
        question_id
        for question_id in routing.questions_to_ask
        if question_id in decision_rule.required_question_ids
    ]

    unresolved_question_ids = [
        question_id
        for question_id, answer in answers_by_id.items()
        if not isinstance(answer.raw_answer, bool)
    ]

    negative_question_ids = [
        question_id
        for question_id, answer in answers_by_id.items()
        if answer.raw_answer is False
    ]

    supporting_question_ids = [
        question_id
        for question_id in decision_rule.required_question_ids
        if question_id in answers_by_id
    ]

    missing_information = [
        f"Falta responder: {question_id}"
        for question_id in missing_question_ids
    ]

    missing_information.extend(
        f"Respuesta no resuelta: {question_id}"
        for question_id in unresolved_question_ids
    )

    if (
        decision_rule.validation_status
        == DecisionRuleValidationStatus.DRAFT
    ):
        missing_information.append(
            "La suficiencia de las preguntas y de la regla "
            "de evaluación declarativa de afiliación está pendiente "
            "de validación por un experto en SST."
        )

        if negative_question_ids:
            explanation = (
                "La empresa realizó una o más declaraciones negativas "
                "sobre el requisito de afiliación. Estas respuestas "
                "se conservan para la evaluación, pero la matriz de "
                "decisión todavía se encuentra pendiente de "
                "validación experta."
            )

        elif missing_question_ids or unresolved_question_ids:
            explanation = (
                "La información declarada sobre afiliación todavía "
                "está incompleta o contiene respuestas no resueltas. "
                "Además, la matriz de decisión permanece pendiente "
                "de validación experta."
            )

        else:
            explanation = (
                "Las preguntas requeridas por la matriz fueron "
                "respondidas, pero la regla todavía está en estado "
                "draft y no ha sido validada para determinar un "
                "resultado de cumplimiento o incumplimiento "
                "según declaración."
            )

        return RequirementDeclarativeAssessment(
            requirement_id=AFFILIATION_REQUIREMENT_ID,
            status=(
                DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            ),
            explanation=explanation,
            applicability=applicability,
            supporting_question_ids=supporting_question_ids,
            missing_information=missing_information,
        )

    if (
        decision_rule.validation_status
        == DecisionRuleValidationStatus.EXPERT_VALIDATED
    ):
        raise RuntimeError(
            "La regla de afiliación está marcada como validada por "
            "experto, pero la lógica aprobada todavía no ha sido "
            "implementada en el motor de evaluación."
        )

    raise RuntimeError(
        "La matriz contiene un estado de validación no soportado."
    )


def _validate_matrix_consistency(
    decision_rule: RequirementDecisionRule,
) -> None:
    """
    Verifica que la regla recuperada corresponda realmente
    al requisito y régimen implementados por este evaluador.
    """

    if decision_rule.requirement_id != AFFILIATION_REQUIREMENT_ID:
        raise ValueError(
            "La matriz devolvió una regla correspondiente "
            "a otro requisito."
        )

    if decision_rule.regime_id != AFFILIATION_REGIME_ID:
        raise ValueError(
            "La matriz devolvió una regla correspondiente "
            "a otro régimen."
        )


def _index_affiliation_answers(
    answers: list[QuestionAnswer],
    *,
    question_ids: list[str],
) -> dict[str, QuestionAnswer]:
    """
    Indexa únicamente las respuestas correspondientes al requisito
    de afiliación y las contrasta con las preguntas de la matriz.
    """

    allowed_question_ids = set(question_ids)

    result: dict[str, QuestionAnswer] = {}

    for answer in answers:
        if answer.requirement_id != AFFILIATION_REQUIREMENT_ID:
            continue

        if answer.question_id not in allowed_question_ids:
            raise ValueError(
                "Se recibió una pregunta no reconocida por la "
                "matriz de decisión de afiliación: "
                f"{answer.question_id}"
            )

        if answer.question_id in result:
            raise ValueError(
                "Se recibió más de una respuesta para la pregunta "
                f"'{answer.question_id}'."
            )

        result[answer.question_id] = answer

    return result