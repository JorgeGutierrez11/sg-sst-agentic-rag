
from pathlib import Path

import pytest

from agents.diagnostico_cumplimiento.catalog.loader import (
    load_catalog,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_format import (
    AnswerFormatStatus,
    classify_boolean_answer,
)


PILOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "catalog"
    / "data"
    / "res0312_piloto_v1.json"
)


@pytest.mark.parametrize(
    ("raw_answer", "expected_status"),
    [
        (True, AnswerFormatStatus.STRUCTURED),
        (False, AnswerFormatStatus.STRUCTURED),
        ("Sí", AnswerFormatStatus.NEEDS_INTERPRETATION),
        ("No sé", AnswerFormatStatus.NEEDS_INTERPRETATION),
        (
            "Creo que sí, pero no estoy seguro.",
            AnswerFormatStatus.NEEDS_INTERPRETATION,
        ),
        (8, AnswerFormatStatus.INVALID_FORMAT),
        (["Sí"], AnswerFormatStatus.INVALID_FORMAT),
    ],
)
def test_classifies_boolean_answer_format(
    raw_answer,
    expected_status: AnswerFormatStatus,
) -> None:
    requirement = load_catalog(PILOT_PATH).requirements[0]
    question = requirement.questions[0]

    answer = QuestionAnswer(
        requirement_id=requirement.id,
        question_id=question.id,
        raw_answer=raw_answer,
    )

    result = classify_boolean_answer(question, answer)

    assert result == expected_status

    # La clasificación nunca debe modificar la respuesta original.
    assert answer.raw_answer == raw_answer
