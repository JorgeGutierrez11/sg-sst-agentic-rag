from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.question_routing import (
    QuestionRoutingDecision,
    QuestionRoutingStatus,
    QuestionRoutingTrace,
)


AFFILIATION_REQUIREMENT_ID = "res0312_art3_afiliacion_1_10"


AFFILIATION_FLOWS = {
    "health": {
        "affiliation": "q_health_affiliation",
        "support": "q_health_affiliation_support",
        "payment": "q_health_payment_support",
        "label": "salud",
    },
    "pension": {
        "affiliation": "q_pension_affiliation",
        "support": "q_pension_affiliation_support",
        "payment": "q_pension_payment_support",
        "label": "pensiones",
    },
    "occupational_risk": {
        "affiliation": "q_occupational_risk_affiliation",
        "support": "q_occupational_risk_affiliation_support",
        "payment": "q_occupational_risk_payment_support",
        "label": "riesgos laborales",
    },
}


def build_affiliation_question_routing(
    answers: list[QuestionAnswer],
) -> QuestionRoutingTrace:
    """
    Decide qué preguntas auxiliares de afiliación deben formularse.

    La traza distingue entre:

    - preguntas todavía pendientes de formular;
    - preguntas que ya fueron respondidas;
    - preguntas omitidas por una dependencia lógica.

    Este enrutamiento no determina:
    - aplicabilidad normativa;
    - obligaciones de afiliación o pago;
    - cumplimiento o incumplimiento;
    - excepciones según modalidad de vinculación.
    """

    answers_by_id = {
        answer.question_id: answer
        for answer in answers
        if answer.requirement_id == AFFILIATION_REQUIREMENT_ID
    }

    decisions: list[QuestionRoutingDecision] = []

    for flow_id, flow in AFFILIATION_FLOWS.items():
        affiliation_id = flow["affiliation"]
        support_id = flow["support"]
        payment_id = flow["payment"]
        label = flow["label"]

        affiliation_answer = answers_by_id.get(affiliation_id)

        if affiliation_answer is None:
            decisions.append(
                QuestionRoutingDecision(
                    question_id=affiliation_id,
                    status=QuestionRoutingStatus.ASK,
                    rule_id=f"{flow_id}_affiliation_entry",
                    reason=(
                        "Se requiere conocer la situación declarada "
                        f"de afiliación al sistema de {label}."
                    ),
                )
            )

            decisions.extend(
                _omit_dependent_questions(
                    flow_id=flow_id,
                    label=label,
                    support_id=support_id,
                    payment_id=payment_id,
                    trigger=f"{affiliation_id}=unanswered",
                    reason=(
                        "Primero debe conocerse la respuesta sobre "
                        f"la afiliación al sistema de {label}."
                    ),
                )
            )

            continue

        decisions.append(
            QuestionRoutingDecision(
                question_id=affiliation_id,
                status=QuestionRoutingStatus.ANSWERED,
                rule_id=f"{flow_id}_affiliation_answered",
                triggered_by=f"{affiliation_id}=answered",
                reason=(
                    "La pregunta sobre afiliación al sistema de "
                    f"{label} ya fue respondida."
                ),
            )
        )

        raw_answer = affiliation_answer.raw_answer

        if raw_answer is True:
            decisions.extend(
                _route_after_affirmative_affiliation(
                    flow_id=flow_id,
                    label=label,
                    affiliation_id=affiliation_id,
                    support_id=support_id,
                    payment_id=payment_id,
                    answers_by_id=answers_by_id,
                )
            )

            continue

        if raw_answer is False:
            decisions.extend(
                _omit_dependent_questions(
                    flow_id=flow_id,
                    label=label,
                    support_id=support_id,
                    payment_id=payment_id,
                    trigger=f"{affiliation_id}=False",
                    reason=(
                        "La empresa declaró que no existe la afiliación "
                        f"consultada al sistema de {label}; por ello "
                        "no se solicitan en este punto soportes de una "
                        "afiliación declarada como inexistente."
                    ),
                )
            )

            continue

        decisions.extend(
            _omit_dependent_questions(
                flow_id=flow_id,
                label=label,
                support_id=support_id,
                payment_id=payment_id,
                trigger=f"{affiliation_id}=unresolved",
                reason=(
                    "La respuesta sobre la afiliación al sistema de "
                    f"{label} existe, pero todavía no puede interpretarse "
                    "como una respuesta afirmativa o negativa para "
                    "habilitar las preguntas dependientes."
                ),
            )
        )

    return QuestionRoutingTrace(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        decisions=decisions,
    )


def _route_after_affirmative_affiliation(
    *,
    flow_id: str,
    label: str,
    affiliation_id: str,
    support_id: str,
    payment_id: str,
    answers_by_id: dict[str, QuestionAnswer],
) -> list[QuestionRoutingDecision]:
    """
    Enruta las preguntas dependientes cuando la afiliación
    fue declarada afirmativamente.

    Si una pregunta dependiente ya tiene respuesta, se registra
    como ANSWERED en lugar de volver a formularla.
    """

    decisions: list[QuestionRoutingDecision] = []

    dependent_questions = [
        (
            support_id,
            f"{flow_id}_support_after_affiliation",
            (
                "La empresa declaró que existe la afiliación "
                f"al sistema de {label}; se consulta la "
                "disponibilidad del soporte correspondiente."
            ),
        ),
        (
            payment_id,
            f"{flow_id}_payment_after_affiliation",
            (
                "La empresa declaró que existe la afiliación "
                f"al sistema de {label}; se consulta la "
                "disponibilidad del comprobante de pago."
            ),
        ),
    ]

    for question_id, rule_id, ask_reason in dependent_questions:
        if question_id in answers_by_id:
            decisions.append(
                QuestionRoutingDecision(
                    question_id=question_id,
                    status=QuestionRoutingStatus.ANSWERED,
                    rule_id=f"{rule_id}_answered",
                    triggered_by=f"{question_id}=answered",
                    reason=(
                        "La pregunta dependiente ya fue respondida "
                        "y permanece registrada en la traza."
                    ),
                )
            )
        else:
            decisions.append(
                QuestionRoutingDecision(
                    question_id=question_id,
                    status=QuestionRoutingStatus.ASK,
                    rule_id=rule_id,
                    triggered_by=f"{affiliation_id}=True",
                    reason=ask_reason,
                )
            )

    return decisions


def _omit_dependent_questions(
    *,
    flow_id: str,
    label: str,
    support_id: str,
    payment_id: str,
    trigger: str,
    reason: str,
) -> list[QuestionRoutingDecision]:
    """
    Construye las decisiones de omisión para las preguntas
    dependientes de una afiliación.
    """

    return [
        QuestionRoutingDecision(
            question_id=support_id,
            status=QuestionRoutingStatus.OMIT,
            rule_id=f"{flow_id}_support_dependency",
            triggered_by=trigger,
            reason=reason,
        ),
        QuestionRoutingDecision(
            question_id=payment_id,
            status=QuestionRoutingStatus.OMIT,
            rule_id=f"{flow_id}_payment_dependency",
            triggered_by=trigger,
            reason=reason,
        ),
    ]