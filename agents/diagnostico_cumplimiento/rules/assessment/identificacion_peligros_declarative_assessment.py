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
from agents.diagnostico_cumplimiento.rules.decision_matrix import (
    DecisionRuleValidationStatus,
    RequirementDecisionRule,
    get_decision_rule,
)
from agents.diagnostico_cumplimiento.rules.routing.identificacion_peligros_question_routing import (
    IDENTIFICACION_PELIGROS_REQUIREMENT_ID,
    build_identificacion_peligros_question_routing,
)


IDENTIFICACION_PELIGROS_REGIME_ID = (
    "res0312_art3_risk_i_1_10"
)


def get_identificacion_peligros_decision_rule(
) -> RequirementDecisionRule:
    return get_decision_rule(
        requirement_id=IDENTIFICACION_PELIGROS_REQUIREMENT_ID,
        regime_id=IDENTIFICACION_PELIGROS_REGIME_ID,
    )


IDENTIFICACION_PELIGROS_QUESTION_IDS = list(
    get_identificacion_peligros_decision_rule().required_question_ids
)


def assess_identificacion_peligros_as_declared(
    *,
    answers: list[QuestionAnswer],
    applicability: RequirementApplicabilityDecision,
) -> RequirementDeclarativeAssessment:
    """
    Construye el resultado declarativo del requisito de
    identificación de peligros, evaluación y valoración
    de riesgos.

    Mientras la regla permanezca en DRAFT no emite
    cumplimiento o incumplimiento según declaración.
    """

    if (
        applicability.requirement_id
        != IDENTIFICACION_PELIGROS_REQUIREMENT_ID
    ):
        raise ValueError(
            "La decisión de aplicabilidad no corresponde "
            "al requisito de identificación de peligros."
        )

    decision_rule = (
        get_identificacion_peligros_decision_rule()
    )

    _validate_matrix_consistency(
        decision_rule
    )

    if (
        applicability.status
        == RequirementApplicabilityStatus.NOT_APPLICABLE
    ):
        return RequirementDeclarativeAssessment(
            requirement_id=(
                IDENTIFICACION_PELIGROS_REQUIREMENT_ID
            ),
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
            requirement_id=(
                IDENTIFICACION_PELIGROS_REQUIREMENT_ID
            ),
            status=(
                DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            ),
            explanation=(
                "No existe información suficiente para determinar "
                "la aplicabilidad del requisito de identificación "
                "de peligros, evaluación y valoración de riesgos."
            ),
            applicability=applicability,
            missing_information=list(
                applicability.missing_information
            ),
        )

    answers_by_id = _index_answers(
        answers,
        question_ids=decision_rule.required_question_ids,
    )

    routing = (
        build_identificacion_peligros_question_routing(
            answers
        )
    )

    missing_question_ids = [
        question_id
        for question_id in routing.questions_to_ask
        if question_id
        in decision_rule.required_question_ids
    ]

    unresolved_question_ids = [
        question_id
        for question_id, answer in answers_by_id.items()
        if not isinstance(
            answer.raw_answer,
            bool,
        )
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
            "de evaluación declarativa de identificación de "
            "peligros, evaluación y valoración de riesgos está "
            "pendiente de validación por un experto en SST."
        )

        if negative_question_ids:
            explanation = (
                "La empresa realizó una o más declaraciones "
                "negativas relacionadas con la identificación "
                "de peligros, evaluación o valoración de riesgos. "
                "Estas respuestas se conservan para la evaluación, "
                "pero la matriz de decisión todavía se encuentra "
                "pendiente de validación experta."
            )

        elif missing_question_ids or unresolved_question_ids:
            explanation = (
                "La información declarada sobre identificación "
                "de peligros, evaluación y valoración de riesgos "
                "todavía está incompleta o contiene respuestas "
                "no resueltas. Además, la matriz permanece "
                "pendiente de validación experta."
            )

        else:
            explanation = (
                "Las preguntas requeridas por la matriz para "
                "identificación de peligros, evaluación y "
                "valoración de riesgos fueron respondidas, pero "
                "la regla todavía está en estado draft y no ha "
                "sido validada para determinar un resultado de "
                "cumplimiento o incumplimiento según declaración."
            )

        return RequirementDeclarativeAssessment(
            requirement_id=(
                IDENTIFICACION_PELIGROS_REQUIREMENT_ID
            ),
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
            "La regla de identificación de peligros está marcada "
            "como validada por experto, pero la lógica aprobada "
            "todavía no ha sido implementada en el motor."
        )

    raise RuntimeError(
        "La matriz contiene un estado de validación no soportado."
    )


def _validate_matrix_consistency(
    decision_rule: RequirementDecisionRule,
) -> None:
    if (
        decision_rule.requirement_id
        != IDENTIFICACION_PELIGROS_REQUIREMENT_ID
    ):
        raise ValueError(
            "La matriz devolvió una regla correspondiente "
            "a otro requisito."
        )

    if (
        decision_rule.regime_id
        != IDENTIFICACION_PELIGROS_REGIME_ID
    ):
        raise ValueError(
            "La matriz devolvió una regla correspondiente "
            "a otro régimen."
        )


def _index_answers(
    answers: list[QuestionAnswer],
    *,
    question_ids: list[str],
) -> dict[str, QuestionAnswer]:
    allowed_question_ids = set(
        question_ids
    )

    result: dict[str, QuestionAnswer] = {}

    for answer in answers:
        if (
            answer.requirement_id
            != IDENTIFICACION_PELIGROS_REQUIREMENT_ID
        ):
            continue

        if answer.question_id not in allowed_question_ids:
            raise ValueError(
                "Se recibió una pregunta no reconocida por la "
                "matriz de identificación de peligros: "
                f"{answer.question_id}"
            )

        if answer.question_id in result:
            raise ValueError(
                "Se recibió más de una respuesta para la pregunta "
                f"'{answer.question_id}'."
            )

        result[answer.question_id] = answer

    return result