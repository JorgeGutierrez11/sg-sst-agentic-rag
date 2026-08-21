# Multi-Query + Reciprocal Rank Fusion para recuperación normativa

Multi-Query + RRF es una técnica experimental de query understanding y fusión de resultados. Genera variantes de la pregunta, recupera documentos por cada variante y fusiona los rankings con Reciprocal Rank Fusion para mejorar el recall en preguntas ambiguas o con múltiples formulaciones posibles.

## Propósito

La recuperación semántica puede fallar cuando la pregunta del usuario no coincide bien con el vocabulario del corpus. Multi-Query intenta cubrir varias formulaciones equivalentes de la misma necesidad de información.

El objetivo no es responder varias subpreguntas, sino recuperar mejor evidencia para una sola pregunta original.

## Ubicación en el pipeline LangGraph

El flujo experimental reemplaza la recuperación simple por generación de variantes, fan-out de recuperación y fusión RRF:

```text
generate_query_variants -> retrieve_variant* -> rrf_fuse -> record_retrieval_trace
                         -> format_context/build_messages/generate_answer o fallback_answer
                         -> format_result
```

Archivos principales:

- `agents/consulta_normativa/langchain_rag/query_understanding/multi_query.py`
- `agents/consulta_normativa/langchain_rag/retrieval/fusion.py`
- `agents/consulta_normativa/langchain_rag/graph.py`
- `agents/consulta_normativa/langchain_rag/config.py`
- `agents/consulta_normativa/langchain_rag/core/state.py`

## Resumen de implementación

La técnica se divide en cuatro piezas:

| Pieza | Responsabilidad |
|---|---|
| `generate_query_variants_node(llm, max_variants)` | Genera variantes con el LLM y escribe `query_variants`. Incluye siempre la pregunta original como primera variante. |
| `fanout_retrieve_variants(state)` | Crea un `Send("retrieve_variant", {"query": query})` por cada variante. |
| `retrieve_variant_node(retriever, top_k)` | Ejecuta el retriever para una variante y normaliza resultados con `recovered_documents`. |
| `rrf_fuse_node(rrf_k, top_k)` | Fusiona listas con `reciprocal_rank_fusion` y escribe los documentos finales en `documents`. |

El prompt de variantes está especializado en SG-SST colombiano y solicita consultas alternativas orientadas a vocabulario normativo/técnico. La salida esperada es una consulta por línea, sin numeración ni explicaciones.

## Parámetros de configuración

Valores definidos en `agents/consulta_normativa/langchain_rag/config.py`:

| Parámetro | Valor actual | Uso |
|---|---:|---|
| `MULTI_QUERY_MAX_VARIANTS` | `3` | Máximo de variantes generadas por el LLM. |
| `MULTI_QUERY_TOP_K_PER_VARIANT` | `DEFAULT_TOP_K` (`3`) | Documentos recuperados por cada variante. |
| `MULTIQUERY_RRF_TOP_K` | `DEFAULT_TOP_K` (`3`) | Documentos finales después de la fusión RRF. |
| `RRF_K` | `60` | Constante de ponderación en `1 / (k + rank)`. |

## Decisiones y guardrails importantes

| Aspecto | Implementación actual |
|---|---|
| Técnica experimental | El builder separado `build_langgraph_rag_multiquery_rrf(...)` mantiene aislado el flujo Multi-Query + RRF del RAG base. |
| Pregunta original incluida | `query_variants` inicia con `question`, seguida de variantes generadas. Así la recuperación no depende únicamente del LLM. |
| Variación controlada | El parser elimina líneas vacías, marcadores simples, comillas envolventes, duplicados y variantes iguales a la pregunta original. |
| Fan-out con LangGraph | `fanout_retrieve_variants` usa `langgraph.types.Send` para ejecutar recuperación por variante. |
| Acumulación de listas | `retrieved_lists` usa `Annotated[..., add]` en `RagGraphState` para combinar resultados de los workers. |
| Deduplicación RRF | `document_identity` usa `_chroma_id` si existe; si no, usa referencia derivada de metadata más hash del texto. |
| Estabilidad de orden | En empates, RRF conserva prioridad por primer encuentro (`first_seen`). |

## Campos de estado

| Campo | Uso |
|---|---|
| `question` | Pregunta original. También se incluye como primera variante. |
| `query_variants` | Lista de consultas a recuperar: pregunta original + variantes generadas. |
| `multi_query_trace` | Traza de observabilidad/evaluación: `variant_count`, `generated_count`, `fallback`, `error`. |
| `retrieved_lists` | Listas de `RetrievedDocument` recuperadas por variante. Se acumulan con reducer `add`. |
| `documents` | Resultado final fusionado y recortado a `top_k`. |
| `retrieval_traces` | Traza posterior de conteo de documentos recuperados. |

## Fallos y comportamiento fallback

La generación de variantes sí tiene fallback propio mediante `multi_query_fallback(question, error)`:

- pregunta en blanco: devuelve `query_variants = [question]` sin invocar el LLM;
- excepción del LLM: devuelve solo la pregunta original y registra el tipo de error;
- salida sin variantes válidas: devuelve solo la pregunta original con `error = "blank_model_output"`.

Después de ese punto no hay un fallback específico adicional para RRF. Si la recuperación o la fusión no producen evidencia útil, aplica el enrutamiento existente por evidencia: `record_retrieval_trace_node` + `evidence_route` llevan a `fallback_answer_node` cuando `documents` queda vacío.

## Notas operativas y de evaluación

- Es una técnica experimental: debe compararse contra el RAG base y contra Query Rewriting usando métricas de contexto relevante, fidelidad y relevancia de respuesta.
- Medir el costo adicional: se hacen hasta `1 + max_variants` recuperaciones por pregunta.
- Revisar `multi_query_trace` para detectar fallbacks o bajo número de variantes generadas.
- Ajustar `top_k_per_variant` y `final top_k` con cuidado: valores altos aumentan recall, pero también ruido y costo de revisión/evaluación.
- Pruebas enfocadas: `python -m unittest agents.consulta_normativa.tests.test_langchain_rag_multi_query agents.consulta_normativa.tests.test_langchain_rag_fusion agents.consulta_normativa.tests.test_langchain_rag_graph`.

## Ejemplo de integración en LangGraph

El siguiente ejemplo replica la estructura actual de `build_langgraph_rag_multiquery_rrf(...)`:

```python
from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.config import (
    MULTI_QUERY_MAX_VARIANTS,
    MULTI_QUERY_TOP_K_PER_VARIANT,
    MULTIQUERY_RRF_TOP_K,
    RRF_K,
)
from agents.consulta_normativa.langchain_rag.core.instrumentation import record_retrieval_trace_node
from agents.consulta_normativa.langchain_rag.core.routes import evidence_route
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.graph import (
    build_messages_node,
    fallback_answer_node,
    format_context_node,
    format_result_node,
    generate_answer_node,
)
from agents.consulta_normativa.langchain_rag.query_understanding.multi_query import generate_query_variants_node
from agents.consulta_normativa.langchain_rag.retrieval.fusion import (
    fanout_retrieve_variants,
    retrieve_variant_node,
    rrf_fuse_node,
)

Retriever = Callable[[str, int], dict[str, Any]]


def build_langgraph_rag_multiquery_rrf(
    llm: Any,
    retriever: Retriever,
    top_k: int = MULTIQUERY_RRF_TOP_K,
    max_variants: int = MULTI_QUERY_MAX_VARIANTS,
    top_k_per_variant: int = MULTI_QUERY_TOP_K_PER_VARIANT,
    rrf_k: int = RRF_K,
) -> Any:
    from langgraph.graph import END, StateGraph

    workflow = StateGraph(RagGraphState)

    workflow.add_node("generate_query_variants", generate_query_variants_node(llm, max_variants))
    workflow.add_node("retrieve_variant", retrieve_variant_node(retriever, top_k_per_variant))
    workflow.add_node("rrf_fuse", rrf_fuse_node(rrf_k, top_k))
    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)
    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)
    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))
    workflow.add_node("format_result", format_result_node)

    workflow.set_entry_point("generate_query_variants")
    workflow.add_conditional_edges(
        "generate_query_variants",
        fanout_retrieve_variants,
        ["retrieve_variant"],
    )
    workflow.add_edge("retrieve_variant", "rrf_fuse")
    workflow.add_edge("rrf_fuse", "record_retrieval_trace")
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
