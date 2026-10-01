from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.rules.routing.affiliation_question_routing import (
    AFFILIATION_REQUIREMENT_ID,
    build_affiliation_question_routing,
)


def answer(question_id, value):
    return QuestionAnswer(
        requirement_id=AFFILIATION_REQUIREMENT_ID,
        question_id=question_id,
        raw_answer=value,
    )


def test_without_answers_only_entry_questions_are_asked():
    trace = build_affiliation_question_routing([])

    assert trace.answered_questions == []

    assert trace.questions_to_ask == [
        "q_health_affiliation",
        "q_pension_affiliation",
        "q_occupational_risk_affiliation",
    ]

    assert trace.omitted_questions == [
        "q_health_affiliation_support",
        "q_health_payment_support",
        "q_pension_affiliation_support",
        "q_pension_payment_support",
        "q_occupational_risk_affiliation_support",
        "q_occupational_risk_payment_support",
    ]


def test_affirmative_affiliation_enables_dependent_questions():
    trace = build_affiliation_question_routing([
        answer("q_health_affiliation", True),
    ])

    assert trace.answered_questions == [
        "q_health_affiliation",
    ]

    assert trace.questions_to_ask == [
        "q_health_affiliation_support",
        "q_health_payment_support",
        "q_pension_affiliation",
        "q_occupational_risk_affiliation",
    ]

    assert "q_health_affiliation_support" not in (
        trace.omitted_questions
    )

    assert "q_health_payment_support" not in (
        trace.omitted_questions
    )


def test_negative_affiliation_omits_dependent_questions():
    trace = build_affiliation_question_routing([
        answer("q_health_affiliation", False),
    ])

    assert trace.answered_questions == [
        "q_health_affiliation",
    ]

    assert trace.questions_to_ask == [
        "q_pension_affiliation",
        "q_occupational_risk_affiliation",
    ]

    assert "q_health_affiliation_support" in (
        trace.omitted_questions
    )

    assert "q_health_payment_support" in (
        trace.omitted_questions
    )

    support_decision = next(
        decision
        for decision in trace.decisions
        if decision.question_id
        == "q_health_affiliation_support"
    )

    assert support_decision.triggered_by == (
        "q_health_affiliation=False"
    )

    assert support_decision.rule_id == (
        "health_support_dependency"
    )


def test_already_answered_dependent_question_is_not_asked_again():
    trace = build_affiliation_question_routing([
        answer("q_health_affiliation", True),
        answer("q_health_affiliation_support", False),
    ])

    assert trace.answered_questions == [
        "q_health_affiliation",
        "q_health_affiliation_support",
    ]

    assert "q_health_affiliation_support" not in (
        trace.questions_to_ask
    )

    assert "q_health_payment_support" in (
        trace.questions_to_ask
    )

    support_decision = next(
        decision
        for decision in trace.decisions
        if decision.question_id
        == "q_health_affiliation_support"
    )

    assert support_decision.status.value == "answered"


def test_mixed_branches_evolve_independently():
    trace = build_affiliation_question_routing([
        answer("q_health_affiliation", True),
        answer("q_pension_affiliation", False),
    ])

    assert trace.answered_questions == [
        "q_health_affiliation",
        "q_pension_affiliation",
    ]

    assert trace.questions_to_ask == [
        "q_health_affiliation_support",
        "q_health_payment_support",
        "q_occupational_risk_affiliation",
    ]

    assert trace.omitted_questions == [
        "q_pension_affiliation_support",
        "q_pension_payment_support",
        "q_occupational_risk_affiliation_support",
        "q_occupational_risk_payment_support",
    ]

    # La respuesta negativa de pensión no afecta
    # las preguntas dependientes de salud.
    assert "q_health_affiliation_support" in (
        trace.questions_to_ask
    )

    assert "q_health_payment_support" in (
        trace.questions_to_ask
    )