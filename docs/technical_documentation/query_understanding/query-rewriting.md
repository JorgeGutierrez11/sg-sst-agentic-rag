# Query Rewriting para recuperación normativa

Query Rewriting transforma la pregunta natural del usuario en una consulta más adecuada para recuperación semántica sobre el corpus normativo de SG-SST colombiano. La técnica mejora el vocabulario usado por el retriever sin cambiar la pregunta original que se entrega al generador de respuesta.

## Propósito

La consulta del usuario puede llegar con expresiones coloquiales, ambiguas o poco cercanas al lenguaje jurídico/técnico del corpus. El nodo de reescritura convierte esa entrada en una consulta breve, formal y orientada a recuperación, por ejemplo sustituyendo expresiones como “me lastimé trabajando” por “accidente de trabajo”.

La generación de respuesta sigue usando `state["question"]`. Solo la recuperación usa `state.get("retrieval_query") or state["question"]`.

## Ubicación en el pipeline LangGraph

En el flujo actual, `rewrite_query` se ejecuta antes de `retrieve`:

```text
rewrite_query -> retrieve -> normalize_documents -> record_retrieval_trace
               -> format_context/build_messages/generate_answer o fallback_answer
               -> format_result
```

Archivos principales:

- `agents/consulta_normativa/langchain_rag/query_understanding/rewrite_query.py`
- `agents/consulta_normativa/langchain_rag/graph.py`
- `agents/consulta_normativa/langchain_rag/core/state.py`

## Resumen de implementación

`rewrite_query_node(llm)` construye un nodo LangGraph que:

1. Lee `state["question"]`.
2. Normaliza espacios con `strip()` para validar si hay contenido real.
3. Invoca el LLM mediante `invoke_llm_text(llm, messages)`.
4. Construye los mensajes con `build_query_rewrite_messages(question)` usando imports diferidos de `langchain_core.messages`.
5. Escribe `retrieval_query` y `query_rewrite_trace` en el estado.

El prompt del sistema está especializado en SG-SST colombiano e incluye:

- corpus normativo disponible;
- instrucción de no responder la pregunta;
- conversión a registro formal/normativo;
- preservación literal de normas, artículos, años, tablas, códigos CIIU y otros identificadores;
- prohibición de inventar normas, obligaciones, cifras, entidades o requisitos;
- regla de audiencia por defecto: si la pregunta no especifica perspectiva, se orienta hacia el responsable SG-SST/empleador; si el usuario explicita que pregunta como trabajador, conserva esa perspectiva.

## Decisiones y guardrails importantes

| Aspecto | Implementación actual |
|---|---|
| Separación recuperación/respuesta | `retrieval_query` solo afecta la recuperación. `build_messages_node` arma el prompt final con `state["question"]`. |
| Preservación normativa | El prompt exige conservar identificadores normativos mencionados por el usuario. |
| No expansión especulativa | El prompt prohíbe agregar normas, códigos CIIU, obligaciones o requisitos no mencionados. |
| Observabilidad | `query_rewrite_trace` permite saber si la consulta cambió y si hubo fallback. |
| Dependencias opcionales | Los mensajes de LangChain se importan dentro de `build_query_rewrite_messages`, no al cargar el módulo. |

## Campos de estado

| Campo | Uso |
|---|---|
| `question` | Pregunta original del usuario. Es obligatoria para el nodo. |
| `retrieval_query` | Consulta reescrita para el retriever. Si falla la reescritura, contiene la pregunta original. |
| `query_rewrite_trace` | Traza de observabilidad/evaluación: `changed`, `fallback`, `error`. No es requerida para que el resto del pipeline ejecute. |
| `raw_results` | Resultado crudo de recuperación escrito por `retrieve_node`. |
| `documents` | Documentos normalizados usados por las etapas posteriores. |

## Fallos y comportamiento fallback

La función `fallback_rewrite(question, error)` conserva la pregunta original como consulta de recuperación:

```python
{"retrieval_query": question, "query_rewrite_trace": {...}}
```

Casos cubiertos:

- pregunta en blanco: `error = "blank_question"`, no invoca el LLM;
- salida vacía del modelo: `error = "blank_model_output"`;
- excepción al invocar el LLM: `error = type(error).__name__` y se registra un log de error.

Este fallback evita que una falla de reescritura bloquee el RAG: el sistema recupera con la pregunta original.

## Ejemplo de integración en LangGraph

```python
from typing import Any
from collections.abc import Callable

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
from agents.consulta_normativa.langchain_rag.query_understanding.rewrite_query import rewrite_query_node

Retriever = Callable[[str, int], dict[str, Any]]


def retrieve_node(retriever: Retriever, top_k: int) -> Callable[[RagGraphState], RagGraphState]:
    def run(state: RagGraphState) -> RagGraphState:
        retrieval_query = state.get("retrieval_query") or state["question"]
        return {"raw_results": retriever(retrieval_query, top_k)}

    return run


def build_langgraph_rag_with_rewrite(
    llm: Any,
    retriever: Retriever,
    top_k: int = DEFAULT_TOP_K,
) -> Any:
    from langgraph.graph import END, StateGraph

    workflow = StateGraph(RagGraphState)

    #Query Understanding
    workflow.add_node("rewrite_query", rewrite_query_node(llm))
    
    #Retrieval
    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)
    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)
    
    #Response Generation
    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)
    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))
    workflow.add_node("format_result", format_result_node)

    workflow.set_entry_point("rewrite_query")
    workflow.add_edge("rewrite_query", "retrieve")
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
