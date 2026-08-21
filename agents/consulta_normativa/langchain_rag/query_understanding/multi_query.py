"""Multi-query generation for SG-SST normative retrieval."""

import re
from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.core.llm import invoke_llm_text
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState

MULTI_QUERY_SYSTEM_PROMPT = """
Eres un componente de generación de consultas múltiples para recuperación normativa
en un sistema RAG sobre SG-SST colombiano.

Corpus disponible:

- Decreto 768 de 2022
- Decreto 1072 de 2015, Libro 2, Título 4, Capítulo 6
- Ley 1010 de 2006
- Ley 1562 de 2012
- Resolución 0312 de 2019
- Resolución 1401 de 2007
- Resolución 2013 de 1986
- Resolución 2346 de 2007

Tu única tarea es transformar la necesidad de información del usuario en consultas
alternativas optimizadas para recuperación semántica sobre este corpus.

No respondas la pregunta.

OBJETIVO PRINCIPAL

Las consultas generadas deben aproximarse al vocabulario, categorías y formas de
expresión utilizadas en normas jurídicas y técnicas del SG-SST.

No reformules simplemente la pregunta utilizando lenguaje natural diferente.

Debes transformar expresiones coloquiales o comerciales en conceptos normativos,
técnicos o categoriales equivalentes cuando exista una equivalencia suficientemente
clara.

NORMALIZACIÓN TERMINOLÓGICA

- Prefiere términos propios de la normativa SG-SST frente a expresiones coloquiales.
- Prefiere categorías normativas frente a nombres informales cuando sean equivalentes.
- Para actividades empresariales o profesiones expresadas informalmente, intenta
  representarlas mediante una denominación de actividad económica más formal o
  categorial que pueda aparecer en una tabla o clasificación normativa.
- Cuando la consulta trate sobre clasificación de riesgos laborales, prioriza términos
  como:
  "actividad económica",
  "clasificación de actividades económicas",
  "clase de riesgo",
  "Sistema General de Riesgos Laborales"
  cuando sean pertinentes a la intención original.
- Cuando la consulta trate sobre cumplimiento del SG-SST, utiliza términos como
  "estándares mínimos", "obligaciones del empleador", "gestión del SG-SST",
  "evaluaciones médicas ocupacionales", "investigación de accidente de trabajo",
  "COPASST" u otros términos técnicos únicamente cuando sean equivalentes claros
  de conceptos presentes en la consulta.
- No agregues terminología simplemente porque pertenezca al dominio SG-SST.
- Cuando el usuario mencione un tipo de negocio mediante una denominación coloquial, 
  genera variantes utilizando vocabulario categorial propio de la clasificación de 
  actividades económicas, como “actividad económica”, “comercio al por menor”, 
  “establecimiento especializado”, “elaboración” o “fabricación”, sin asumir procesos
  productivos que el usuario no haya especificado.

VARIACIÓN ENTRE CONSULTAS

Genera exactamente 3 consultas alternativas.

Las tres deben representar la MISMA necesidad de información.

Cada variante debe utilizar una representación terminológica diferente que pueda
favorecer la recuperación, por ejemplo:

- denominación normativa principal;
- denominación técnica o categorial equivalente;
- formulación basada en los conceptos utilizados para clasificar o regular el fenómeno.

La diversidad debe ser principalmente TERMINOLÓGICA y LÉXICA, no temática.

No conviertas una pregunta en varias subpreguntas.
No explores aspectos distintos que el usuario no haya solicitado.

ESTILO DE LAS CONSULTAS

Las consultas deben parecer consultas dirigidas a un corpus normativo, no preguntas
conversacionales.

Prefiere estructuras nominales y términos clave, por ejemplo:

"clasificación de actividad económica clase de riesgo"

en lugar de:

"¿a qué nivel de riesgo pertenece esta empresa según la normativa?"

Evita expresiones conversacionales como:

- "qué pasa si"
- "qué tengo que hacer"
- "a qué pertenece"
- "según la normativa"
- "quiero saber"
- "en qué nivel está"

cuando puedan sustituirse por conceptos normativos más precisos.

Evita también palabras innecesarias que no aporten capacidad de recuperación.

PRESERVACIÓN DE LA INTENCIÓN

- Conserva el sujeto y las condiciones relevantes expresadas por el usuario.
- Conserva literalmente cualquier ley, decreto, resolución, artículo, año, tabla,
  código CIIU, numeral, literal u otro identificador normativo mencionado.
- Conserva cantidades relevantes, como número de trabajadores o nivel de riesgo.
- Si el usuario indica explícitamente que pregunta como trabajador, conserva esa
  perspectiva.
- Si la consulta está formulada desde la perspectiva de la empresa o empleador,
  conserva esa perspectiva.

RESTRICCIONES

- No inventes normas.
- No inventes leyes, decretos o resoluciones.
- No inventes artículos, numerales o literales.
- No inventes códigos CIIU.
- No inventes clases o niveles de riesgo.
- No inventes obligaciones, sanciones, cifras, entidades ni requisitos.
- No asignes una actividad económica a un código CIIU que el usuario no haya dado.
- No asignes una clase de riesgo: tu tarea es formular consultas para recuperarla.
- No agregues una norma concreta si el usuario no la mencionó.
- Si no existe una equivalencia técnica o normativa suficientemente clara para una
  expresión del usuario, conserva esa expresión en lugar de inventar una categoría.
- No repitas literalmente la consulta original.
- No generes variantes que solo cambien el orden de las mismas palabras.
- No respondas la consulta.

EJEMPLOS

Usuario:
¿Cada cuánto toca capacitar al comité de seguridad?

Consultas:
capacitación COPASST periodicidad
formación del Comité Paritario de Seguridad y Salud en el Trabajo frecuencia
periodicidad de capacitación del COPASST

Usuario:
¿Qué documentos debo guardar del sistema de seguridad y salud?

Consultas:
conservación de documentación del SG-SST
retención documental del Sistema de Gestión de Seguridad y Salud en el Trabajo
documentación del SG-SST conservación y custodia

Usuario:
Una empresa de contabilidad, ¿a qué nivel de riesgo pertenece?

Consultas:
actividad económica de servicios contables clasificación clase de riesgo
clasificación de actividades económicas servicios de contabilidad Sistema General de Riesgos Laborales
servicios contables actividad económica clase de riesgo laboral

Usuario:
Tengo 8 trabajadores y soy riesgo I, ¿qué debo cumplir?

Consultas:
estándares mínimos SG-SST empresa de 8 trabajadores riesgo I
requisitos de estándares mínimos empresa hasta 10 trabajadores clase de riesgo I
cumplimiento de estándares mínimos SG-SST número de trabajadores riesgo I

Usuario:
¿Qué debe hacer mi empresa si un trabajador se accidenta?

Consultas:
obligaciones del empleador ante accidente de trabajo
investigación de accidente de trabajo responsabilidades del empleador
actuaciones del empleador frente a accidente de trabajo

Usuario:
El código CIIU 6920, ¿a qué actividad pertenece y cuál es su riesgo?

Consultas:
código CIIU 6920 actividad económica clase de riesgo
clasificación de actividad económica código CIIU 6920 Sistema General de Riesgos Laborales
código CIIU 6920 clasificación de actividades económicas riesgo laboral

FORMATO DE SALIDA

Devuelve únicamente las 3 consultas.

Una consulta por línea.

Sin numeración.
Sin viñetas.
Sin comillas.
Sin etiquetas.
Sin explicaciones.
""".strip()


# Multi-Query implementation.

def generate_query_variants_node(llm: Any, max_variants: int) -> Callable[[RagGraphState], RagGraphState]:
    """Generate query variants."""

    def run(state: RagGraphState) -> RagGraphState:
        question = state["question"]
        if not question.strip():
            return multi_query_fallback(question, "blank_question")

        try:
            raw_text = invoke_llm_text(
                llm,
                build_multi_query_messages(question.strip(), max_variants)
            )

            variants = parse_query_variants(raw_text, question, max_variants)
        except Exception as error:
            return multi_query_fallback(question, type(error).__name__)

        if not variants:
            return multi_query_fallback(question, "blank_model_output")

        query_variants = [question, *variants]
        return {
            "query_variants": query_variants,
            "multi_query_trace": {
                "variant_count": len(query_variants),
                "generated_count": len(query_variants) - 1,
                "fallback": False,
                "error": None,
            },
        }

    return run

def build_multi_query_messages(question: str, max_variants: int) -> list[Any]:
    """Build lazy-imported LangChain messages for query variant generation."""

    # pyrefly: ignore [missing-import]
    from langchain_core.messages import HumanMessage, SystemMessage

    instruction = (
        f"Genera máximo {max_variants} consultas alternativas para esta pregunta. "
        "Devuelve una consulta por línea.\n\n"
        f"Pregunta original:\n{question}"
    )
    return [
        SystemMessage(content=MULTI_QUERY_SYSTEM_PROMPT),
        HumanMessage(content=instruction),
    ]


def parse_query_variants(raw_text: str, original_question: str, max_variants: int) -> list[str]:
    """Parse line-based model output into unique query variants."""

    original = original_question.strip()
    variants: list[str] = []
    for raw_line in raw_text.splitlines():
        variant = clean_variant_line(raw_line)
        if not variant or variant == original or variant in variants:
            continue
        variants.append(variant)
        if len(variants) >= max_variants:
            break
    return variants

def clean_variant_line(raw_line: str) -> str:
    """Remove simple list markers and wrapping quotes from one model-output line."""

    variant = raw_line.strip()
    variant = re.sub(r"^(?:\d+[\.)]|[-*])\s*", "", variant).strip()
    return variant.strip('"“”\'‘’').strip()


def multi_query_fallback(question: str, error: str) -> RagGraphState:
    """Use only the original question when multi-query generation fails."""

    return {
        "query_variants": [question],
        "multi_query_trace": {
            "variant_count": 1,
            "generated_count": 0,
            "fallback": True,
            "error": error,
        },
    }
