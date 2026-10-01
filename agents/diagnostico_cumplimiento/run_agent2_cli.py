from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agents.diagnostico_cumplimiento.catalog.loader import (
    load_catalog_for_profile,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.enums import (
    RiskClass,
)
from agents.diagnostico_cumplimiento.domain.interpretation import (
    AnswerInterpretation,
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.domain.models import (
    CompanyProfile,
)
from agents.diagnostico_cumplimiento.preliminary_diagnosis import (
    run_preliminary_diagnosis,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_interpreter import (
    interpret_boolean_answer_hybrid,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_answer_processor import (
    process_requirement_answers,
)
from agents.diagnostico_cumplimiento.rules.applicability import (
    select_applicable_requirements,
)
from agents.diagnostico_cumplimiento.reporting.art27_scoring_matrix import (
    Article27ScoringMatrix,
)
from agents.diagnostico_cumplimiento.reporting.art27_table_pdf import (
    build_article27_table_pdf,
)
from agents.diagnostico_cumplimiento.reporting.orientative_report import (
    OrientativeReport,
)
from agents.diagnostico_cumplimiento.reporting.scoring_matrix import (
    build_scoring_matrix,
)
from agents.diagnostico_cumplimiento.reporting.upa_scoring_matrix import (
    UPAScoringMatrix,
)
from agents.diagnostico_cumplimiento.reporting.upa_table_pdf import (
    build_upa_table_pdf,
)


ASSESSMENT_STATUS_LABELS = {
    "complies_as_declared": "Cumple según declaración",
    "does_not_comply_as_declared": "No cumple según declaración",
    "not_applicable": "No aplica",
    "insufficient_information": "Información insuficiente",
}


@dataclass(frozen=True)
class CollectedBooleanAnswer:
    """
    Conserva la respuesta original y su interpretación.

    ``evaluation_answer`` contiene el valor normalizado que se
    entrega posteriormente al motor determinístico.
    """

    original_answer: QuestionAnswer
    interpretation: AnswerInterpretation
    evaluation_answer: QuestionAnswer


def main() -> None:
    print()
    print("==============================================")
    print(" Diagnóstico orientativo de SG-SST")
    print("==============================================")
    print()
    print(
        "A continuación se recopilará información sobre la empresa "
        "y sus prácticas actuales de SG-SST."
    )
    print(
        "El resultado se basa en información declarada y no "
        "constituye una auditoría ni una verificación documental."
    )
    print()

    # ========================================================
    # Perfil empresarial
    # ========================================================

    print("----------------------------------------------")
    print("Perfil de la empresa")
    print("----------------------------------------------")
    print()

    economic_activity = _ask_required_text(
        "Actividad económica principal: "
    )

    ciiu_code = _ask_optional_text(
        "Código CIIU, si lo conoce (Enter para omitir): "
    )

    worker_count = _ask_worker_count()

    risk_class = _ask_risk_class()

    is_agricultural_production_unit = _ask_yes_no(
        "¿La empresa corresponde a una Unidad de "
        "Producción Agropecuaria (UPA)? (sí/no): "
    )

    permanent_worker_count: int | None = None

    if is_agricultural_production_unit:
        permanent_worker_count = _ask_permanent_worker_count(
            total_worker_count=worker_count,
        )

    profile = CompanyProfile(
        worker_count=worker_count,
        risk_class=risk_class,
        economic_activity=economic_activity,
        ciiu_code=ciiu_code,
        is_agricultural_production_unit=(
            is_agricultural_production_unit
        ),
        permanent_worker_count=permanent_worker_count,
    )

    print()
    print("Datos registrados:")
    print(
        f"- Actividad económica: "
        f"{profile.economic_activity}"
    )
    print(
        f"- Código CIIU: "
        f"{profile.ciiu_code or 'No informado'}"
    )
    print(
        f"- Número de trabajadores: "
        f"{profile.worker_count}"
    )
    print(
        f"- Clase de riesgo: "
        f"{profile.risk_class.value}"
    )
    print(
        "- Unidad de Producción Agropecuaria: "
        f"{'Sí' if profile.is_agricultural_production_unit else 'No'}"
    )

    if profile.is_agricultural_production_unit:
        print(
            "- Trabajadores permanentes de la UPA: "
            f"{profile.permanent_worker_count}"
        )

    # ========================================================
    # Selección automática del paquete normativo
    # ========================================================

    catalog = load_catalog_for_profile(
        profile
    )

    applicable_requirements = (
        select_applicable_requirements(
            profile,
            catalog,
        )
    )

    print()
    print("----------------------------------------------")
    print("Paquete normativo seleccionado")
    print("----------------------------------------------")
    print(
        f"{catalog.name}"
    )
    print(
        f"Requisitos a evaluar: "
        f"{len(applicable_requirements)}"
    )

    print()
    print("----------------------------------------------")
    print("Requisitos identificados")
    print("----------------------------------------------")

    for index, requirement in enumerate(
        applicable_requirements,
        start=1,
    ):
        item_prefix = (
            f"{requirement.official_item_id} - "
            if requirement.official_item_id
            else ""
        )

        print(
            f"{index}. "
            f"{item_prefix}"
            f"{requirement.name}"
        )

    # ========================================================
    # Cuestionario
    # ========================================================

    print()
    print("==============================================")
    print("Inicio del diagnóstico")
    print("==============================================")

    answers: list[QuestionAnswer] = []

    answer_trace: list[
        CollectedBooleanAnswer
    ] = []

    for requirement_index, requirement in enumerate(
        applicable_requirements,
        start=1,
    ):
        print()
        print("----------------------------------------------")
        print(
            f"[{requirement_index}/"
            f"{len(applicable_requirements)}] "
            f"{requirement.name}"
        )
        print("----------------------------------------------")

        if requirement.official_item_id:
            print(
                f"Ítem normativo: "
                f"{requirement.official_item_id}"
            )

        print(
            "Responde con la información que puedas confirmar "
            "sobre la situación actual de la empresa."
        )

        while True:
            requirement_answers = [
                answer
                for answer in answers
                if answer.requirement_id == requirement.id
            ]

            processing = process_requirement_answers(
                requirement=requirement,
                answers=requirement_answers,
            )

            if not processing.unanswered_question_ids:
                break

            next_question_id = _select_next_question(
                requirement=requirement,
                question_ids=(
                    processing.unanswered_question_ids
                ),
            )

            question = next(
                question
                for question in requirement.questions
                if question.id == next_question_id
            )

            print()
            print(question.text)

            collected_answer = (
                _ask_natural_boolean_answer(
                    requirement=requirement,
                    question_id=next_question_id,
                )
            )

            answers.append(
                collected_answer.evaluation_answer
            )

            answer_trace.append(
                collected_answer
            )

        # Muestra únicamente una advertencia operativa.
        final_processing = process_requirement_answers(
            requirement=requirement,
            answers=[
                answer
                for answer in answers
                if answer.requirement_id == requirement.id
            ],
        )

        if (
            final_processing.unresolved_question_ids
            or final_processing.blocked_question_ids
        ):
            print()
            print(
                "Este requisito quedó con información "
                "pendiente o no resuelta."
            )

    # ========================================================
    # Diagnóstico genérico
    # ========================================================

    result = run_preliminary_diagnosis(
        profile=profile,
        answers=answers,
    )

    assessments_by_requirement = {
        assessment.requirement_id: assessment
        for assessment in result.assessments
    }

    # ========================================================
    # Resultado
    # ========================================================

    print()
    print("==============================================")
    print("Resultado del diagnóstico")
    print("==============================================")

    for requirement in result.questionnaire.requirements:
        assessment = assessments_by_requirement.get(
            requirement.requirement_id
        )

        if assessment is None:
            raise RuntimeError(
                "No se generó evaluación para el requisito: "
                f"{requirement.requirement_id}"
            )

        print()
        print("----------------------------------------------")

        if requirement.official_item_id:
            print(
                f"{requirement.official_item_id} - "
                f"{requirement.name}"
            )
        else:
            print(
                requirement.name
            )

        print("----------------------------------------------")

        print(
            "Estado: "
            f"{_assessment_status_label(assessment.status.value)}"
        )

        print()
        print("Resultado del análisis:")
        print(
            assessment.explanation
        )

        if (
            assessment.applicability.reason
            and assessment.status.value == "not_applicable"
        ):
            print()
            print("Motivo de no aplicabilidad:")
            print(
                assessment.applicability.reason
            )

        if assessment.missing_information:
            print()
            print("Información pendiente:")

            for item in assessment.missing_information:
                print(
                    f"- {item}"
                )

    # ========================================================
    # Resumen
    # ========================================================

    status_counts: dict[str, int] = {}

    for assessment in result.assessments:
        status_counts[assessment.status.value] = (
            status_counts.get(
                assessment.status.value,
                0,
            )
            + 1
        )

    print()
    print("==============================================")
    print("Resumen")
    print("==============================================")

    for status, count in status_counts.items():
        print(
            f"- {_assessment_status_label(status)}: "
            f"{count}"
        )

    print()
    print(
        f"Total de requisitos evaluados: "
        f"{len(result.assessments)}"
    )

    # ========================================================
    # Generación automática del PDF
    # ========================================================

    print()
    print("----------------------------------------------")
    print("Generación del informe PDF")
    print("----------------------------------------------")

    try:
        pdf_path = _generate_pdf_report(
            result.report
        )

    except Exception as exc:
        print(
            "No fue posible generar automáticamente "
            "el informe PDF."
        )
        print(
            f"Detalle: {exc}"
        )

    else:
        print(
            "Informe PDF generado correctamente:"
        )
        print(
            pdf_path
        )

    print()
    print("==============================================")
    print("Fin del diagnóstico")
    print("==============================================")
    print()
    print(
        "Los resultados se basan exclusivamente en la "
        "información declarada por la empresa."
    )
    print(
        "No constituyen una auditoría, certificación ni "
        "verificación documental del SG-SST."
    )
    print()


def _generate_pdf_report(
    report: OrientativeReport,
) -> Path:
    """
    Genera automáticamente el PDF correspondiente al
    paquete normativo utilizado durante el diagnóstico.

    Los paquetes generales utilizan la Tabla de Valores
    del artículo 27. Las UPA de diez (10) o menos
    trabajadores permanentes utilizan su tabla especial
    de tres estándares.
    """

    output_dir = Path(
        "outputs/diagnosticos"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    output_path = (
        output_dir
        / f"diagnostico_sgsst_{timestamp}.pdf"
    )

    matrix = build_scoring_matrix(
        report
    )

    if isinstance(
        matrix,
        Article27ScoringMatrix,
    ):
        return build_article27_table_pdf(
            matrix,
            output_path,
        )

    if isinstance(
        matrix,
        UPAScoringMatrix,
    ):
        return build_upa_table_pdf(
            matrix,
            output_path,
        )

    raise TypeError(
        "Tipo de matriz de calificación "
        f"no soportado: {type(matrix).__name__}"
    )


def _assessment_status_label(
    status: str,
) -> str:
    return ASSESSMENT_STATUS_LABELS.get(
        status,
        status.replace(
            "_",
            " ",
        ).capitalize(),
    )


def _ask_required_text(
    prompt: str,
) -> str:
    while True:
        value = input(
            prompt
        ).strip()

        if value:
            return value

        print(
            "Este dato es necesario para continuar."
        )


def _ask_optional_text(
    prompt: str,
) -> str | None:
    value = input(
        prompt
    ).strip()

    return value or None


def _ask_risk_class() -> RiskClass:
    while True:
        value = input(
            "Clase de riesgo de la empresa "
            "(I, II, III, IV o V): "
        ).strip().upper()

        try:
            risk_class = RiskClass(
                value
            )

        except ValueError:
            print(
                "Ingresa una clase de riesgo válida: "
                "I, II, III, IV o V."
            )
            continue

        if risk_class != RiskClass.I:
            print()
            print(
                "Actualmente este diagnóstico está disponible "
                "únicamente para empresas clasificadas "
                "en riesgo I."
            )
            print()
            continue

        return risk_class


def _ask_worker_count() -> int:
    while True:
        value = input(
            "Número total de trabajadores de la empresa: "
        ).strip()

        try:
            worker_count = int(
                value
            )

        except ValueError:
            print(
                "Ingresa un número entero válido."
            )
            continue

        if worker_count < 1:
            print(
                "El número de trabajadores debe ser "
                "mayor que cero."
            )
            continue

        return worker_count


def _ask_permanent_worker_count(
    *,
    total_worker_count: int,
) -> int:
    while True:
        value = input(
            "Número de trabajadores permanentes de la UPA: "
        ).strip()

        try:
            permanent_worker_count = int(
                value
            )

        except ValueError:
            print(
                "Ingresa un número entero válido."
            )
            continue

        if permanent_worker_count < 1:
            print(
                "El número de trabajadores permanentes debe "
                "ser mayor que cero."
            )
            continue

        if permanent_worker_count > total_worker_count:
            print(
                "El número de trabajadores permanentes no puede "
                "superar el número total de trabajadores."
            )
            continue

        return permanent_worker_count


def _ask_yes_no(
    prompt: str,
) -> bool:
    while True:
        value = input(
            prompt
        ).strip().casefold()

        if value in {
            "sí",
            "si",
            "s",
            "yes",
            "y",
        }:
            return True

        if value in {
            "no",
            "n",
        }:
            return False

        print(
            "Responde sí o no."
        )


def _ask_natural_boolean_answer(
    *,
    requirement,
    question_id: str,
) -> CollectedBooleanAnswer:
    """
    Recibe lenguaje natural y conserva:

    - respuesta original;
    - interpretación;
    - valor normalizado para la evaluación.

    El LLM interpreta la declaración del usuario.
    No determina cumplimiento normativo.
    """

    while True:
        raw_text = input(
            "> "
        ).strip()

        if not raw_text:
            print(
                "Escribe una respuesta para continuar."
            )
            continue

        original_answer = QuestionAnswer(
            requirement_id=requirement.id,
            question_id=question_id,
            raw_answer=raw_text,
        )

        interpretation = (
            interpret_boolean_answer_hybrid(
                requirement,
                original_answer,
            )
        )

        if (
            interpretation.status
            == InterpretationStatus.AFFIRMATIVE
        ):
            evaluation_answer = QuestionAnswer(
                requirement_id=requirement.id,
                question_id=question_id,
                raw_answer=True,
            )

            return CollectedBooleanAnswer(
                original_answer=original_answer,
                interpretation=interpretation,
                evaluation_answer=evaluation_answer,
            )

        if (
            interpretation.status
            == InterpretationStatus.NEGATIVE
        ):
            evaluation_answer = QuestionAnswer(
                requirement_id=requirement.id,
                question_id=question_id,
                raw_answer=False,
            )

            return CollectedBooleanAnswer(
                original_answer=original_answer,
                interpretation=interpretation,
                evaluation_answer=evaluation_answer,
            )

        if (
            interpretation.status
            == InterpretationStatus.INSUFFICIENT_INFORMATION
        ):
            print(
                "La respuesta quedó registrada como "
                "información insuficiente."
            )

            return CollectedBooleanAnswer(
                original_answer=original_answer,
                interpretation=interpretation,
                evaluation_answer=original_answer,
            )

        if (
            interpretation.status
            == InterpretationStatus.NEEDS_CLARIFICATION
        ):
            print()
            print(
                "Necesito precisar tu respuesta:"
            )
            print(
                interpretation.explanation
            )
            print()
            print(
                "Responde nuevamente con la información "
                "que puedas confirmar."
            )
            continue

        print(
            "No fue posible interpretar la respuesta. "
            "Intenta expresarla de otra manera."
        )


def _select_next_question(
    *,
    requirement,
    question_ids: list[str],
) -> str:
    """
    Selecciona la siguiente pregunta activa respetando
    el orden definido en el catálogo.
    """

    available = set(
        question_ids
    )

    for question in requirement.questions:
        if question.id in available:
            return question.id

    raise RuntimeError(
        "El motor de routing produjo una pregunta que "
        "no existe en el requisito."
    )


if __name__ == "__main__":
    main()