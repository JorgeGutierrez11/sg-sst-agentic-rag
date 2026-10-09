from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agents.consulta_normativa.langchain_rag.core.llm import (
    build_deepseek_llm,
    invoke_llm_text,
)
from agents.diagnostico_cumplimiento.reporting.normative_gap_analysis import (
    NormativeGapAnalysis,
    NormativeGapCandidate,
    NormativeGapFinding,
    NormativeGapSource,
)


logger = logging.getLogger(__name__)


class LLMGapEnrichmentItem(BaseModel):
    """
    Parte de una brecha cuya redacción puede ser enriquecida por el LLM.

    El modelo no decide cumplimiento, no interpreta normativa nueva
    y no genera fuentes.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

    finding_reason: str = Field(min_length=1)

    orientative_action: str = Field(min_length=1)


class LLMGapEnrichmentResponse(BaseModel):
    """
    Respuesta estructurada esperada del LLM para todas las brechas.
    """

    model_config = ConfigDict(extra="forbid")

    findings: list[LLMGapEnrichmentItem]


def enrich_normative_gaps(
    candidates: list[NormativeGapCandidate],
    *,
    llm: Any | None = None,
) -> NormativeGapAnalysis:
    """
    Enriquece en una sola llamada LLM la redacción de las brechas.

    El estado declarativo, requisito, criterio normativo y fuente
    provienen siempre del diagnóstico y del catálogo.

    Si el LLM falla, se utiliza una construcción determinista para
    permitir que el reporte continúe generándose.
    """

    if not candidates:
        return NormativeGapAnalysis()

    try:
        model = llm or build_deepseek_llm()

        raw_response = invoke_llm_text(
            model,
            _build_enrichment_messages(candidates),
        )

        enrichment = _parse_enrichment_response(
            raw_response,
            candidates,
        )

        return _build_analysis_from_enrichment(
            candidates,
            enrichment,
        )

    except Exception as error:
        logger.warning(
            "Normative gap LLM enrichment failed; "
            "using deterministic fallback | error=%s | detail=%s",
            type(error).__name__,
            str(error),
        )

        return _build_fallback_analysis(candidates)


def _build_enrichment_messages(
    candidates: list[NormativeGapCandidate],
) -> list[tuple[str, str]]:
    """
    Construye el prompt para enriquecer todas las brechas
    mediante una única invocación.
    """

    payload = [
        {
            "requirement_id": candidate.requirement_id,
            "official_item_id": candidate.official_item_id,
            "requirement_name": candidate.requirement_name,
            "status": candidate.status.value,
            "assessment_explanation": (
                candidate.assessment_explanation
            ),
            "findings": candidate.findings,
            "missing_information": (
                candidate.missing_information
            ),
            "official_criterion": (
                candidate.official_criterion
            ),
            "official_verification_method": (
                candidate.official_verification_method
            ),
            "suggested_actions": (
                candidate.suggested_actions
            ),
        }
        for candidate in candidates
    ]

    system_message = """
Eres un componente de redacción del informe orientativo de diagnóstico
del SG-SST.

Recibirás requisitos que YA fueron evaluados por reglas deterministas.
No debes volver a evaluar cumplimiento.

Tu tarea se limita a redactar, para cada requisito:

1. finding_reason:
   Una explicación breve, clara y profesional de por qué el requisito
   requiere atención, usando exclusivamente el resultado declarativo,
   los hallazgos y la información faltante suministrados.

2. orientative_action:
   Una lista breve de acciones concretas que ayuden a la empresa
   a revisar, completar o atender el requisito.

REGLAS PARA orientative_action

- Devuelve entre 2 y 5 acciones concretas.
- Cada acción debe comenzar con "• ".
- Separa cada acción mediante un salto de línea.
- Cada acción debe expresar una sola tarea o comprobación.
- Usa verbos concretos como:
  verificar, confirmar, elaborar, asignar, realizar, implementar,
  ejecutar, documentar, conservar, actualizar o solicitar.
- Descompón el requisito en sus elementos relevantes cuando el
  criterio o el método de verificación contengan varias condiciones.
- Incluye los soportes o evidencias que deben revisarse o conservarse
  cuando estén indicados en el método de verificación.
- Evita recomendaciones genéricas como:
  "revisar el requisito",
  "revisar la situación declarada",
  "contrastar con el criterio",
  "cumplir con la normativa"
  o expresiones equivalentes.
- No repitas literalmente el criterio normativo completo.
- No redactes párrafos introductorios antes de las acciones.

TRATAMIENTO SEGÚN EL ESTADO

Si el estado es "does_not_comply_as_declared":

- Parte de las condiciones que no se encuentran satisfechas.
- Propón acciones concretas orientadas a atender esas condiciones.
- No es necesario comenzar con "revisar" o "considerar".
- Puedes utilizar directamente verbos como elaborar, realizar,
  implementar, asignar o ejecutar cuando estén sustentados por
  el criterio normativo y el método de verificación.

Ejemplo de forma:

• Elaborar el documento requerido.
• Incluir los elementos mínimos indicados en el requisito.
• Obtener las firmas o soportes correspondientes.
• Conservar la evidencia de su implementación.

Si el estado es "insufficient_information":

- NO asumas que existe incumplimiento.
- Prioriza acciones como verificar, confirmar, aclarar o aportar
  evidencia.
- Si corresponde, puedes incluir una acción condicional del tipo:
  "Si no se cuenta con ..., realizar/elaborar/implementar ...".
- Distingue claramente entre verificar una condición existente
  y recomendar implementarla cuando no exista.

Ejemplo de forma:

• Confirmar si la empresa cuenta con el elemento requerido.
• Verificar que incluya las condiciones señaladas en el requisito.
• Revisar o aportar los soportes correspondientes.
• Si no se cuenta con el elemento requerido, implementarlo conforme
  al criterio aplicable.

FUENTES DE INFORMACIÓN PERMITIDAS

Para redactar las acciones utiliza exclusivamente:

- el estado declarativo;
- la explicación de la evaluación;
- los hallazgos;
- la información faltante;
- el criterio oficial;
- el método oficial de verificación;
- las acciones sugeridas suministradas.

NO debes:

- cambiar el estado de cumplimiento;
- determinar nuevamente si la empresa cumple;
- inventar requisitos normativos;
- inventar documentos, soportes o procedimientos;
- inventar artículos, resoluciones o fuentes;
- agregar obligaciones que no aparezcan en los datos suministrados;
- agregar plazos, responsables o frecuencias no suministrados;
- afirmar que se realizó auditoría o verificación documental;
- establecer criticidad, prioridad o severidad;
- excluir requisitos recibidos;
- agregar requisitos nuevos.

Conserva exactamente cada requirement_id recibido.

Devuelve EXCLUSIVAMENTE JSON válido con esta estructura:

{
  "findings": [
    {
      "requirement_id": "id original",
      "finding_reason": "texto breve",
      "orientative_action": "• Acción 1\\n• Acción 2\\n• Acción 3"
    }
  ]
}
""".strip()

    human_message = (
        "Requisitos que requieren atención:\n\n"
        + json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )

    return [
        ("system", system_message),
        ("human", human_message),
    ]


def _parse_enrichment_response(
    raw_response: str,
    candidates: list[NormativeGapCandidate],
) -> LLMGapEnrichmentResponse:
    """
    Valida que DeepSeek devuelva exactamente una redacción
    para cada requisito solicitado.
    """

    text = raw_response.strip()

    if text.startswith("```"):
        text = _remove_markdown_fence(text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "DeepSeek no devolvió JSON válido para las brechas."
        ) from error

    try:
        response = LLMGapEnrichmentResponse.model_validate(data)
    except ValidationError as error:
        raise ValueError(
            "La respuesta de DeepSeek no cumple el esquema "
            "esperado para las brechas."
        ) from error

    expected_ids = {
        candidate.requirement_id
        for candidate in candidates
    }

    received_ids = [
        finding.requirement_id
        for finding in response.findings
    ]

    if len(received_ids) != len(set(received_ids)):
        raise ValueError(
            "DeepSeek devolvió requirement_id duplicados."
        )

    if set(received_ids) != expected_ids:
        raise ValueError(
            "DeepSeek no devolvió exactamente los requisitos "
            "solicitados."
        )

    return response


def _build_analysis_from_enrichment(
    candidates: list[NormativeGapCandidate],
    enrichment: LLMGapEnrichmentResponse,
) -> NormativeGapAnalysis:
    """
    Combina la redacción del LLM con los datos normativos
    deterministas del catálogo.
    """

    enrichment_by_id = {
        item.requirement_id: item
        for item in enrichment.findings
    }

    findings: list[NormativeGapFinding] = []

    for candidate in candidates:
        enriched = enrichment_by_id[
            candidate.requirement_id
        ]

        findings.append(
            NormativeGapFinding(
                requirement_id=candidate.requirement_id,
                official_item_id=candidate.official_item_id,
                requirement_name=candidate.requirement_name,
                status=candidate.status,
                finding_reason=enriched.finding_reason,
                normative_requirement=(
                    candidate.official_criterion
                ),
                orientative_action=(
                    enriched.orientative_action
                ),
                sources=[
                    _build_catalog_source(candidate)
                ],
            )
        )

    return NormativeGapAnalysis(
        findings=findings,
    )


def _build_fallback_analysis(
    candidates: list[NormativeGapCandidate],
) -> NormativeGapAnalysis:
    """
    Construye el análisis sin LLM cuando el enriquecimiento
    no está disponible.
    """

    findings = [
        NormativeGapFinding(
            requirement_id=candidate.requirement_id,
            official_item_id=candidate.official_item_id,
            requirement_name=candidate.requirement_name,
            status=candidate.status,
            finding_reason=_fallback_finding_reason(
                candidate
            ),
            normative_requirement=(
                candidate.official_criterion
            ),
            orientative_action=_fallback_action(
                candidate
            ),
            sources=[
                _build_catalog_source(candidate)
            ],
        )
        for candidate in candidates
    ]

    return NormativeGapAnalysis(
        findings=findings,
    )


def _fallback_finding_reason(
    candidate: NormativeGapCandidate,
) -> str:
    if candidate.findings:
        return " ".join(candidate.findings)

    if candidate.missing_information:
        return (
            "La información suministrada no permite determinar "
            "completamente el cumplimiento del requisito. "
            "Información pendiente: "
            + "; ".join(candidate.missing_information)
        )

    return candidate.assessment_explanation


def _fallback_action(
    candidate: NormativeGapCandidate,
) -> str:
    if candidate.suggested_actions:
        return " ".join(candidate.suggested_actions)

    if candidate.official_verification_method:
        return (
            "Revisar el cumplimiento del requisito y contrastarlo "
            "con el método oficial de verificación: "
            f"{candidate.official_verification_method}"
        )

    return (
        "Revisar la situación identificada frente al criterio "
        "normativo aplicable y definir las acciones correspondientes."
    )


def _build_catalog_source(
    candidate: NormativeGapCandidate,
) -> NormativeGapSource:
    source = candidate.catalog_source

    return NormativeGapSource(
        norm=source.norm,
        reference=(
            f"Artículo {source.requirements_article}"
        ),
    )


def _remove_markdown_fence(
    text: str,
) -> str:
    lines = text.splitlines()

    if lines and lines[0].startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()