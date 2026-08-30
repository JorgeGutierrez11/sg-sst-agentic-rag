# LLM-Based Query Expansion para recuperación normativa

LLM-Based Query Expansion conserva la pregunta original y añade términos técnicos o normativos controlados para mejorar la recuperación semántica sobre el corpus SG-SST colombiano. La técnica no reescribe ni sustituye la consulta del usuario: genera términos adicionales y el sistema los anexa a la consulta usada por el retriever.

## Propósito

La consulta del usuario puede ser coloquial, incompleta o no usar el vocabulario normativo exacto del corpus. Query Expansion busca ampliar la cobertura de búsqueda con términos relevantes que ayuden a encontrar documentos donde el mismo concepto aparece con vocabulario técnico.

El objetivo no es responder la pregunta, reescribirla ni generar múltiples consultas. El objetivo es producir una sola consulta de recuperación más rica, manteniendo intacta la intención original.

## Ubicación en el pipeline LangGraph

En el flujo activo, `expand_query` se ejecuta antes de `retrieve`:

```text
expand_query -> retrieve -> normalize_documents -> record_retrieval_trace
             -> format_context/build_messages/generate_answer o fallback_answer
             -> format_result
```

La generación de respuesta sigue usando `state["question"]`. Solo la recuperación usa `state.get("retrieval_query") or state["question"]`.

Archivos principales:

- `agents/consulta_normativa/langchain_rag/query_understanding/query_expansion.py`
- `agents/consulta_normativa/langchain_rag/graph.py`
- `agents/consulta_normativa/langchain_rag/core/state.py`

## Resumen de implementación

`query_expansion_node(llm)` construye un nodo LangGraph que:

1. Lee `state["question"]`.
2. Normaliza espacios con `strip()` para validar si hay contenido real.
3. Crea un expander con `llm.with_structured_output(QueryExpansionOutput, method="function_calling")`.
4. Construye los mensajes con `build_query_expansion_messages(question)` usando imports diferidos de `langchain_core.messages`.
5. Invoca el expander estructurado y recibe `expansion_terms`.
6. Limpia términos vacíos, duplicados, ya presentes en la pregunta o inseguros.
7. Construye `retrieval_query` anexando los términos aceptados a la pregunta original.
8. Escribe `retrieval_query` y `query_expansion_trace` en el estado.

El prompt del sistema está especializado en SG-SST colombiano e incluye:

- corpus normativo disponible;
- instrucción explícita de no reescribir, reformular, sustituir ni eliminar información de la consulta original;
- generación máxima de seis términos o expresiones de expansión;
- generación de denominaciones técnicas, siglas, categorías normativas o expresiones formales relacionadas;
- regla de especificidad mínima para evitar términos amplios como `SG-SST`, `normativa`, `empresa`, `empleador` o `trabajador` cuando no discriminan documentos relevantes;
- preservación literal de normas, artículos, años, tablas, códigos CIIU y otros identificadores;
- prohibición de inventar normas, obligaciones, cifras, entidades o requisitos;
- ejemplos positivos y negativos para preguntas de clasificación de riesgo por actividad económica.

## Decisiones y guardrails importantes

| Aspecto | Implementación actual |
|---|---|
| Técnica activa | `build_langgraph_rag(...)` registra `expand_query` como nodo de query understanding antes de recuperación. |
| Separación recuperación/respuesta | `retrieval_query` solo afecta la recuperación. `build_messages_node` arma el prompt final con `state["question"]`. |
| Structured Output | `QueryExpansionOutput` define `expansion_terms: list[str]` para evitar parsing manual de texto libre. |
| Expansión controlada | El prompt permite máximo `MAX_EXPANSION_TERMS` términos y prohíbe agregar normas, CIIU, años o clasificaciones no mencionadas. |
| Limpieza determinística | `clean_expansion_terms` elimina términos vacíos, duplicados, ya presentes en la pregunta o inseguros. |
| Preservación de identificadores | `is_safe_expansion_term` rechaza términos que introducen identificadores normativos no presentes en la pregunta original. |
| Observabilidad | `query_expansion_trace` sigue el patrón de `query_rewrite_trace`: `changed`, `fallback` y `error`. |
| Dependencias opcionales | Los mensajes de LangChain se importan dentro de `build_query_expansion_messages`, no al cargar el módulo. |

## Guardrail de identificadores normativos

`NORMATIVE_IDENTIFIER_PATTERNS` protege identificadores que no deben aparecer en términos de expansión si el usuario no los mencionó explícitamente.

Actualmente cubre:

- leyes, decretos y resoluciones con número;
- años de cuatro dígitos;
- códigos CIIU, por ejemplo `CIIU 6920`;
- artículos, por ejemplo `artículo 2`;
- numerales, por ejemplo `numeral 4.1`;
- literales, por ejemplo `literal a`;
- parágrafos, por ejemplo `parágrafo 1`;
- tablas, por ejemplo `tabla 1`;
- clases de riesgo, por ejemplo `riesgo II`.

Este guardrail no decide si la expansión es buena; solo evita que el LLM agregue identificadores normativos o clasificaciones concretas no mencionadas por el usuario. Como la pregunta original siempre se conserva en `retrieval_query`, el problema principal no es perder identificadores, sino inventarlos en los términos añadidos.

## Campos de estado

| Campo | Uso |
|---|---|
| `question` | Pregunta original del usuario. Es obligatoria para el nodo. |
| `retrieval_query` | Pregunta original más términos de expansión aceptados. Si falla la expansión, contiene la pregunta original. |
| `query_expansion_trace` | Traza de observabilidad/evaluación: `changed`, `fallback`, `error`. |
| `raw_results` | Resultado crudo de recuperación escrito por `retrieve_node`. |
| `documents` | Documentos normalizados usados por las etapas posteriores. |

`query_expansion_trace` está separado de `query_rewrite_trace` para que la evaluación pueda distinguir qué técnica de comprensión de consulta produjo cada resultado.

## Fallos y comportamiento fallback

La función `fallback_expansion(question, error)` conserva la pregunta original como consulta de recuperación:

```python
{
    "retrieval_query": question,
    "query_expansion_trace": {
        "changed": False,
        "fallback": True,
        "error": error,
    },
}
```

Casos cubiertos:

- pregunta en blanco: `error = "blank_question"`, no invoca el LLM;
- excepción al invocar el expander estructurado: `error = type(error).__name__` y se registra un log de error.

Si el modelo devuelve una lista vacía o todos los términos se filtran por limpieza/guardrails, no se considera fallo operativo: `retrieval_query` queda igual a la pregunta original, `fallback = False` y `changed = False`.

Este fallback evita que una falla operativa de expansión bloquee el RAG: el sistema recupera con la pregunta original.

## Notas operativas y de evaluación

- Es una técnica de query understanding: debe compararse contra Query Rewriting y Multi-Query + RRF usando métricas de contexto relevante, fidelidad y relevancia de respuesta.
- No debe evaluarse como mejora de generación: la respuesta sigue dependiendo del contexto recuperado y del prompt final.
- Revisar `retrieval_query` para auditar qué vocabulario agregó el LLM y detectar términos demasiado generales.
- Ajustar `MAX_EXPANSION_TERMS` solo después de revisar expansiones reales sobre preguntas de prueba.
- Los guardrails regex protegen identificadores concretos, pero no reemplazan evaluación semántica ni validación experta del resultado recuperado.
- Pruebas enfocadas: `python -m unittest agents.consulta_normativa.tests.test_langchain_rag_query_expansion agents.consulta_normativa.tests.test_langchain_rag_graph`.

## Ejemplo de integración en LangGraph

El siguiente ejemplo replica la integración activa de `expand_query` antes de recuperación:

```python
from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.config import DEFAULT_TOP_K
from agents.consulta_normativa.langchain_rag.core.instrumentation import record_retrieval_trace_node
from agents.consulta_normativa.langchain_rag.core.routes import evidence_route
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.graph import (
    build_messages_node,
    fallback_answer_node,
    format_context_node,
    format_result_node,
    generate_answer_node,
    normalize_documents_node,
)
from agents.consulta_normativa.langchain_rag.query_understanding.query_expansion import query_expansion_node

Retriever = Callable[[str, int], dict[str, Any]]


def retrieve_node(retriever: Retriever, top_k: int) -> Callable[[RagGraphState], RagGraphState]:
    def run(state: RagGraphState) -> RagGraphState:
        retrieval_query = state.get("retrieval_query") or state["question"]
        return {"raw_results": retriever(retrieval_query, top_k)}

    return run


def build_langgraph_rag_with_expansion(
    llm: Any,
    retriever: Retriever,
    top_k: int = DEFAULT_TOP_K,
) -> Any:
    from langgraph.graph import END, StateGraph

    workflow = StateGraph(RagGraphState)

    # Query Understanding
    workflow.add_node("expand_query", query_expansion_node(llm))

    # Retrieval
    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)
    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)

    # Response Generation
    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)
    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))
    workflow.add_node("format_result", format_result_node)

    workflow.set_entry_point("expand_query")
    workflow.add_edge("expand_query", "retrieve")
    workflow.add_edge("retrieve", "normalize_documents")
    workflow.add_edge("normalize_documents", "record_retrieval_trace")
    workflow.add_conditional_edges(
        "record_retrieval_trace",
        evidence_route,
        {"with_evidence": "format_context", "without_evidence": "fallback_answer"},
    )
    workflow.add_edge("fallback_answer", "format_result")
    workflow.add_edge("format_context", "build_messages")
    workflow.add_edge("build_messages", "generate_answer")
    workflow.add_edge("generate_answer", "format_result")
    workflow.add_edge("format_result", END)

    return workflow.compile()
```
