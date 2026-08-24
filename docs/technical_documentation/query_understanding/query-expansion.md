# LLM-Based Query Expansion para recuperación normativa

LLM-Based Query Expansion normaliza la pregunta del usuario y, cuando aporta valor, añade términos normativos controlados para mejorar la recuperación semántica sobre el corpus SG-SST colombiano. La técnica conserva la pregunta original para la generación de respuesta y usa la consulta expandida solo para recuperación.

## Propósito

La consulta del usuario puede ser coloquial, incompleta o no usar el vocabulario normativo exacto del corpus. Query Expansion busca acercar esa consulta al lenguaje técnico de SG-SST y ampliar la cobertura de búsqueda con pocos términos relevantes.

El objetivo no es responder la pregunta ni generar múltiples consultas. El objetivo es producir una sola consulta de recuperación más rica, sin cambiar la intención original del usuario.

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
3. Invoca el LLM mediante `invoke_llm_text(llm, messages)`.
4. Construye los mensajes con `build_query_expansion_messages(question)` usando imports diferidos de `langchain_core.messages`.
5. Valida la salida con guardrails determinísticos.
6. Escribe `retrieval_query` y `query_expansion_trace` en el estado.

El prompt del sistema está especializado en SG-SST colombiano e incluye:

- corpus normativo disponible;
- normalización de expresiones coloquiales hacia términos técnicos;
- adición máxima de dos términos normativos estrechamente relacionados;
- preservación literal de normas, artículos, años, tablas, códigos CIIU y otros identificadores;
- prohibición de inventar normas, obligaciones, cifras, entidades o requisitos;
- regla de audiencia por defecto: si la pregunta no especifica perspectiva, se orienta hacia el responsable SG-SST/empleador; si el usuario explicita que pregunta como trabajador, conserva esa perspectiva.

## Decisiones y guardrails importantes

| Aspecto | Implementación actual |
|---|---|
| Técnica activa | `build_langgraph_rag(...)` registra `expand_query` como nodo de query understanding antes de recuperación. |
| Separación recuperación/respuesta | `retrieval_query` solo afecta la recuperación. `build_messages_node` arma el prompt final con `state["question"]`. |
| Expansión controlada | El prompt permite máximo dos términos normativos adicionales y prohíbe agregar normas o CIIU no mencionados. |
| Preservación de identificadores | `_preserves_citations` exige que los identificadores citables del original y la expansión sean iguales. |
| Límite de expansión | `_added_words` limita palabras nuevas con `MAX_ADDED_WORDS` como proxy generoso, no como conteo exacto de términos conceptuales. |
| Observabilidad | `query_expansion_trace` incluye `technique = "llm_query_expansion"`, `changed`, `fallback` y `error`. |
| Dependencias opcionales | Los mensajes de LangChain se importan dentro de `build_query_expansion_messages`, no al cargar el módulo. |

## Guardrail de identificadores normativos

`NORMATIVE_CITATION_PATTERN` protege identificadores que no deben perderse ni aparecer si el usuario no los mencionó explícitamente.

Actualmente cubre:

- leyes, decretos, resoluciones, artículos, tablas, capítulos y títulos con número;
- años de cuatro dígitos;
- códigos CIIU, incluyendo formas como `CIIU 6920` y `código CIIU 4711`;
- numerales, por ejemplo `numeral 4.1`;
- literales, por ejemplo `literal a`;
- parágrafos, por ejemplo `parágrafo 1`.

Este guardrail no decide si la expansión es buena; solo evita que el LLM pierda o invente identificadores normativos citables.

## Campos de estado

| Campo | Uso |
|---|---|
| `question` | Pregunta original del usuario. Es obligatoria para el nodo. |
| `retrieval_query` | Consulta expandida usada por el retriever. Si falla la expansión, contiene la pregunta original. |
| `query_expansion_trace` | Traza de observabilidad/evaluación: `technique`, `changed`, `fallback`, `error`. |
| `raw_results` | Resultado crudo de recuperación escrito por `retrieve_node`. |
| `documents` | Documentos normalizados usados por las etapas posteriores. |

`query_expansion_trace` está separado de `query_rewrite_trace` para que la evaluación pueda distinguir qué técnica de comprensión de consulta produjo cada resultado.

## Fallos y comportamiento fallback

La función `fallback_expansion(question, error)` conserva la pregunta original como consulta de recuperación:

```python
{
    "retrieval_query": question,
    "query_expansion_trace": {
        "technique": "llm_query_expansion",
        "changed": False,
        "fallback": True,
        "error": error,
    },
}
```

Casos cubiertos:

- pregunta en blanco: `error = "blank_question"`, no invoca el LLM;
- salida vacía del modelo: `error = "blank_model_output"`;
- excepción al invocar el LLM: `error = type(error).__name__` y se registra un log de error;
- violación de guardrails: `error = "guardrail_violation"`.

Este fallback evita que una falla de expansión bloquee el RAG: el sistema recupera con la pregunta original.

## Notas operativas y de evaluación

- Es una técnica de query understanding: debe compararse contra Query Rewriting y Multi-Query + RRF usando métricas de contexto relevante, fidelidad y relevancia de respuesta.
- No debe evaluarse como mejora de generación: la respuesta sigue dependiendo del contexto recuperado y del prompt final.
- Revisar `query_expansion_trace` para medir cambios, fallbacks y bloqueos por guardrail.
- Ajustar `MAX_ADDED_WORDS` solo después de revisar expansiones reales sobre preguntas de prueba; el valor actual es un proxy, no una garantía semántica perfecta.
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
