from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.question_routing import (
    QuestionRoutingDecision,
    QuestionRoutingStatus,
    QuestionRoutingTrace,
)


MEDIDAS_PREVENCION_CONTROL_REQUIREMENT_ID = (
    "res0312_art3_medidas_prevencion_control_1_10"
)

MEASURES_EXECUTION_ID = "q_prevention_measures_execution"

MEASURES_DEPENDENT_IDS = [
    "q_prevention_measures_risk_based",
    "q_prevention_measures_support",
]


def build_medidas_prevencion_control_question_routing(
    answers: list[QuestionAnswer],
) -> QuestionRoutingTrace:
    """
    Decide qué preguntas auxiliares deben formularse sobre
    medidas de prevención y control.

    La ejecución de medidas funciona como pregunta de entrada.

    Este routing no determina cumplimiento normativo.
    """

    answers_by_id = {
        answer.question_id: answer
        for answer in answers
        if answer.requirement_id
        == MEDIDAS_PREVENCION_CONTROL_REQUIREMENT_ID
    }

    decisions: list[QuestionRoutingDecision] = []

    execution_answer = answers_by_id.get(
        MEASURES_EXECUTION_ID
    )

    if execution_answer is None:
        decisions.append(
            QuestionRoutingDecision(
                question_id=MEASURES_EXECUTION_ID,
                status=QuestionRoutingStatus.ASK,
                rule_id="prevention_measures_execution_entry",
                reason=(
                    "Primero se requiere conocer si la empresa "
                    "ha ejecutado medidas de prevención y control."
                ),
            )
        )

        decisions.extend(
            _omit_dependent_questions(
                trigger=(
                    "q_prevention_measures_execution=unanswered"
                ),
                reason=(
                    "Primero debe conocerse si existen medidas "
                    "de prevención y control ejecutadas."
                ),
            )
        )

        return _trace(decisions)

    decisions.append(
        QuestionRoutingDecision(
            question_id=MEASURES_EXECUTION_ID,
            status=QuestionRoutingStatus.ANSWERED,
            rule_id="prevention_measures_execution_answered",
            triggered_by=(
                "q_prevention_measures_execution=answered"
            ),
            reason=(
                "La pregunta sobre ejecución de medidas "
                "ya fue respondida."
            ),
        )
    )

    if execution_answer.raw_answer is False:
        decisions.extend(
            _omit_dependent_questions(
                trigger=(
                    "q_prevention_measures_execution=False"
                ),
                reason=(
                    "La empresa declaró que no ha ejecutado "
                    "medidas de prevención y control; por ello "
                    "no se consultan características ni soportes "
                    "de medidas declaradas como no ejecutadas."
                ),
            )
        )

        return _trace(decisions)

    if execution_answer.raw_answer is not True:
        decisions.extend(
            _omit_dependent_questions(
                trigger=(
                    "q_prevention_measures_execution=unresolved"
                ),
                reason=(
                    "La respuesta sobre ejecución de medidas "
                    "todavía no puede interpretarse como "
                    "afirmativa o negativa."
                ),
            )
        )

        return _trace(decisions)

    for question_id in MEASURES_DEPENDENT_IDS:
        if question_id in answers_by_id:
            decisions.append(
                QuestionRoutingDecision(
                    question_id=question_id,
                    status=QuestionRoutingStatus.ANSWERED,
                    rule_id=f"{question_id}_answered",
                    triggered_by=f"{question_id}=answered",
                    reason=(
                        "La pregunta dependiente ya fue respondida."
                    ),
                )
            )
        else:
            decisions.append(
                QuestionRoutingDecision(
                    question_id=question_id,
                    status=QuestionRoutingStatus.ASK,
                    rule_id=f"{question_id}_after_execution",
                    triggered_by=(
                        "q_prevention_measures_execution=True"
                    ),
                    reason=(
                        "La empresa declaró que ha ejecutado "
                        "medidas de prevención y control; se "
                        "consulta una característica asociada."
                    ),
                )
            )

    return _trace(decisions)


def _omit_dependent_questions(
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
        for question_id in MEASURES_DEPENDENT_IDS
    ]


def _trace(
    decisions: list[QuestionRoutingDecision],
) -> QuestionRoutingTrace:
    return QuestionRoutingTrace(
        requirement_id=(
            MEDIDAS_PREVENCION_CONTROL_REQUIREMENT_ID
        ),
        decisions=decisions,
    )