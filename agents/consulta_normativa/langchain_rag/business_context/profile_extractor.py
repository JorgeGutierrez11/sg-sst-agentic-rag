"""Extraction of explicit business-profile facts from user messages."""

import logging
from typing import Any

from pydantic import BaseModel, Field

from agents.consulta_normativa.langchain_rag.business_context.models import (
    BusinessProfile,
    BusinessProfileExtractionResult,
    ProfileField,
)

logger = logging.getLogger(__name__)


class ExtractedProfileFact(BaseModel):
    """One explicit business-profile fact found in the user message."""

    field: ProfileField
    value: str | int
    evidence: str


class BusinessProfileExtractionSchema(BaseModel):
    """Structured LLM output for explicit business-profile extraction."""

    facts: list[ExtractedProfileFact] = Field(default_factory=list)


BUSINESS_PROFILE_EXTRACTION_SYSTEM_PROMPT = """
Eres un componente de extracción de información empresarial para un agente
de consulta normativa sobre SG-SST en Colombia.

Tu única tarea es extraer información que el usuario declare EXPLÍCITAMENTE
sobre su propia empresa en el MENSAJE ACTUAL.

Campos permitidos:

- economic_activity:
  Actividad económica que el usuario afirma que realiza su empresa.

- ciiu_code:
  Código CIIU que el usuario declara explícitamente para su empresa.
  Conserva el código como texto.

- worker_count:
  Número exacto de trabajadores que el usuario declara explícitamente.

- risk_class:
  Clase de riesgo I, II, III, IV o V únicamente cuando el usuario afirma
  explícitamente que esa es la clase de riesgo de su empresa.

REGLAS ESTRICTAS:

- NO respondas la pregunta del usuario.
- NO uses conocimiento externo.
- NO infieras información.
- NO calcules la clase de riesgo a partir del CIIU.
- NO deduzcas el CIIU a partir de la actividad económica.
- NO deduzcas el número de trabajadores.
- NO extraigas información solamente sugerida, probable o hipotética.
- NO extraigas un dato cuando el usuario está preguntando si ese dato es cierto.
- Una descripción empresarial incluida dentro de una pregunta también se
  considera explícita cuando el usuario se identifica directamente con ella.

  Ejemplos que SÍ deben extraerse:

  "¿Qué CIIU me aplica si soy una panadería?"
  → economic_activity = "panadería"

  "Si mi empresa es una ferretería, ¿qué estándares debo cumplir?"
  → economic_activity = "ferretería"

  "Tengo una empresa de mantenimiento de motocicletas, ¿qué me aplica?"
  → economic_activity = "mantenimiento de motocicletas"

- NO confundas estas expresiones con escenarios realmente hipotéticos.

  Ejemplos que NO deben extraerse:

  "¿Qué pasaría si tuviera una panadería?"
  "Supongamos que una empresa tiene 8 trabajadores."
  "Una panadería debería cumplir qué requisitos?"

Ejemplo:

Usuario:
"Mi CIIU es 1240, ¿qué riesgo soy?"

Extraer:
- ciiu_code = 1240

NO extraer:
- risk_class

Otro ejemplo:

Usuario:
"Creo que somos riesgo I."

NO extraer risk_class porque el usuario expresa incertidumbre.

Otro ejemplo:

Usuario:
"Somos riesgo I y tenemos 8 trabajadores."

Extraer:
- risk_class = I
- worker_count = 8


Para cada dato extraído debes incluir como evidence un fragmento textual
EXACTO del mensaje del usuario que respalde ese dato.

Si no existe información empresarial explícita, devuelve una lista facts vacía.

Si aparecen varios valores del mismo campo y el usuario indica claramente que
uno corresponde al estado actual, conserva únicamente el valor actual.

FORMATO DE SALIDA:

Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura:

{
  "facts": [
    {
      "field": "economic_activity",
      "value": "mantenimiento de motocicletas",
      "evidence": "empresa de mantenimiento de motocicletas"
    }
  ]
}

Los únicos valores permitidos para "field" son:
- "economic_activity"
- "ciiu_code"
- "worker_count"
- "risk_class"

Si no existe información empresarial explícita, devuelve exactamente:

{
  "facts": []
}

No incluyas explicaciones, Markdown, bloques de código ni texto fuera del JSON.
""".strip()


def extract_business_profile(
    llm: Any,
    question: str,
) -> BusinessProfileExtractionResult:
    """Extract explicit business-profile information from the current message."""

    normalized_question = question.strip()

    if not normalized_question:
        return _empty_extraction()

    try:
        extractor = llm.with_structured_output(
            BusinessProfileExtractionSchema,
            method="json_mode",
        )

        response = extractor.invoke(
            build_business_profile_extraction_messages(
                normalized_question
            )
        )

        extraction = BusinessProfileExtractionSchema.model_validate(response)

    except Exception as error:
        logger.error(
            "Business profile extraction failed: %s",
            error,
        )
        return _empty_extraction()

    return normalize_business_profile_extraction(
        extraction=extraction,
        question=normalized_question,
    )


def build_business_profile_extraction_messages(
    question: str,
) -> list[Any]:
    """Build messages used by the business-profile extractor."""

    # pyrefly: ignore [missing-import]
    from langchain_core.messages import HumanMessage, SystemMessage

    return [
        SystemMessage(content=BUSINESS_PROFILE_EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]


def normalize_business_profile_extraction(
    extraction: BusinessProfileExtractionSchema,
    question: str,
) -> BusinessProfileExtractionResult:
    """Convert structured LLM output into the business-profile contract."""

    updates: BusinessProfile = {}
    evidence: dict[ProfileField, str] = {}

    for fact in extraction.facts:
        value = str(fact.value).strip()
        fact_evidence = fact.evidence.strip()

        if not value or not fact_evidence:
            continue

        # Evidence must actually exist in the current user message.
        if fact_evidence not in question:
            continue

        if fact.field == "economic_activity":
            updates["economic_activity"] = value
            evidence["economic_activity"] = fact_evidence

        elif fact.field == "ciiu_code":
            updates["ciiu_code"] = value
            evidence["ciiu_code"] = fact_evidence

        elif fact.field == "worker_count":
            try:
                worker_count = int(value)
            except ValueError:
                continue

            if worker_count < 0:
                continue

            updates["worker_count"] = worker_count
            evidence["worker_count"] = fact_evidence

        elif fact.field == "risk_class":
            risk_class = value.upper()

            if risk_class not in {"I", "II", "III", "IV", "V"}:
                continue

            updates["risk_class"] = risk_class
            evidence["risk_class"] = fact_evidence

    return {
        "updates": updates,
        "evidence": evidence,
    }


def _empty_extraction() -> BusinessProfileExtractionResult:
    """Return a safe empty extraction result."""

    return {
        "updates": {},
        "evidence": {},
    }