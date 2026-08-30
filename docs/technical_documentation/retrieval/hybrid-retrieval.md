# Hybrid Retrieval con Chroma + BM25 + RRF para recuperación normativa

Hybrid Retrieval combina recuperación densa con Chroma y recuperación dispersa con BM25 para la misma consulta. Ambas ramas recuperan candidatos de forma independiente y luego sus rankings se fusionan con Reciprocal Rank Fusion (RRF) antes de construir el contexto enviado al LLM.

## Propósito

El objetivo no es generar respuestas ni reconstruir índices. El objetivo es mejorar la evidencia recuperada combinando señales semánticas y léxicas en un único ranking de documentos normativos.

La técnica opera solo en tiempo de consulta: abre índices existentes, consulta Chroma y BM25, fusiona candidatos y devuelve el mismo contrato de resultados que consume el grafo LangGraph.

## Ubicación en el pipeline LangGraph

El runtime activo construye un retriever híbrido antes del nodo `retrieve`. Para el grafo, el contrato permanece estable: `Callable[[str, int], dict[str, Any]]`.

```text
question -> hybrid_retriever(query, top_k)
             ├─ Chroma query_top_k(query, HYBRID_CANDIDATE_TOP_K)
             ├─ BM25 query_top_k(query, HYBRID_CANDIDATE_TOP_K)
             └─ RRF -> top_k final
         -> retrieve -> normalize_documents -> record_retrieval_trace
         -> format_context/build_messages/generate_answer o fallback_answer
         -> format_result
```

La posición es importante: Hybrid Retrieval reemplaza la fuente de candidatos del retriever, pero no cambia los nodos posteriores. `build_langgraph_rag(...)` sigue recibiendo un retriever compatible y controla el `top_k` final con `RETRIEVAL_TOP_K`.

Archivos principales:

- `agents/shared/hybrid_retrieval.py`
- `agents/shared/chroma_retrieval.py`
- `agents/shared/bm25_retrieval.py`
- `agents/consulta_normativa/langchain_rag/config.py`
- `agents/consulta_normativa/langchain_rag/main.py`
- `agents/consulta_normativa/langchain_rag/formatting.py`
- `agents/consulta_normativa/langchain_rag/retrieval/fusion.py`

## Resumen de implementación

La técnica se divide en estas piezas:

| Pieza | Responsabilidad |
|---|---|
| `hybrid_retriever(dense_collection, sparse_index, candidate_top_k, rrf_k)` | Construye un retriever compatible con LangGraph que consulta Chroma y BM25 con la misma pregunta y fusiona sus rankings. |
| `chroma_retrieval.query_top_k(collection, question, top_k)` | Ejecuta recuperación densa en Chroma y devuelve `ids`, `documents`, `metadatas` y `distances`. |
| `bm25_retrieval.query_top_k(index, question, top_k)` | Ejecuta recuperación dispersa BM25 con tokenización en español y devuelve `ids`, `documents`, `metadatas` y `scores`. |
| `recovered_documents(results)` | Normaliza resultados crudos en objetos `RetrievedDocument` y conserva un `_document_id` cuando existe un id de resultado. |
| `reciprocal_rank_fusion(ranked_lists, k)` | Fusiona listas rankeadas sin mezclar scores heterogéneos; deduplica por identidad canónica y ordena por score RRF. |
| `documents_to_raw_results(documents)` | Convierte los documentos fusionados de vuelta al shape crudo `ids/documents/metadatas` esperado por el grafo. |

El resultado final no incluye `distances` ni `scores`: después de RRF solo se conserva el ranking fusionado y la metadata necesaria para formato, referencias y trazabilidad interna.

## Parámetros de configuración

Valores definidos en `agents/consulta_normativa/langchain_rag/config.py`:

| Parámetro | Uso |
|---|---|
| `RETRIEVAL_TOP_K` | Autoridad final sobre cuántos documentos entran al contexto del grafo. |
| `HYBRID_CANDIDATE_TOP_K` | Tamaño del pool de candidatos que recupera cada motor antes de la fusión. |
| `HYBRID_RRF_K` | Parámetro `k` usado por Hybrid Retrieval para RRF. Actualmente hereda de `RRF_K`. |
| `RRF_K` | Valor base de RRF compartido con otras técnicas que usan fusión por ranking. |

## Decisiones y guardrails importantes

| Aspecto | Implementación actual |
|---|---|
| Autoridad de `top_k` final | `RETRIEVAL_TOP_K` se pasa a `build_langgraph_rag(...)` y limita la cantidad final de documentos usados por el grafo. |
| Pool por motor | Chroma y BM25 recuperan `HYBRID_CANDIDATE_TOP_K` candidatos cada uno para dar margen a la fusión. |
| Sin mezcla de scores | No se combinan `distances` de Chroma con `scores` de BM25; RRF usa posiciones de ranking. |
| Identidad canónica | La deduplicación usa `_document_id`, luego `document_id` y finalmente un fallback basado en referencia y hash del texto. |
| Trazabilidad de fuente | Solo `_retrieval_sources` indica si el documento apareció por `chroma`, `bm25` o ambos. |
| Errores operativos | Fallas de consulta o de apertura de índices se propagan como errores operativos; no se silencian dentro del retriever híbrido. |


## Metadata interna

| Campo | Uso |
|---|---|
| `_document_id` | Identidad técnica normalizada desde el id del resultado cuando el motor no entrega una metadata canónica explícita. |
| `document_id` | Identidad canónica persistida en metadata cuando existe en los documentos indexados. |
| `_retrieval_sources` | Lista interna de observabilidad con las ramas que recuperaron el documento: `chroma`, `bm25` o ambas. |

`_retrieval_sources` es metadata interna de trazabilidad y evaluación. No debe interpretarse como evidencia normativa para el LLM ni como parte del contenido legal recuperado.

## Fallos y comportamiento fallback

Hybrid Retrieval conserva un comportamiento explícito ante ramas vacías y errores:

- si `top_k <= 0`, devuelve un resultado vacío con shape `ids/documents/metadatas`;
- si Chroma y BM25 no recuperan documentos, devuelve el mismo shape vacío;
- si una rama no recupera documentos, la fusión usa los documentos de la otra rama;
- si Chroma o BM25 fallan durante la consulta, el error se propaga;
- si faltan el índice Chroma o el índice BM25, es un error de preparación operativa, no un fallback funcional.

## Notas operativas y de evaluación

- Los índices de Chroma y BM25 deben existir antes de ejecutar el agente; esta técnica no los crea ni los reconstruye.
- Si cambia la metadata usada para identidad, referencias o filtrado, se deben regenerar los artefactos vectoriales y reconstruir ambos índices.
- Evaluar Hybrid Retrieval contra baselines Chroma-only y BM25-only para separar el aporte de la fusión.
- Validar que el top-k final mantenga suficiente evidencia sin saturar el contexto del LLM.
- Pruebas enfocadas: `python -m unittest agents.consulta_normativa.tests.test_hybrid_retrieval agents.consulta_normativa.tests.test_langchain_rag_main`.

## Ejemplo de integración

```python
from agents.consulta_normativa.langchain_rag.config import (
    DEFAULT_CHROMA_PATH,
    DEFAULT_COLLECTION_NAME,
    HYBRID_CANDIDATE_TOP_K,
    HYBRID_RRF_K,
    RETRIEVAL_TOP_K,
)
from agents.consulta_normativa.langchain_rag.graph import build_langgraph_rag
from agents.shared.bm25_retrieval import DEFAULT_BM25_PATH, open_existing_index
from agents.shared.chroma_retrieval import open_existing_collection
from agents.shared.hybrid_retrieval import hybrid_retriever

collection = open_existing_collection(DEFAULT_CHROMA_PATH, DEFAULT_COLLECTION_NAME)
sparse_index = open_existing_index(DEFAULT_BM25_PATH)

retriever = hybrid_retriever(
    collection,
    sparse_index,
    candidate_top_k=HYBRID_CANDIDATE_TOP_K,
    rrf_k=HYBRID_RRF_K,
)

graph = build_langgraph_rag(llm, retriever, top_k=RETRIEVAL_TOP_K)
```
