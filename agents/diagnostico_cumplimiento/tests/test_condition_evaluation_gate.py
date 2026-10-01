
from pathlib import Path

from agents.diagnostico_cumplimiento.catalog.loader import load_catalog
from agents.diagnostico_cumplimiento.domain.answers import QuestionAnswer
from agents.diagnostico_cumplimiento.domain.condition_evaluation import (
    ConditionEvaluationStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.condition_answer_summary import (
    summarize_condition_answers,
)
from agents.diagnostico_cumplimiento.questionnaire.condition_evaluation_gate import (
    prepare_condition_evaluation,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)


def get_requirement():
    return load_catalog(PILOT_PATH).requirements[0]


def build_answer(requirement, question_id, raw_answer):
    return QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question_id,
        raw_answer=raw_answer,
    )


def test_distinguishes_interpreted_and_pending_conditions() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", "Sí"),
        build_answer(requirement, "q_pension_affiliation", "No sé"),
    ]

    summaries = summarize_condition_answers(requirement, answers)

    evaluations = [
        prepare_condition_evaluation(summary)
        for summary in summaries
    ]

    assert [evaluation.status for evaluation in evaluations] == [
        ConditionEvaluationStatus.NOT_EVALUATED,
        ConditionEvaluationStatus.PENDING_INFORMATION,
        ConditionEvaluationStatus.PENDING_INFORMATION,
    ]


def test_all_affirmative_answers_do_not_imply_compliance() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, question.id, True)
        for question in requirement.questions
    ]

    summaries = summarize_condition_answers(requirement, answers)

    evaluations = [
        prepare_condition_evaluation(summary)
        for summary in summaries
    ]

    assert all(
        evaluation.status == ConditionEvaluationStatus.NOT_EVALUATED
        for evaluation in evaluations
    )

    assert all(
        evaluation.criterion_reference is None
        and evaluation.evaluated_question_ids == []
        for evaluation in evaluations
    )


def test_negative_answer_does_not_automatically_imply_noncompliance() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(requirement, "q_health_affiliation", False),
    ]

    summaries = summarize_condition_answers(requirement, answers)

    evaluation = prepare_condition_evaluation(summaries[0])

    assert evaluation.status == ConditionEvaluationStatus.NOT_EVALUATED
    assert evaluation.criterion_reference is None
    assert evaluation.evaluated_question_ids == []


def test_no_answers_remain_pending_information() -> None:
    requirement = get_requirement()

    summaries = summarize_condition_answers(requirement, [])

    evaluations = [
        prepare_condition_evaluation(summary)
        for summary in summaries
    ]

    assert all(
        evaluation.status == ConditionEvaluationStatus.PENDING_INFORMATION
        for evaluation in evaluations
    )


def test_ambiguous_answer_remains_pending_information() -> None:
    requirement = get_requirement()

    answers = [
        build_answer(
            requirement,
            "q_health_affiliation",
            "Creo que sí, pero no estoy seguro.",
        ),
    ]

    summaries = summarize_condition_answers(requirement, answers)

    evaluation = prepare_condition_evaluation(summaries[0])

    assert evaluation.status == (
        ConditionEvaluationStatus.PENDING_INFORMATION
    )
    assert evaluation.criterion_reference is None
    assert evaluation.evaluated_question_ids == []
