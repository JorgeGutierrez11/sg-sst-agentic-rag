from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.question_routing import (
    QuestionRoutingDecision,
    QuestionRoutingStatus,
    QuestionRoutingTrace,
)


PLAN_ANUAL_REQUIREMENT_ID = "res0312_art3_plan_anual_1_10"

PLAN_EXISTS_QUESTION_ID = "q_plan_exists"

PLAN_DEPENDENT_QUESTION_IDS = [
    "q_employer_signature",
    "q_plan_objectives",
    "q_plan_targets",
    "q_plan_responsibilities",
    "q_plan_resources",
    "q_annual_schedule",
]


def build_plan_anual_question_routing(
    answers: list[QuestionAnswer],
) -> QuestionRoutingTrace:
    """
    Decide qué preguntas auxiliares del Plan Anual de Trabajo
    deben formularse.

    La existencia del plan funciona como pregunta de entrada:

    - si todavía no se conoce, se pregunta primero;
    - si el plan existe, se habilitan sus condiciones;
    - si no existe, las preguntas sobre su contenido se omiten;
    - si la respuesta no puede resolverse, las preguntas
      dependientes permanecen omitidas.

    Este enrutamiento no determina cumplimiento normativo.
    """

    answers_by_id = {
        answer.question_id: answer
        for answer in answers
        if answer.requirement_id == PLAN_ANUAL_REQUIREMENT_ID
    }

    decisions: list[QuestionRoutingDecision] = []

    plan_exists_answer = answers_by_id.get(
        PLAN_EXISTS_QUESTION_ID
    )

    if plan_exists_answer is None:
        decisions.append(
            QuestionRoutingDecision(
                question_id=PLAN_EXISTS_QUESTION_ID,
                status=QuestionRoutingStatus.ASK,
                rule_id="plan_exists_entry",
                reason=(
                    "Primero se requiere conocer si la empresa "
                    "cuenta con un Plan Anual de Trabajo del SG-SST."
                ),
            )
        )

        decisions.extend(
            _omit_plan_detail_questions(
                trigger="q_plan_exists=unanswered",
                reason=(
                    "Primero debe determinarse si existe un "
                    "Plan Anual de Trabajo antes de consultar "
                    "sus características."
                ),
            )
        )

        return QuestionRoutingTrace(
            requirement_id=PLAN_ANUAL_REQUIREMENT_ID,
            decisions=decisions,
        )

    decisions.append(
        QuestionRoutingDecision(
            question_id=PLAN_EXISTS_QUESTION_ID,
            status=QuestionRoutingStatus.ANSWERED,
            rule_id="plan_exists_answered",
            triggered_by="q_plan_exists=answered",
            reason=(
                "La pregunta sobre la existencia del Plan Anual "
                "de Trabajo ya fue respondida."
            ),
        )
    )

    raw_answer = plan_exists_answer.raw_answer

    if raw_answer is True:
        decisions.extend(
            _route_plan_detail_questions(
                answers_by_id=answers_by_id,
            )
        )

    elif raw_answer is False:
        decisions.extend(
            _omit_plan_detail_questions(
                trigger="q_plan_exists=False",
                reason=(
                    "La empresa declaró que no cuenta con un "
                    "Plan Anual de Trabajo; por ello no se consultan "
                    "características de un documento declarado "
                    "como inexistente."
                ),
            )
        )

    else:
        decisions.extend(
            _omit_plan_detail_questions(
                trigger="q_plan_exists=unresolved",
                reason=(
                    "La respuesta sobre la existencia del Plan Anual "
                    "todavía no puede interpretarse como afirmativa "
                    "o negativa para habilitar las preguntas "
                    "dependientes."
                ),
            )
        )

    return QuestionRoutingTrace(
        requirement_id=PLAN_ANUAL_REQUIREMENT_ID,
        decisions=decisions,
    )


def _route_plan_detail_questions(
    *,
    answers_by_id: dict[str, QuestionAnswer],
) -> list[QuestionRoutingDecision]:
    """
    Habilita las preguntas sobre las características del plan
    cuando su existencia fue declarada afirmativamente.
    """

    decisions: list[QuestionRoutingDecision] = []

    for question_id in PLAN_DEPENDENT_QUESTION_IDS:
        if question_id in answers_by_id:
            decisions.append(
                QuestionRoutingDecision(
                    question_id=question_id,
                    status=QuestionRoutingStatus.ANSWERED,
                    rule_id=f"{question_id}_answered",
                    triggered_by=f"{question_id}=answered",
                    reason=(
                        "La pregunta sobre una característica "
                        "del Plan Anual ya fue respondida."
                    ),
                )
            )

        else:
            decisions.append(
                QuestionRoutingDecision(
                    question_id=question_id,
                    status=QuestionRoutingStatus.ASK,
                    rule_id=f"{question_id}_after_plan_exists",
                    triggered_by="q_plan_exists=True",
                    reason=(
                        "La empresa declaró que cuenta con un "
                        "Plan Anual de Trabajo; se consulta una "
                        "de sus características."
                    ),
                )
            )

    return decisions


def _omit_plan_detail_questions(
    *,
    trigger: str,
    reason: str,
) -> list[QuestionRoutingDecision]:
    """
    Omite las preguntas dependientes sobre las características
    del Plan Anual.
    """

    return [
        QuestionRoutingDecision(
            question_id=question_id,
            status=QuestionRoutingStatus.OMIT,
            rule_id=f"{question_id}_dependency",
            triggered_by=trigger,
            reason=reason,
        )
        for question_id in PLAN_DEPENDENT_QUESTION_IDS
    ]