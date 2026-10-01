from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.catalog.schemas import (
    PhvaDefinition,
    RequirementScoring,
    RequirementSource,
)
from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    DeclarativeAssessmentStatus,
    RequirementDeclarativeAssessment,
)
from agents.diagnostico_cumplimiento.domain.interpretation import (
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.domain.requirement_applicability import (
    RequirementApplicabilityStatus,
)
from agents.diagnostico_cumplimiento.questionnaire.questionnaire import (
    QuestionnaireSnapshot,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_snapshot import (
    QuestionRoutingState,
)


class QuestionReport(BaseModel):
    """
    Estado declarativo de una pregunta utilizada para recopilar
    información sobre un requisito.

    La pregunta no constituye por sí misma una conclusión normativa.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1)

    role: str = Field(min_length=1)

    text: str = Field(min_length=1)

    routing_state: QuestionRoutingState

    answer_provided: bool

    interpretation_status: InterpretationStatus | None = None

    interpreted_value: Any | None = None


class RequirementReport(BaseModel):
    """
    Resultado orientativo de un requisito normativo.

    La unidad evaluada es el requisito, no cada pregunta.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

    official_item_id: str | None = None

    name: str = Field(min_length=1)

    phva: PhvaDefinition

    scoring: RequirementScoring

    official_criterion: str = Field(min_length=1)

    official_verification_method: str | None = None

    verification_method_source: str = Field(min_length=1)

    source: RequirementSource

    applicability_status: RequirementApplicabilityStatus | None = None

    applicability_reason: str | None = None

    assessment_status: DeclarativeAssessmentStatus | None = None

    assessment_explanation: str | None = None

    supporting_question_ids: list[str] = Field(
        default_factory=list,
    )

    missing_information: list[str] = Field(
        default_factory=list,
    )

    assessment_evidence_verified: bool | None = None

    requires_expert_validation: bool | None = None

    findings: list[str] = Field(
        default_factory=list,
    )

    suggested_actions: list[str] = Field(
        default_factory=list,
    )

    questions: list[QuestionReport] = Field(
        min_length=1,
    )


class OrientativeReport(BaseModel):
    """
    Informe orientativo generado a partir de información declarada.
    """

    model_config = ConfigDict(extra="forbid")

    catalog_id: str = Field(min_length=1)
    catalog_version: str = Field(min_length=1)

    title: str = "Diagnóstico orientativo del SG-SST"

    requirements: list[RequirementReport] = Field(
        min_length=1,
    )

    scope_note: str = (
        "Este informe se genera a partir del paquete normativo "
        "seleccionado para el perfil empresarial suministrado. "
        "Los resultados se basan exclusivamente en información "
        "declarada por la empresa y no constituyen una auditoría, "
        "certificación ni verificación documental del SG-SST."
    )


def build_orientative_report(
    questionnaire: QuestionnaireSnapshot,
    assessments: list[RequirementDeclarativeAssessment] | None = None,
    routing: list[object] | None = None,
) -> OrientativeReport:
    """
    Genera el informe orientativo del diagnóstico.

    ``routing`` se conserva temporalmente por compatibilidad con
    llamadas antiguas. El nuevo flujo obtiene el estado de routing
    directamente desde cada RequirementSnapshot.
    """

    del routing

    assessments = assessments or []

    assessments_by_requirement = {
        assessment.requirement_id: assessment
        for assessment in assessments
    }

    if len(assessments_by_requirement) != len(assessments):
        raise ValueError(
            "Existen evaluaciones declarativas duplicadas "
            "para un mismo requisito."
        )

    questionnaire_requirement_ids = {
        requirement.requirement_id
        for requirement in questionnaire.requirements
    }

    unknown_assessment_ids = (
        set(assessments_by_requirement)
        - questionnaire_requirement_ids
    )

    if unknown_assessment_ids:
        raise ValueError(
            "Existen evaluaciones declarativas que no corresponden "
            "a requisitos del cuestionario: "
            f"{sorted(unknown_assessment_ids)}"
        )

    findings_by_requirement = {
        finding.requirement_id: finding
        for finding in questionnaire.declarative_findings
    }

    if len(findings_by_requirement) != len(
        questionnaire.declarative_findings
    ):
        raise ValueError(
            "Existen hallazgos declarativos duplicados "
            "para un mismo requisito."
        )

    requirement_reports: list[RequirementReport] = []

    for requirement in questionnaire.requirements:
        finding = findings_by_requirement.get(
            requirement.requirement_id
        )

        if finding is None:
            raise ValueError(
                "No se encontraron hallazgos declarativos para "
                f"el requisito '{requirement.requirement_id}'."
            )

        assessment = assessments_by_requirement.get(
            requirement.requirement_id
        )

        questions_by_id = {
            question.question_id: question
            for question in requirement.questions
        }

        findings: list[str] = []
        suggested_actions: list[str] = []

        # ----------------------------------------------------
        # Declaraciones negativas
        # ----------------------------------------------------

        for question_id in finding.negative_question_ids:
            question = questions_by_id[question_id]

            findings.append(
                "La empresa declaró una situación negativa "
                f"respecto de: {question.text}"
            )

            suggested_actions.append(
                "Revisar la situación declarada y contrastarla "
                "con el criterio y método de verificación del "
                f"requisito: {question.text}"
            )

        # ----------------------------------------------------
        # Información pendiente
        # ----------------------------------------------------

        for question_id in finding.unanswered_question_ids:
            question = questions_by_id[question_id]

            findings.append(
                f"Falta información declarada sobre: {question.text}"
            )

            suggested_actions.append(
                f"Completar la información solicitada: {question.text}"
            )

        # ----------------------------------------------------
        # Respuestas no resueltas
        # ----------------------------------------------------

        for question_id in finding.unresolved_question_ids:
            question = questions_by_id[question_id]

            findings.append(
                "La respuesta requiere aclaración respecto de: "
                f"{question.text}"
            )

            suggested_actions.append(
                f"Aclarar la información declarada: {question.text}"
            )

        # ----------------------------------------------------
        # Preguntas bloqueadas
        # ----------------------------------------------------

        for question_id in finding.blocked_question_ids:
            question = questions_by_id[question_id]

            findings.append(
                "No fue posible resolver todavía la información "
                f"correspondiente a: {question.text}"
            )

        # ----------------------------------------------------
        # Resultado del assessment
        # ----------------------------------------------------

        if assessment is not None:
            if (
                assessment.status
                == DeclarativeAssessmentStatus.NOT_APPLICABLE
            ):
                findings.append(
                    "El requisito fue determinado como no aplicable "
                    "para el caso declarado."
                )

            elif (
                assessment.status
                == DeclarativeAssessmentStatus.COMPLIES_AS_DECLARED
            ):
                findings.append(
                    "Las declaraciones recopiladas permiten clasificar "
                    "el requisito como cumplido según lo declarado."
                )

                suggested_actions.append(
                    "Conservar y contrastar los soportes correspondientes "
                    "con el método de verificación definido para el "
                    "requisito."
                )

            elif (
                assessment.status
                == DeclarativeAssessmentStatus.DOES_NOT_COMPLY_AS_DECLARED
            ):
                findings.append(
                    "Las declaraciones recopiladas permiten identificar "
                    "al menos una condición evaluativa no satisfecha."
                )

            elif (
                assessment.status
                == DeclarativeAssessmentStatus.INSUFFICIENT_INFORMATION
            ):
                findings.append(
                    "La información disponible no permite emitir una "
                    "conclusión declarativa completa sobre el requisito."
                )

        question_reports = [
            QuestionReport(
                question_id=question.question_id,
                role=question.role,
                text=question.text,
                routing_state=question.routing_state,
                answer_provided=question.answer is not None,
                interpretation_status=(
                    question.interpretation.status
                    if question.interpretation is not None
                    else None
                ),
                interpreted_value=(
                    question.interpretation.interpreted_value
                    if question.interpretation is not None
                    else None
                ),
            )
            for question in requirement.questions
        ]

        requirement_reports.append(
            RequirementReport(
                requirement_id=requirement.requirement_id,
                official_item_id=requirement.official_item_id,
                name=requirement.name,
                phva=requirement.phva,
                scoring=requirement.scoring,
                official_criterion=requirement.official_criterion,
                official_verification_method=(
                    requirement.official_verification_method
                ),
                verification_method_source=(
                    requirement.verification_method_source
                ),
                source=requirement.source,
                applicability_status=(
                    assessment.applicability.status
                    if assessment is not None
                    else None
                ),
                applicability_reason=(
                    assessment.applicability.reason
                    if assessment is not None
                    else None
                ),
                assessment_status=(
                    assessment.status
                    if assessment is not None
                    else None
                ),
                assessment_explanation=(
                    assessment.explanation
                    if assessment is not None
                    else None
                ),
                supporting_question_ids=(
                    list(assessment.supporting_question_ids)
                    if assessment is not None
                    else []
                ),
                missing_information=(
                    list(assessment.missing_information)
                    if assessment is not None
                    else []
                ),
                assessment_evidence_verified=(
                    assessment.evidence_verified
                    if assessment is not None
                    else None
                ),
                requires_expert_validation=(
                    assessment.requires_expert_validation
                    if assessment is not None
                    else None
                ),
                findings=_unique_preserving_order(
                    findings
                ),
                suggested_actions=_unique_preserving_order(
                    suggested_actions
                ),
                questions=question_reports,
            )
        )

    return OrientativeReport(
        catalog_id=questionnaire.catalog_id,
        catalog_version=questionnaire.catalog_version,
        requirements=requirement_reports,
    )


def _unique_preserving_order(
    values: list[str],
) -> list[str]:
    return list(
        dict.fromkeys(values)
    )