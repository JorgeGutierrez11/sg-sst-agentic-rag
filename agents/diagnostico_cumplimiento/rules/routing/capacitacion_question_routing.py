from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.question_routing import (
    QuestionRoutingDecision,
    QuestionRoutingStatus,
    QuestionRoutingTrace,
)


CAPACITACION_REQUIREMENT_ID = (
    "res0312_art3_capacitacion_1_10"
)

TRAINING_PREPARATION_QUESTION_ID = (
    "q_training_preparation"
)

TRAINING_EXECUTION_QUESTION_ID = (
    "q_training_execution"
)

TRAINING_DETAIL_QUESTION_IDS = [
    "q_priority_risks_training",
    "q_prevention_control_training",
    "q_training_records",
]


def build_capacitacion_question_routing(
    answers: list[QuestionAnswer],
) -> QuestionRoutingTrace:
    """
    Decide qué preguntas auxiliares de capacitación deben
    formularse según las respuestas previas.

    El routing no determina cumplimiento normativo.
    """

    answers_by_id = {
        answer.question_id: answer
        for answer in answers
        if answer.requirement_id
        == CAPACITACION_REQUIREMENT_ID
    }

    decisions: list[QuestionRoutingDecision] = []

    preparation_answer = answers_by_id.get(
        TRAINING_PREPARATION_QUESTION_ID
    )

    # 1. Primero determinar si existen programas o actividades.
    if preparation_answer is None:
        decisions.append(
            QuestionRoutingDecision(
                question_id=TRAINING_PREPARATION_QUESTION_ID,
                status=QuestionRoutingStatus.ASK,
                rule_id="training_preparation_entry",
                reason=(
                    "Primero se requiere conocer si la empresa "
                    "cuenta con un programa o actividades de "
                    "capacitación en SST."
                ),
            )
        )

        decisions.extend(
            _omit_after_preparation(
                trigger="q_training_preparation=unanswered",
                reason=(
                    "Primero debe conocerse si existen programas "
                    "o actividades de capacitación antes de "
                    "consultar su ejecución y características."
                ),
            )
        )

        return QuestionRoutingTrace(
            requirement_id=CAPACITACION_REQUIREMENT_ID,
            decisions=decisions,
        )

    decisions.append(
        QuestionRoutingDecision(
            question_id=TRAINING_PREPARATION_QUESTION_ID,
            status=QuestionRoutingStatus.ANSWERED,
            rule_id="training_preparation_answered",
            triggered_by="q_training_preparation=answered",
            reason=(
                "La pregunta sobre la existencia de programas "
                "o actividades de capacitación ya fue respondida."
            ),
        )
    )

    # 2. Si no existen actividades, no tiene sentido preguntar
    # por ejecución, contenidos o soportes.
    if preparation_answer.raw_answer is False:
        decisions.extend(
            _omit_after_preparation(
                trigger="q_training_preparation=False",
                reason=(
                    "La empresa declaró que no cuenta con un "
                    "programa o actividades de capacitación; "
                    "por ello no se consultan características "
                    "dependientes de dichas actividades."
                ),
            )
        )

        return QuestionRoutingTrace(
            requirement_id=CAPACITACION_REQUIREMENT_ID,
            decisions=decisions,
        )

    if preparation_answer.raw_answer is not True:
        decisions.extend(
            _omit_after_preparation(
                trigger="q_training_preparation=unresolved",
                reason=(
                    "La respuesta sobre la existencia de "
                    "actividades de capacitación todavía no puede "
                    "interpretarse como afirmativa o negativa."
                ),
            )
        )

        return QuestionRoutingTrace(
            requirement_id=CAPACITACION_REQUIREMENT_ID,
            decisions=decisions,
        )

    # 3. Existen actividades: determinar si fueron ejecutadas.
    execution_answer = answers_by_id.get(
        TRAINING_EXECUTION_QUESTION_ID
    )

    if execution_answer is None:
        decisions.append(
            QuestionRoutingDecision(
                question_id=TRAINING_EXECUTION_QUESTION_ID,
                status=QuestionRoutingStatus.ASK,
                rule_id="training_execution_after_preparation",
                triggered_by="q_training_preparation=True",
                reason=(
                    "La empresa declaró que cuenta con programas "
                    "o actividades de capacitación; se requiere "
                    "conocer si fueron ejecutadas."
                ),
            )
        )

        decisions.extend(
            _omit_training_details(
                trigger="q_training_execution=unanswered",
                reason=(
                    "Primero debe conocerse si las actividades "
                    "de capacitación fueron ejecutadas antes de "
                    "consultar sus contenidos y soportes."
                ),
            )
        )

        return QuestionRoutingTrace(
            requirement_id=CAPACITACION_REQUIREMENT_ID,
            decisions=decisions,
        )

    decisions.append(
        QuestionRoutingDecision(
            question_id=TRAINING_EXECUTION_QUESTION_ID,
            status=QuestionRoutingStatus.ANSWERED,
            rule_id="training_execution_answered",
            triggered_by="q_training_execution=answered",
            reason=(
                "La pregunta sobre la ejecución de las "
                "actividades de capacitación ya fue respondida."
            ),
        )
    )

    if execution_answer.raw_answer is False:
        decisions.extend(
            _omit_training_details(
                trigger="q_training_execution=False",
                reason=(
                    "La empresa declaró que las actividades de "
                    "capacitación no han sido ejecutadas; por ello "
                    "no se consultan contenidos ni soportes de "
                    "capacitaciones realizadas."
                ),
            )
        )

    elif execution_answer.raw_answer is True:
        decisions.extend(
            _route_training_details(
                answers_by_id=answers_by_id,
            )
        )

    else:
        decisions.extend(
            _omit_training_details(
                trigger="q_training_execution=unresolved",
                reason=(
                    "La respuesta sobre la ejecución de las "
                    "capacitaciones todavía no puede interpretarse "
                    "como afirmativa o negativa."
                ),
            )
        )

    return QuestionRoutingTrace(
        requirement_id=CAPACITACION_REQUIREMENT_ID,
        decisions=decisions,
    )


def _route_training_details(
    *,
    answers_by_id: dict[str, QuestionAnswer],
) -> list[QuestionRoutingDecision]:
    decisions: list[QuestionRoutingDecision] = []

    for question_id in TRAINING_DETAIL_QUESTION_IDS:
        if question_id in answers_by_id:
            decisions.append(
                QuestionRoutingDecision(
                    question_id=question_id,
                    status=QuestionRoutingStatus.ANSWERED,
                    rule_id=f"{question_id}_answered",
                    triggered_by=f"{question_id}=answered",
                    reason=(
                        "La pregunta sobre la capacitación "
                        "ya fue respondida."
                    ),
                )
            )
        else:
            decisions.append(
                QuestionRoutingDecision(
                    question_id=question_id,
                    status=QuestionRoutingStatus.ASK,
                    rule_id=f"{question_id}_after_execution",
                    triggered_by="q_training_execution=True",
                    reason=(
                        "La empresa declaró que ha ejecutado "
                        "actividades de capacitación; se consulta "
                        "una característica de dichas actividades."
                    ),
                )
            )

    return decisions


def _omit_after_preparation(
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
        for question_id in [
            TRAINING_EXECUTION_QUESTION_ID,
            *TRAINING_DETAIL_QUESTION_IDS,
        ]
    ]


def _omit_training_details(
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
        for question_id in TRAINING_DETAIL_QUESTION_IDS
    ]