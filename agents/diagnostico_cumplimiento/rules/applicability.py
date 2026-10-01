from agents.diagnostico_cumplimiento.catalog.schemas import (
    AssessmentCatalog,
    CatalogRequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.models import CompanyProfile


class ApplicabilityError(ValueError):
    """Error relacionado con la selección de requisitos aplicables."""


class OutOfScopeError(ApplicabilityError):
    """El perfil empresarial está fuera del alcance del Agente 2."""


class CatalogCoverageError(ApplicabilityError):
    """El catálogo seleccionado no contiene requisitos evaluables."""


class AmbiguousApplicabilityError(ApplicabilityError):
    """
    Error legado.

    Se conserva temporalmente para no romper imports existentes.
    Ya no se utiliza para seleccionar variantes dentro del catálogo,
    porque cada perfil empresarial recibe un único paquete normativo.
    """


def select_applicable_requirements(
    profile: CompanyProfile,
    catalog: AssessmentCatalog,
) -> list[CatalogRequirementDefinition]:
    """
    Devuelve los requisitos contenidos en el paquete normativo
    previamente seleccionado para la empresa.

    La selección por clase de riesgo, número de trabajadores y tipo
    de empresa se realiza antes, mediante catalog.selector.

    Esta función NO resuelve todavía la aplicabilidad condicional
    de requisitos individuales porque dicha decisión puede depender
    de respuestas obtenidas durante el cuestionario.

    En particular:

    - ``always``:
      el requisito se evalúa normalmente.

    - ``conditional``:
      puede resultar posteriormente en ``not_applicable`` cuando
      se evalúe su pregunta de aplicabilidad.

    - ``event_dependent``:
      determinadas preguntas dependen de la ocurrencia de un evento,
      pero la ausencia del evento no implica automáticamente
      ``not_applicable``.
    """

    if profile.risk_class != RiskClass.I:
        raise OutOfScopeError(
            "El Agente 2 únicamente admite empresas de riesgo I. "
            f"Clase de riesgo declarada: {profile.risk_class.value}."
        )

    requirements = list(catalog.requirements)

    if not requirements:
        raise CatalogCoverageError(
            "El paquete normativo seleccionado no contiene "
            "requisitos evaluables."
        )

    return requirements