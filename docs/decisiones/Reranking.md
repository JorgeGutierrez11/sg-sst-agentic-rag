# Plan de implementación — Reranking post-recuperación

## Objetivo

Agregar un nodo experimental de reranking para reordenar candidatos ya recuperados según su
relevancia semántica frente a la consulta. Este plan **no reemplaza** Multi-Query + RRF: se inserta
después de la recuperación/fusión y antes de que el grafo decida si hay evidencia suficiente.

El reranking responde una pregunta distinta a RRF:

- RRF fusiona rankings por posición, sin entender semánticamente el par consulta-documento.
- El reranker evalúa cada par `(consulta, documento)` con un CrossEncoder y reordena por score.

## Decisión principal

Implementar reranking como módulo independiente en:

```text
agents/consulta_normativa/langchain_rag/retrieval/reranking.py
```

El nodo debe ser insertable en cualquier flujo que ya haya producido `state["documents"]`:

```text
recuperación simple → rerank → evidence_route → ...
multi-query + rrf → rerank → evidence_route → ...
hybrid retrieval futuro → rerank → evidence_route → ...
```

No debe depender de Multi-Query, RRF ni del grafo base.

## Documentación revisada

La documentación actual de `sentence-transformers` muestra dos rutas válidas para CrossEncoder:

```python
scores = model.predict([(query, passage) for passage in passages])
```

y:

```python
ranks = model.rank(query, passages, return_documents=True)
```

Para este proyecto se prefiere `predict(...)` porque permite mantener la lista original de
`RetrievedDocument` y ordenar nosotros mismos sin transformar a tipos externos.

## Fuera de alcance

- No implementar reranking en el grafo base como default.
- No cambiar `LangChainRagResult`.
- No cambiar `RetrievedDocument` todavía.
- No agregar scores al contexto mostrado al usuario.
- No hacer llamadas a Groq ni usar LLM para reranking.
- No descargar ni ejecutar el modelo real en tests.

## Modelo recomendado

```python
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
```

Motivo:

- Es multilingüe, útil para consultas y documentos en español.
- Corre localmente vía `sentence-transformers`.
- No consume tokens de Groq, que ya es un cuello de botella del proyecto.

Riesgo: puede descargar un modelo grande y aumentar latencia, especialmente sin GPU. Por eso debe
entrar como experimento medido, no como default silencioso.

## Configuración

Agregar a `config.py` cuando se implemente:

```python
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
RERANKER_MAX_LENGTH = 512
RERANKER_CANDIDATE_POOL_SIZE = 15
RERANKER_FINAL_TOP_K = DEFAULT_TOP_K
```

Decisión:

- `RERANKER_CANDIDATE_POOL_SIZE` debe ser mayor que `DEFAULT_TOP_K` para que el reranker tenga
  margen real de reordenamiento.
- `RERANKER_FINAL_TOP_K` debe quedarse igual a `DEFAULT_TOP_K` para comparar de forma justa contra
  el baseline.

## Estado requerido

`RagGraphState` ya tiene `documents`. Agregar solo si se necesita trazabilidad interna:

```python
reranking_trace: dict[str, Any]
```

No agregar `reranked_documents`: el contrato interno debe seguir siendo `documents` para que los
nodos posteriores (`evidence_route`, `format_context`, `build_messages`) no sepan si hubo reranking.

## `retrieval/reranking.py`

Funciones propuestas:

```python
def get_reranker(model_name: str, max_length: int) -> Any:
    """Load and cache a CrossEncoder reranker lazily."""


def document_text_for_reranking(document: RetrievedDocument) -> str:
    """Return the text sent to the reranker for one candidate."""


def rerank_documents(
    query: str,
    documents: list[RetrievedDocument],
    reranker: Any,
    final_top_k: int,
) -> list[RetrievedDocument]:
    """Score query/document pairs and return the top documents by descending score."""


def rerank_node(
    reranker: Any,
    candidate_pool_size: int,
    final_top_k: int,
) -> Callable[[RagGraphState], RagGraphState]:
    """Rerank state['documents'] and write the selected documents back to state['documents']."""
```

## Query usada para reranking

Usar la consulta más cercana a recuperación:

```python
query = state.get("retrieval_query") or state["question"]
```

Para Multi-Query + RRF, la pregunta original puede ser más representativa que una sola variante.
Por eso el builder experimental puede decidir explícitamente si usa:

- `question` para evaluar relevancia contra la necesidad original; o
- `retrieval_query` cuando venga del rewrite simple.

Decisión recomendada inicial:

```python
query = state["question"]
```

Motivo: el reranker debe seleccionar documentos que respondan la necesidad original del usuario, no
solo una variante de búsqueda.

## Texto del documento para reranking

Usar únicamente:

```python
document.document
```

No incluir todo el bloque de metadata al principio. Motivo: el reranker debe evaluar relevancia del
contenido normativo, no sobreponderar referencias como “Resolución 0312” o “tabla”.

Si luego se observa que el modelo pierde señales legales importantes, evaluar una versión con una
línea corta de referencia normativa, pero no en la primera implementación.

## Manejo de errores

Reranking debe tener fallback conservador:

```python
return {"documents": documents[:final_top_k], "reranking_trace": {"fallback": True, "error": type(error).__name__}}
```

Motivo: si falla la carga local del modelo o `predict`, el RAG no debe caerse. Debe degradar al orden
de recuperación/fusión ya existente.

## Wiring recomendado

### Con Multi-Query + RRF

```text
generate_query_variants
  → retrieve_variant fan-out
  → rrf_fuse
  → rerank
  → record_retrieval_trace
  → evidence_route
```

### Con recuperación simple

```text
rewrite_query
  → retrieve
  → normalize_documents
  → rerank
  → record_retrieval_trace
  → evidence_route
```

No activar en el builder base todavía. Crear builder alterno cuando se quiera comparar:

```python
build_langgraph_rag_with_reranking(...)
build_langgraph_rag_multiquery_rrf_with_reranking(...)
```

## Relación con Multi-Query + RRF

El plan Multi-Query + RRF debe entregar un pool mayor al reranker si este se conecta después:

```python
MULTIQUERY_RRF_TOP_K = 15  # o 20, según latencia medida
```

Luego el reranker reduce a:

```python
RERANKER_FINAL_TOP_K = DEFAULT_TOP_K
```

Esto evita un error común: fusionar a solo 3 documentos y luego pretender que el reranker mejore
algo. Sin candidatos suficientes, no hay margen real de mejora.

## Tests requeridos

Crear:

```text
agents/consulta_normativa/tests/test_langchain_rag_reranking.py
```

Casos mínimos:

- `rerank_documents` ordena por scores descendentes usando un fake reranker.
- `rerank_documents` conserva objetos `RetrievedDocument`, no crea modelos nuevos.
- `rerank_node` escribe en `documents`, no en otro campo.
- `rerank_node` limita a `final_top_k`.
- `rerank_node` usa fallback si `predict` lanza excepción.
- `get_reranker` importa `sentence_transformers.CrossEncoder` de forma perezosa.
- Tests no descargan ni cargan el modelo real.

## Verificación

```bash
python -m unittest \
  agents.consulta_normativa.tests.test_langchain_rag_reranking \
  agents.consulta_normativa.tests.test_langchain_rag_fusion \
  agents.consulta_normativa.tests.test_langchain_rag_graph
```

```bash
python -m compileall agents/consulta_normativa/langchain_rag agents/consulta_normativa/tests
```

## Criterios de aceptación

- Reranking vive en `retrieval/reranking.py`.
- No hay llamadas a Groq ni LLM.
- `sentence-transformers` se importa perezosamente.
- El nodo lee candidatos desde `state["documents"]` y escribe el resultado final en el mismo campo.
- Si falla, degrada al orden previo sin romper el RAG.
- El builder base no cambia por defecto.
- No se modifica `LangChainRagResult`.

## Decisiones pendientes antes de implementar

1. Confirmar si se quiere medir primero reranking sobre recuperación simple o sobre Multi-Query + RRF.
2. Confirmar `RERANKER_CANDIDATE_POOL_SIZE` inicial según latencia aceptable del equipo.
3. Confirmar si la descarga local del modelo es viable en el entorno final de ejecución.
