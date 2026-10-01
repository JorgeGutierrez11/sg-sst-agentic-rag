
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from agents.diagnostico_cumplimiento.catalog.loader import (
    load_catalog,
    load_catalog_for_profile,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.models import (
    CompanyProfile,
)
from agents.diagnostico_cumplimiento.rules.applicability import (
    select_applicable_requirements,
)
from agents.diagnostico_cumplimiento.reporting.declarative_findings import (
    RequirementDeclarativeFindings,
    summarize_requirement_declarations,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_snapshot import (
    RequirementSnapshot,
    build_requirement_snapshot,
)


class QuestionnaireSnapshot(BaseModel):
    """
    Resultado consolidado del cuestionario.

    Incluye los requisitos seleccionados y sus hallazgos
    declarativos. No representa un diagnóstico normativo completo.
    """

    model_config = ConfigDict(extra="forbid")

    catalog_id: str = Field(min_length=1)
    catalog_version: str = Field(min_length=1)
    company_profile: CompanyProfile

    requirements: list[RequirementSnapshot] = Field(
        min_length=1,
    )

    declarative_findings: list[RequirementDeclarativeFindings] = Field(
        min_length=1,
    )

    scope_note: str = (
        "Este resultado corresponde únicamente a los requisitos "
        "incluidos en el catálogo utilizado. Los hallazgos se basan "
        "en información declarada por la empresa; no constituyen "
        "una verificación documental ni una certificación de "
        "cumplimiento normativo."
    )


def run_questionnaire(
    profile: CompanyProfile,
    answers: list[QuestionAnswer],
    catalog_path: str | Path | None = None,
) -> QuestionnaireSnapshot:
    """
    Ejecuta el cuestionario para el perfil empresarial suministrado.

    Por defecto selecciona automáticamente el paquete normativo
    correspondiente al perfil de la empresa.

    ``catalog_path`` se conserva temporalmente para compatibilidad
    con pruebas y flujos antiguos durante la migración.

    El cuestionario consolida información declarada por el usuario.
    No constituye una verificación documental ni una certificación
    de cumplimiento normativo.
    """

    if catalog_path is None:
        catalog = load_catalog_for_profile(profile)
    else:
        catalog = load_catalog(catalog_path)

    applicable_requirements = select_applicable_requirements(
        profile,
        catalog,
    )

    applicable_ids = {
        requirement.id
        for requirement in applicable_requirements
    }

    answers_by_requirement: dict[str, list[QuestionAnswer]] = {
        requirement.id: []
        for requirement in applicable_requirements
    }

    for answer in answers:
        if answer.requirement_id not in applicable_ids:
            raise ValueError(
                "La respuesta hace referencia a un requisito "
                "que no pertenece a los requisitos aplicables "
                f"seleccionados: '{answer.requirement_id}'."
            )

        answers_by_requirement[answer.requirement_id].append(
            answer
        )

    snapshots = [
        build_requirement_snapshot(
            requirement,
            answers_by_requirement[requirement.id],
        )
        for requirement in applicable_requirements
    ]

    declarative_findings = [
        summarize_requirement_declarations(snapshot)
        for snapshot in snapshots
    ]

    return QuestionnaireSnapshot(
        catalog_id=catalog.catalog_id,
        catalog_version=catalog.schema_version,
        company_profile=profile,
        requirements=snapshots,
        declarative_findings=declarative_findings,
    )