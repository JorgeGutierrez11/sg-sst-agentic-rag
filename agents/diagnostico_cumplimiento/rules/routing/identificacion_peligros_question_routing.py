from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.question_routing import (
    QuestionRoutingDecision,
    QuestionRoutingStatus,
    QuestionRoutingTrace,
)


IDENTIFICACION_PELIGROS_REQUIREMENT_ID = (
    "res0312_art3_identificacion_peligros_1_10"
)

HAZARD_IDENTIFICATION_ID = "q_hazard_identification"
RISK_EVALUATION_ID = "q_risk_evaluation"
RISK_VALUATION_ID = "q_risk_valuation"
ARL_ACCOMPANIMENT_ID = "q_arl_accompaniment"
RISK_DOCUMENT_ID = "q_risk_document_available"
ARL_SUPPORT_ID = "q_arl_support_available"


def build_identificacion_peligros_question_routing(
    answers: list[QuestionAnswer],
) -> QuestionRoutingTrace:
    """
    Decide qué preguntas auxiliares deben formularse para
    identificación de peligros, evaluación y valoración de riesgos.

    El routing únicamente gestiona dependencias entre preguntas.
    No determina cumplimiento normativo.
    """

    answers_by_id = {
        answer.question_id: answer
        for answer in answers
        if answer.requirement_id
        == IDENTIFICACION_PELIGROS_REQUIREMENT_ID
    }

    decisions: list[QuestionRoutingDecision] = []

    hazard_answer = answers_by_id.get(
        HAZARD_IDENTIFICATION_ID
    )

    # 1. Identificación de peligros: pregunta de entrada.
    if hazard_answer is None:
        decisions.append(
            _ask(
                HAZARD_IDENTIFICATION_ID,
                "hazard_identification_entry",
                (
                    "Primero se requiere conocer si la empresa "
                    "ha identificado los peligros presentes."
                ),
            )
        )

        decisions.extend(
            _omit_many(
                [
                    RISK_EVALUATION_ID,
                    RISK_VALUATION_ID,
                    ARL_ACCOMPANIMENT_ID,
                    RISK_DOCUMENT_ID,
                    ARL_SUPPORT_ID,
                ],
                trigger="q_hazard_identification=unanswered",
                reason=(
                    "Primero debe conocerse si la empresa ha "
                    "realizado la identificación de peligros."
                ),
            )
        )

        return _trace(decisions)

    decisions.append(
        _answered(
            HAZARD_IDENTIFICATION_ID,
            "hazard_identification_answered",
        )
    )

    if hazard_answer.raw_answer is False:
        decisions.extend(
            _omit_many(
                [
                    RISK_EVALUATION_ID,
                    RISK_VALUATION_ID,
                    ARL_ACCOMPANIMENT_ID,
                    RISK_DOCUMENT_ID,
                    ARL_SUPPORT_ID,
                ],
                trigger="q_hazard_identification=False",
                reason=(
                    "La empresa declaró que no ha realizado la "
                    "identificación de peligros; se omiten las "
                    "preguntas dependientes de dicho proceso."
                ),
            )
        )

        return _trace(decisions)

    if hazard_answer.raw_answer is not True:
        decisions.extend(
            _omit_many(
                [
                    RISK_EVALUATION_ID,
                    RISK_VALUATION_ID,
                    ARL_ACCOMPANIMENT_ID,
                    RISK_DOCUMENT_ID,
                    ARL_SUPPORT_ID,
                ],
                trigger="q_hazard_identification=unresolved",
                reason=(
                    "La respuesta sobre identificación de peligros "
                    "todavía no puede interpretarse como afirmativa "
                    "o negativa."
                ),
            )
        )

        return _trace(decisions)

    # 2. Con peligros identificados, preguntar evaluación.
    evaluation_answer = answers_by_id.get(
        RISK_EVALUATION_ID
    )

    if evaluation_answer is None:
        decisions.append(
            _ask(
                RISK_EVALUATION_ID,
                "risk_evaluation_after_identification",
                (
                    "La empresa declaró que identificó los peligros; "
                    "se requiere conocer si evaluó los riesgos."
                ),
                trigger="q_hazard_identification=True",
            )
        )

        decisions.extend(
            _omit_many(
                [
                    RISK_VALUATION_ID,
                    RISK_DOCUMENT_ID,
                ],
                trigger="q_risk_evaluation=unanswered",
                reason=(
                    "Primero debe conocerse si los riesgos fueron "
                    "evaluados antes de consultar su valoración "
                    "y el documento integral."
                ),
            )
        )
    else:
        decisions.append(
            _answered(
                RISK_EVALUATION_ID,
                "risk_evaluation_answered",
            )
        )

        _route_risk_valuation_and_document(
            decisions=decisions,
            answers_by_id=answers_by_id,
            evaluation_answer=evaluation_answer,
        )

    # 3. Acompañamiento ARL: rama independiente una vez
    # existe identificación de peligros.
    _route_arl_branch(
        decisions=decisions,
        answers_by_id=answers_by_id,
    )

    return _trace(decisions)


def _route_risk_valuation_and_document(
    *,
    decisions: list[QuestionRoutingDecision],
    answers_by_id: dict[str, QuestionAnswer],
    evaluation_answer: QuestionAnswer,
) -> None:
    if evaluation_answer.raw_answer is False:
        decisions.extend(
            _omit_many(
                [
                    RISK_VALUATION_ID,
                    RISK_DOCUMENT_ID,
                ],
                trigger="q_risk_evaluation=False",
                reason=(
                    "La empresa declaró que no ha realizado la "
                    "evaluación de riesgos; se omiten las preguntas "
                    "dependientes de esa etapa."
                ),
            )
        )
        return

    if evaluation_answer.raw_answer is not True:
        decisions.extend(
            _omit_many(
                [
                    RISK_VALUATION_ID,
                    RISK_DOCUMENT_ID,
                ],
                trigger="q_risk_evaluation=unresolved",
                reason=(
                    "La respuesta sobre evaluación de riesgos "
                    "todavía no está resuelta."
                ),
            )
        )
        return

    valuation_answer = answers_by_id.get(
        RISK_VALUATION_ID
    )

    if valuation_answer is None:
        decisions.append(
            _ask(
                RISK_VALUATION_ID,
                "risk_valuation_after_evaluation",
                (
                    "La empresa declaró que evaluó los riesgos; "
                    "se requiere conocer si realizó su valoración."
                ),
                trigger="q_risk_evaluation=True",
            )
        )

        decisions.extend(
            _omit_many(
                [RISK_DOCUMENT_ID],
                trigger="q_risk_valuation=unanswered",
                reason=(
                    "Primero debe conocerse si se realizó la "
                    "valoración de riesgos antes de consultar el "
                    "documento integral del proceso."
                ),
            )
        )
        return

    decisions.append(
        _answered(
            RISK_VALUATION_ID,
            "risk_valuation_answered",
        )
    )

    if valuation_answer.raw_answer is True:
        _route_single_dependent(
            decisions=decisions,
            answers_by_id=answers_by_id,
            question_id=RISK_DOCUMENT_ID,
            rule_id="risk_document_after_valuation",
            trigger="q_risk_valuation=True",
            reason=(
                "La empresa declaró que realizó identificación, "
                "evaluación y valoración; se consulta la "
                "disponibilidad del documento correspondiente."
            ),
        )

    else:
        decisions.extend(
            _omit_many(
                [RISK_DOCUMENT_ID],
                trigger=(
                    "q_risk_valuation=False"
                    if valuation_answer.raw_answer is False
                    else "q_risk_valuation=unresolved"
                ),
                reason=(
                    "No se consulta el documento integral mientras "
                    "la valoración de riesgos no esté confirmada."
                ),
            )
        )


def _route_arl_branch(
    *,
    decisions: list[QuestionRoutingDecision],
    answers_by_id: dict[str, QuestionAnswer],
) -> None:
    arl_answer = answers_by_id.get(
        ARL_ACCOMPANIMENT_ID
    )

    if arl_answer is None:
        decisions.append(
            _ask(
                ARL_ACCOMPANIMENT_ID,
                "arl_accompaniment_after_identification",
                (
                    "Se requiere conocer si la ARL acompañó "
                    "el proceso de identificación y evaluación "
                    "de riesgos."
                ),
                trigger="q_hazard_identification=True",
            )
        )

        decisions.extend(
            _omit_many(
                [ARL_SUPPORT_ID],
                trigger="q_arl_accompaniment=unanswered",
                reason=(
                    "Primero debe conocerse si existió "
                    "acompañamiento de la ARL."
                ),
            )
        )
        return

    decisions.append(
        _answered(
            ARL_ACCOMPANIMENT_ID,
            "arl_accompaniment_answered",
        )
    )

    if arl_answer.raw_answer is True:
        _route_single_dependent(
            decisions=decisions,
            answers_by_id=answers_by_id,
            question_id=ARL_SUPPORT_ID,
            rule_id="arl_support_after_accompaniment",
            trigger="q_arl_accompaniment=True",
            reason=(
                "La empresa declaró que contó con acompañamiento "
                "de la ARL; se consulta la constancia correspondiente."
            ),
        )
    else:
        decisions.extend(
            _omit_many(
                [ARL_SUPPORT_ID],
                trigger=(
                    "q_arl_accompaniment=False"
                    if arl_answer.raw_answer is False
                    else "q_arl_accompaniment=unresolved"
                ),
                reason=(
                    "No se consulta una constancia mientras el "
                    "acompañamiento de la ARL no esté confirmado."
                ),
            )
        )


def _route_single_dependent(
    *,
    decisions: list[QuestionRoutingDecision],
    answers_by_id: dict[str, QuestionAnswer],
    question_id: str,
    rule_id: str,
    trigger: str,
    reason: str,
) -> None:
    if question_id in answers_by_id:
        decisions.append(
            _answered(
                question_id,
                f"{rule_id}_answered",
            )
        )
    else:
        decisions.append(
            _ask(
                question_id,
                rule_id,
                reason,
                trigger=trigger,
            )
        )


def _ask(
    question_id: str,
    rule_id: str,
    reason: str,
    trigger: str | None = None,
) -> QuestionRoutingDecision:
    return QuestionRoutingDecision(
        question_id=question_id,
        status=QuestionRoutingStatus.ASK,
        rule_id=rule_id,
        triggered_by=trigger,
        reason=reason,
    )


def _answered(
    question_id: str,
    rule_id: str,
) -> QuestionRoutingDecision:
    return QuestionRoutingDecision(
        question_id=question_id,
        status=QuestionRoutingStatus.ANSWERED,
        rule_id=rule_id,
        triggered_by=f"{question_id}=answered",
        reason="La pregunta ya fue respondida.",
    )


def _omit_many(
    question_ids: list[str],
    *,
    trigger: str,
    reason: str,
) -> list[QuestionRoutingDecision]:
    return [
        QuestionRoutingDecision(
            question_id=question_id,
            status=QuestionRoutingStatus.OMIT,
            rule_id=f"{question_id}_dependency",
            triggered_by=trigger,
            reason=reason,
        )
        for question_id in question_ids
    ]


def _trace(
    decisions: list[QuestionRoutingDecision],
) -> QuestionRoutingTrace:
    return QuestionRoutingTrace(
        requirement_id=IDENTIFICACION_PELIGROS_REQUIREMENT_ID,
        decisions=decisions,
    )