from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.declarative_assessment import (
    RequirementDeclarativeAssessment,
)
from agents.diagnostico_cumplimiento.domain.models import (
    CompanyProfile,
)
from agents.diagnostico_cumplimiento.domain.question_routing import (
    QuestionRoutingTrace,
)
from agents.diagnostico_cumplimiento.domain.requirement_applicability import (
    RequirementApplicabilityDecision,
)
from agents.diagnostico_cumplimiento.questionnaire.questionnaire import (
    QuestionnaireSnapshot,
    run_questionnaire,
)
from agents.diagnostico_cumplimiento.reporting.orientative_report import (
    OrientativeReport,
    build_orientative_report,
)
from agents.diagnostico_cumplimiento.rules.assessment.generic_requirement_assessment import (
    assess_requirement_as_declared,
    determine_requirement_applicability,
)


class CatalogCoverage(BaseModel):
    """
    Describe el paquete normativo utilizado en el diagnóstico.

    El catálogo seleccionado corresponde al régimen de Estándares
    Mínimos configurado para el perfil empresarial suministrado.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["selected_package"] = "selected_package"

    included_requirement_count: int = Field(
        ge=1,
    )

    included_requirement_ids: list[str] = Field(
        min_length=1,
    )

    explanation: str = (
        "El diagnóstico utiliza el paquete de requisitos configurado "
        "para el perfil empresarial suministrado dentro del alcance "
        "actual del Agente 2. El resultado corresponde a una "
        "autoevaluación orientativa basada en información declarada "
        "y no constituye auditoría, certificación ni verificación "
        "documental del SG-SST."
    )


class PreliminaryDiagnosisResult(BaseModel):
    """
    Resultado consolidado del Agente 2.

    Contiene:

    - cuestionario procesado;
    - informe orientativo;
    - cobertura del paquete seleccionado;
    - decisiones de aplicabilidad;
    - evaluaciones declarativas por requisito.

    ``routing`` se conserva temporalmente por compatibilidad con
    consumidores antiguos. El nuevo routing está representado
    directamente dentro de los RequirementSnapshot.
    """

    model_config = ConfigDict(extra="forbid")

    questionnaire: QuestionnaireSnapshot

    report: OrientativeReport

    coverage: CatalogCoverage

    applicability: list[RequirementApplicabilityDecision] = Field(
        default_factory=list,
    )

    routing: list[QuestionRoutingTrace] = Field(
        default_factory=list,
    )

    assessments: list[RequirementDeclarativeAssessment] = Field(
        default_factory=list,
    )


def run_preliminary_diagnosis(
    profile: CompanyProfile,
    answers: list[QuestionAnswer],
    catalog_path: str | Path | None = None,
) -> PreliminaryDiagnosisResult:
    """
    Ejecuta el diagnóstico declarativo del Agente 2.

    Por defecto, el catálogo se selecciona automáticamente a partir
    del perfil empresarial.

    ``catalog_path`` se conserva temporalmente para pruebas y flujos
    antiguos durante la migración.

    El flujo es completamente genérico:

    1. selecciona y carga el paquete normativo;
    2. procesa las preguntas y su routing;
    3. determina la aplicabilidad de cada requisito;
    4. realiza la evaluación declarativa;
    5. construye el informe orientativo.

    No utiliza reglas hardcodeadas para requisitos concretos.
    """

    questionnaire = run_questionnaire(
        profile=profile,
        answers=answers,
        catalog_path=catalog_path,
    )

    included_requirement_ids = [
        requirement.requirement_id
        for requirement in questionnaire.requirements
    ]

    coverage = CatalogCoverage(
        included_requirement_count=(
            len(included_requirement_ids)
        ),
        included_requirement_ids=(
            included_requirement_ids
        ),
    )

    # --------------------------------------------------------
    # Aplicabilidad
    # --------------------------------------------------------

    applicability = [
        determine_requirement_applicability(
            requirement
        )
        for requirement in questionnaire.requirements
    ]

    applicability_by_requirement = {
        decision.requirement_id: decision
        for decision in applicability
    }

    # --------------------------------------------------------
    # Evaluación declarativa genérica
    # --------------------------------------------------------

    assessments: list[
        RequirementDeclarativeAssessment
    ] = []

    for requirement in questionnaire.requirements:
        requirement_applicability = (
            applicability_by_requirement[
                requirement.requirement_id
            ]
        )

        assessments.append(
            assess_requirement_as_declared(
                requirement=requirement,
                applicability=requirement_applicability,
            )
        )

    # --------------------------------------------------------
    # Informe
    # --------------------------------------------------------

    report = build_orientative_report(
        questionnaire=questionnaire,
        assessments=assessments,
    )

    return PreliminaryDiagnosisResult(
        questionnaire=questionnaire,
        report=report,
        coverage=coverage,
        applicability=applicability,

        # El nuevo routing está contenido directamente en
        # RequirementSnapshot.questions[].routing_state.
        routing=[],

        assessments=assessments,
    )