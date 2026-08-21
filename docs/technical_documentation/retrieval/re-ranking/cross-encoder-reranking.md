# Re-ranking con Cross-Encoder para recuperación normativa

Re-ranking es una técnica experimental de mejora de ranking posterior a la recuperación. Toma los documentos candidatos ya recuperados, evalúa cada par `(pregunta, documento)` con un Cross-Encoder y reordena los candidatos antes de construir el contexto enviado al LLM.

## Propósito

El objetivo no es recuperar más documentos ni generar respuesta. El objetivo es seleccionar mejor evidencia entre documentos ya recuperados.

## Ubicación en el pipeline LangGraph

En un RAG base sin mejora de consulta, el re-ranking va después de recuperar y normalizar documentos, pero antes de decidir si existe evidencia suficiente:

```text
question -> retrieve -> normalize_documents -> rerank -> record_retrieval_trace
         -> format_context/build_messages/generate_answer o fallback_answer
         -> format_result
```

La posición es importante: el reranker no reemplaza la recuperación inicial. Solo reordena los candidatos que ya existen en `state["documents"]` antes de que el resto del grafo construya el contexto.

Archivos principales:

- `agents/consulta_normativa/langchain_rag/retrieval/reranking.py`
- `agents/consulta_normativa/langchain_rag/graph.py`
- `agents/consulta_normativa/langchain_rag/config.py`
- `agents/consulta_normativa/langchain_rag/core/state.py`

## Resumen de implementación

La técnica se divide en cuatro piezas:

| Pieza | Responsabilidad |
|---|---|
| `get_reranker(model_name, max_length)` | Carga `sentence_transformers.CrossEncoder` de forma perezosa y cacheada. |
| `rerank_node(reranker, candidate_pool_size, final_top_k)` | Lee `documents`, limita candidatos, resuelve el reranker, reordena y escribe nuevamente en `documents`. |
| `rerank_documents(query, documents, reranker, final_top_k)` | Ejecuta `predict` sobre pares `(query, document_text)` y ordena por score descendente. |
| `document_text_for_reranking(document)` | Define qué texto del documento se envía al Cross-Encoder. Actualmente usa solo `document.document`. |

El contrato interno se mantiene estable: los nodos posteriores siguen leyendo `state["documents"]`. No existe un campo público `reranked_documents`.

## Parámetros de configuración

Valores definidos en `agents/consulta_normativa/langchain_rag/config.py`:

| Parámetro | Uso |
|---|---|
| `RERANKER_MODEL_NAME` | Modelo Cross-Encoder local usado para puntuar pares consulta-documento. |
| `RERANKER_MAX_LENGTH` | Longitud máxima que usa el tokenizer del Cross-Encoder. |
| `RERANKER_CANDIDATE_POOL_SIZE` | Número máximo de documentos que entran al reranker. Debe ser mayor que `RERANKER_FINAL_TOP_K`. |
| `RERANKER_FINAL_TOP_K` | Número final de documentos después del re-ranking. |


## Decisiones y guardrails importantes

| Aspecto | Implementación actual |
|---|---|
| Técnica experimental | El re-ranking vive en builders alternos. No se activa en `build_langgraph_rag(...)` por defecto. |
| Modelo local | Usa `sentence-transformers` con Cross-Encoder; no llama a Groq ni a otro LLM. |
| Import perezoso | `CrossEncoder` se importa dentro de `get_reranker`, no al cargar el módulo. |
| Caché | `get_reranker` usa `lru_cache` para no recargar el mismo modelo en cada consulta. |
| Pregunta usada | El nodo usa `state["question"]`, porque el reranker debe evaluar relevancia contra la necesidad original del usuario. |
| Texto evaluado | Se envía únicamente `document.document`, sin metadata, para no sobreponderar referencias normativas. |
| Contrato de salida | El nodo sobrescribe `documents` con los documentos seleccionados y preserva los objetos `RetrievedDocument`. |
| Fallback conservador | Si falla la carga del modelo o `predict`, conserva el orden previo y recorta a `final_top_k`. |

## Campos de estado

| Campo | Uso |
|---|---|
| `question` | Pregunta original usada para puntuar pares consulta-documento. |
| `documents` | Candidatos de entrada y documentos finales después del re-ranking. |
| `reranking_trace` | Traza interna: `fallback`, `error`, `candidate_count`, `selected_count`. |
| `retrieval_traces` | Traza posterior de conteo de documentos recuperados, escrita después de `rerank`. |

`reranking_trace` es interno para observabilidad y evaluación. No cambia `LangChainRagResult` ni se muestra al usuario final.

## Fallos y comportamiento fallback

El re-ranking degrada de forma conservadora:

- sin documentos candidatos: devuelve `documents = []` sin cargar el modelo;
- falla al cargar `sentence-transformers` o el modelo local: conserva el orden previo;
- falla `predict`: conserva el orden previo;
- en fallback, recorta a `final_top_k` para mantener el contrato con los nodos posteriores.

La traza registra el tipo de error cuando existe:

```python
{
    "documents": documents[:final_top_k],
    "reranking_trace": {
        "fallback": True,
        "error": type(error).__name__,
        "candidate_count": len(documents),
        "selected_count": len(documents[:final_top_k]),
    },
}
```

## Notas operativas y de evaluación

- Es una técnica experimental: debe compararse contra RAG base y contra Multi-Query + RRF sin reranking.
- No mezclar el score del Cross-Encoder con distancia Chroma o score RRF sin calibración; son escalas distintas.
- Medir latencia: el Cross-Encoder evalúa pares consulta-documento y puede ser costoso sin GPU.
- Validar el entorno real con `sentence-transformers` instalado antes de usar el builder con modelo real.
- Pruebas enfocadas: `python -m unittest agents.consulta_normativa.tests.test_langchain_rag_reranking agents.consulta_normativa.tests.test_langchain_rag_fusion agents.consulta_normativa.tests.test_langchain_rag_graph`.

## Ejemplo de integración en LangGraph

```python
def build_langgraph_rag_multiquery_rrf_with_reranking(
    llm: Any,
    retriever: Retriever,

    # Multi-Query parameters.
    max_variants: int = MULTI_QUERY_MAX_VARIANTS,
    top_k_per_variant: int = MULTI_QUERY_TOP_K_PER_VARIANT,

    # RRF parameters.
    rrf_k: int = RRF_K,
    
    # Reranker parameters.
    candidate_pool_size: int = RERANKER_CANDIDATE_POOL_SIZE,
    final_top_k: int = RERANKER_FINAL_TOP_K,
    reranker: Any | None = None,
) -> Any:
    """Build the experimental Multi-Query + RRF pipeline with post-retrieval reranking."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)
    lazy_reranker = reranker or default_reranker_loader

    # Multi-Query implementation.
    workflow.add_node("generate_query_variants", generate_query_variants_node(llm, max_variants))
    workflow.add_node("retrieve_variant", retrieve_variant_node(retriever, top_k_per_variant))
    workflow.add_node("rrf_fuse", rrf_fuse_node(rrf_k, candidate_pool_size))
    workflow.add_node("rerank", rerank_node(lazy_reranker, candidate_pool_size, final_top_k))

    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)
    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)
    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))
    workflow.add_node("format_result", format_result_node)

    workflow.set_entry_point("generate_query_variants")
    workflow.add_conditional_edges("generate_query_variants", fanout_retrieve_variants, ["retrieve_variant"])
    workflow.add_edge("retrieve_variant", "rrf_fuse")
    workflow.add_edge("rrf_fuse", "rerank")
    workflow.add_edge("rerank", "record_retrieval_trace")
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
