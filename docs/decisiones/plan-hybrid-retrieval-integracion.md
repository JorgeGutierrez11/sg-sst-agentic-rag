# Plan de implementación Hybrid Retrieval

Este plan integra el retrieval denso existente con Chroma y el retrieval sparse existente con BM25. La integración debe mantenerse mínima: no cambia la construcción de índices, no agrega Multi-Query, no agrega reranking y no modifica el flujo generativo más allá de entregar al grafo un retriever híbrido compatible con el contrato actual.

## 1. Objetivo

Implementar **Hybrid Retrieval** combinando:

- retrieval denso actual sobre Chroma;
- retrieval sparse actual sobre BM25;
- fusión por Reciprocal Rank Fusion (RRF);
- salida compatible con el grafo LangGraph existente.

Flujo objetivo:

```text
question / retrieval_query
        ↓
hybrid retriever
        ↓
┌─────────────────────┬─────────────────────┐
│ Chroma dense top-k  │ BM25 sparse top-k   │
└──────────┬──────────┴──────────┬──────────┘
           ↓                     ↓
  normalize Chroma       normalize BM25
           └──────────┬──────────┘
                      ↓
                    RRF
                      ↓
                 final_top_k
                      ↓
        LangGraph RAG actual
```

## 2. Estado actual

### Retrieval denso actual

`agents/shared/chroma_retrieval.py` expone:

```python
open_existing_collection(persist_path, collection_name)
query_top_k(collection, question, top_k=5) -> dict[str, Any]
```

El helper runtime:

- abre una colección existente;
- no crea colecciones;
- usa `include=["documents", "metadatas", "distances"]`;
- devuelve resultados con shape compatible con Chroma:

```text
ids
documents
metadatas
distances
```

### Retrieval sparse actual

`agents/shared/bm25_retrieval.py` expone:

```python
open_existing_index(persist_path)
query_top_k(index, question, top_k=5) -> dict[str, Any]
```

El helper runtime:

- abre un índice BM25 existente;
- no crea índices;
- limita `top_k` al tamaño del corpus;
- normaliza salidas tuple y `Results` de BM25S;
- devuelve:

```text
ids
documents
metadatas
scores
```

### Grafo LangGraph actual

`agents/consulta_normativa/langchain_rag/graph.py` define el contrato:

```python
Retriever = Callable[[str, int], dict[str, Any]]
```

El nodo `retrieve_node` usa:

```text
retrieval_query si existe
si no, question original
```

Luego guarda `raw_results` y `normalize_documents_node` llama:

```python
recovered_documents(raw_results)
```

en `agents/consulta_normativa/langchain_rag/formatting.py`.

Esto permite implementar Hybrid Retrieval como un **retriever compatible**, sin reescribir el grafo.

### RRF existente

`agents/consulta_normativa/langchain_rag/retrieval/fusion.py` ya contiene:

```python
reciprocal_rank_fusion(ranked_lists, k)
document_identity(document)
```

La función pura de RRF es reutilizable. Los nodos orientados a Multi-Query no deben reutilizarse para esta integración porque su estado y orquestación pertenecen a otra técnica.

## 3. Problemas detectados

### El grafo no debe duplicarse todavía

El grafo actual ya acepta un retriever con contrato `Callable[[str, int], dict[str, Any]]`. Crear un grafo nuevo solo para cambiar el retrieval sería más complejo de lo necesario.

### Multi-Query no pertenece a esta integración

Hybrid Retrieval debe fusionar dos retrievers para una misma consulta. No debe generar variantes de consulta ni reutilizar nodos diseñados para fan-out por múltiples queries.

### Scores incompatibles

Chroma devuelve distancias y BM25 devuelve scores. No deben sumarse ni normalizarse ingenuamente. RRF debe fusionar por posición de ranking, no por magnitud de score.

## 4. Diseño propuesto

### Arquitectura objetivo

```text
agents/shared/
├── chroma_retrieval.py      # existente, query-only dense
├── bm25_retrieval.py        # existente, query-only sparse
└── hybrid_retrieval.py      # nuevo, orquesta dense + sparse + RRF

agents/consulta_normativa/langchain_rag/
├── graph.py                 # sin cambio estructural
├── formatting.py            # sin cambio inicial
├── retrieval/fusion.py      # reutilizar función pura RRF
├── config.py                # defaults híbridos mínimos
└── main.py                  # wiring runtime: abrir Chroma + BM25
```

### Flujo runtime

```text
build_runtime
        ↓
open_existing_collection(data/processed/chroma)
        ↓
open_existing_index(data/processed/bm25)
        ↓
build_hybrid_retriever(collection, bm25_index)
        ↓
build_langgraph_rag(llm, hybrid_retriever)
```

### Flujo de consulta

```text
query
 ↓
Chroma query_top_k(query, candidate_top_k)
BM25 query_top_k(query, candidate_top_k)
 ↓
recovered_documents(dense_raw)
recovered_documents(sparse_raw)
 ↓
reciprocal_rank_fusion([dense_docs, sparse_docs], rrf_k)
 ↓
take final_top_k
 ↓
raw result Chroma-like
```

La salida del retriever híbrido debe seguir siendo compatible con `recovered_documents()`:

```python
{
    "ids": [[...]],
    "documents": [[...]],
    "metadatas": [[...]],
}
```

Opcionalmente puede incluir señales de observabilidad sin romper consumidores actuales:

```python
{
    "hybrid_trace": {...}
}
```

pero no debe requerirse para generar la respuesta.

## 5. Componentes afectados

### Archivos nuevos

```text
agents/shared/hybrid_retrieval.py
agents/consulta_normativa/tests/test_hybrid_retrieval.py
```

Responsabilidades:

| Archivo | Responsabilidad |
|---|---|
| `agents/shared/hybrid_retrieval.py` | Construir un retriever query-only que consulta Chroma y BM25, normaliza resultados, aplica RRF y devuelve shape compatible con el grafo. |
| `agents/consulta_normativa/tests/test_hybrid_retrieval.py` | Validar fusión, deduplicación, `final_top_k`, resultados vacíos y preservación de metadata. |

### Archivos a modificar

```text
agents/consulta_normativa/langchain_rag/config.py
agents/consulta_normativa/langchain_rag/main.py
agents/consulta_normativa/tests/test_langchain_rag_main.py
```

Responsabilidades:

| Archivo | Cambio |
|---|---|
| `config.py` | Agregar defaults mínimos para `HYBRID_CANDIDATE_TOP_K`, `HYBRID_FINAL_TOP_K` y `HYBRID_RRF_K`. |
| `main.py` | Abrir Chroma y BM25 existentes; construir retriever híbrido; mantener `build_langgraph_rag(llm, retriever)`. |
| `test_langchain_rag_main.py` | Ajustar/verificar wiring runtime para Chroma + BM25 + retriever híbrido. |

### Archivos que no deben modificarse

```text
pipeline/vectorization/
pipeline/sparse_indexing/
agents/consulta_normativa/langchain_rag/graph.py
agents/consulta_normativa/langchain_rag/retrieval/multi_query.py
```

Motivo: esta integración debe usar índices ya existentes y mantener estable la orquestación RAG actual.

## 6. Plan de implementación

### 1. Definir configuración híbrida mínima

**Acción**  
Agregar constantes en `agents/consulta_normativa/langchain_rag/config.py`:

```python
HYBRID_CANDIDATE_TOP_K = 10
HYBRID_FINAL_TOP_K = DEFAULT_TOP_K
HYBRID_RRF_K = RRF_K
```

Si se prefiere máxima limpieza experimental inicial, `HYBRID_CANDIDATE_TOP_K` puede iniciar en `DEFAULT_TOP_K`; sin embargo, `10` permite un pool razonable manteniendo `final_top_k=5`.

**Ubicación**  
`agents/consulta_normativa/langchain_rag/config.py`

**Motivo**  
Distinguir candidatos por retriever de documentos finales entregados al LLM.

**Dependencias**  
Ninguna.

### 2. Crear helper `hybrid_retrieval.py`

**Acción**  
Crear `agents/shared/hybrid_retrieval.py` con una función constructora:

```python
def hybrid_retriever(
    dense_collection: Any,
    sparse_index: Any,
    *,
    candidate_top_k: int,
    final_top_k: int,
    rrf_k: int,
) -> Callable[[str, int], dict[str, Any]]:
    ...
```

El callable resultante debe aceptar el contrato actual:

```python
retriever(question: str, top_k: int) -> dict[str, Any]
```

**Ubicación**  
`agents/shared/hybrid_retrieval.py`

**Motivo**  
Mantener el grafo desacoplado de Chroma, BM25 y RRF.

**Dependencias**  
Paso 1.

### 3. Consultar dense y sparse dentro del helper

**Acción**  
Dentro del retriever híbrido:

```text
dense_raw = chroma_retrieval.query_top_k(dense_collection, query, candidate_top_k)
sparse_raw = bm25_retrieval.query_top_k(sparse_index, query, candidate_top_k)
```

**Ubicación**  
`agents/shared/hybrid_retrieval.py`

**Motivo**  
Centralizar la integración sin modificar los helpers query-only existentes.

**Dependencias**  
Paso 2.

### 4. Normalizar ambos rankings

**Acción**  
Convertir ambos resultados a `RetrievedDocument` usando:

```python
recovered_documents(dense_raw)
recovered_documents(sparse_raw)
```

**Ubicación**  
`agents/shared/hybrid_retrieval.py`

**Motivo**  
Reutilizar el contrato actual de formato e identidad. Si ambos raw results contienen `ids`, `recovered_documents()` inyecta la identidad técnica en metadata.

**Dependencias**  
Paso 3.

### 5. Aplicar RRF por ranking, no por score

**Acción**  
Fusionar:

```python
fused_documents = reciprocal_rank_fusion(
    [dense_documents, sparse_documents],
    k=rrf_k,
)
```

Luego cortar:

```python
final_documents = fused_documents[:effective_final_top_k]
```

**Ubicación**  
`agents/shared/hybrid_retrieval.py`

**Motivo**  
Evitar calibrar distancias de Chroma contra scores BM25.

**Dependencias**  
Paso 4.

### 6. Convertir documentos fusionados a raw result compatible

**Acción**  
Crear una función pequeña:

```python
def documents_to_raw_results(documents: list[RetrievedDocument]) -> dict[str, Any]:
    ...
```

Debe devolver:

```python
{
    "ids": [[document_id_1, ...]],
    "documents": [[document.document, ...]],
    "metadatas": [[document.metadata, ...]],
}
```

El `document_id` debe salir de la identidad que ya usa `document_identity(document)`. No reconstruir identidad por texto si ya existe ID en metadata.

**Ubicación**  
`agents/shared/hybrid_retrieval.py`

**Motivo**  
El grafo actual espera `raw_results`, no una lista ya normalizada.

**Dependencias**  
Paso 5.

### 7. Manejar resultados vacíos de forma determinística

**Acción**  
Si ambos retrievers devuelven listas vacías, retornar:

```python
{
    "ids": [[]],
    "documents": [[]],
    "metadatas": [[]],
}
```

Si solo una rama devuelve resultados, RRF debe producir esos documentos sin fallar.

**Ubicación**  
`agents/shared/hybrid_retrieval.py`

**Motivo**  
Mantener el fallback actual del grafo por evidencia insuficiente.

**Dependencias**  
Paso 6.

### 8. Cablear runtime en `main.py`

**Acción**  
En `agents/consulta_normativa/langchain_rag/main.py`:

1. abrir Chroma existente con `open_existing_collection`;
2. abrir BM25 existente con `open_existing_index`;
3. construir retriever híbrido;
4. pasar ese retriever a `build_langgraph_rag(llm, retriever)`.

**Ubicación**  
`agents/consulta_normativa/langchain_rag/main.py`

**Motivo**  
Activar Hybrid Retrieval sin cambiar el grafo.

**Dependencias**  
Pasos 1-7.

### 9. Mantener fallos operativos explícitos

**Acción**  
Si Chroma o BM25 no existen, el runtime debe fallar con mensaje operativo claro. No crear colección ni índice vacío.

**Ubicación**  
`agents/consulta_normativa/langchain_rag/main.py`

**Motivo**  
Evitar consultas silenciosas sobre índices incompletos.

**Dependencias**  
Paso 8.

### 10. Actualizar tests de runtime wiring

**Acción**  
Actualizar `agents/consulta_normativa/tests/test_langchain_rag_main.py` para verificar:

- abre Chroma existente;
- abre BM25 existente;
- construye retriever híbrido;
- llama `build_langgraph_rag(llm, retriever)` sin parámetros Multi-Query;
- no crea índices.

**Ubicación**  
`agents/consulta_normativa/tests/test_langchain_rag_main.py`

**Motivo**  
El test actual puede conservar expectativas viejas de una firma Multi-Query. Debe reflejar el runtime real.

**Dependencias**  
Paso 8.

## 7. Cambios de estado o contratos

### Sin cambios en `RagGraphState`

No agregar campos obligatorios al estado LangGraph.

El retriever híbrido debe seguir devolviendo `raw_results` compatible con:

```python
recovered_documents(raw_results)
```

### Nuevo contrato interno

`agents/shared/hybrid_retrieval.py` debe producir un callable:

```python
Callable[[str, int], dict[str, Any]]
```

compatible con el grafo actual.

### Parámetros nuevos

```text
HYBRID_CANDIDATE_TOP_K
HYBRID_FINAL_TOP_K
HYBRID_RRF_K
```

Regla experimental:

```text
HYBRID_FINAL_TOP_K == DEFAULT_TOP_K
```

para mantener constante la cantidad de contexto enviada al LLM.

## 8. Testing

### Unit tests

Crear:

```bash
python -m unittest agents.consulta_normativa.tests.test_hybrid_retrieval
```

Debe validar:

- fusiona rankings de Chroma y BM25;
- deduplica documentos con el mismo ID;
- no suma `distance + score`;
- respeta `final_top_k`;
- conserva metadata usada por `build_context()` y `build_references()`;
- funciona si una rama no devuelve resultados;
- devuelve shape `ids/documents/metadatas` compatible.

### Integration tests de runtime

Actualizar/ejecutar:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_main
```

Debe validar el wiring Chroma + BM25 + hybrid retriever.

### Regression tests

```bash
python -m unittest \
  agents.consulta_normativa.tests.test_bm25_retrieval \
  agents.consulta_normativa.tests.test_langchain_rag_fusion \
  agents.consulta_normativa.tests.test_langchain_rag_graph \
  agents.consulta_normativa.tests.test_langchain_rag_formatting
```

### Tests de índices offline

```bash
python -m unittest \
  pipeline.tests.test_vectorization_documents \
  pipeline.tests.test_vectorization_chroma_store \
  pipeline.tests.test_sparse_indexing_bm25_store
```

### Compile check

```bash
python -m compileall pipeline/tables pipeline/vectorization pipeline/sparse_indexing agents/shared agents/consulta_normativa
```

## 9. Riesgos

### Alto — Índices desincronizados

Si Chroma y BM25 no representan el mismo corpus, RRF mezclará rankings incompatibles. Antes de evaluación formal:

```text
1. borrar o mover data/processed/chroma
2. reconstruir Chroma desde JSONL actuales
3. reconstruir BM25 desde los mismos JSONL
4. verificar IDs si se agrega una herramienta de paridad
```

### Alto — Contaminar el experimento con Multi-Query o reranking

Este plan debe medir solo el efecto de combinar Chroma + BM25. Agregar Multi-Query, reranking o filtros al mismo tiempo impide atribuir mejoras o regresiones.

### Medio — Pool de candidatos insuficiente

Si `candidate_top_k == final_top_k`, RRF tendrá poco margen para mejorar. Para implementación inicial puede funcionar; para evaluación conviene `candidate_top_k > final_top_k`.

### Medio — Identidad semánticamente imperfecta

`recovered_documents()` usa metadata `_chroma_id` para guardar IDs. BM25 también puede pasar por ese camino porque devuelve `ids`. Es funcional, pero el nombre no es ideal. No renombrarlo en esta fase para evitar ampliar alcance.

### Medio — Fallback silencioso si falta una rama

Si una rama falla por error operativo, no debe ocultarse como lista vacía. Lista vacía solo es válida cuando la consulta no recupera documentos. Errores abriendo índices o ejecutando consultas deben propagarse o reportarse claramente.

## 10. Criterios de aceptación

- Existe `agents/shared/hybrid_retrieval.py`.
- El retriever híbrido consulta Chroma y BM25 para la misma query.
- La fusión usa RRF por ranking, no mezcla scores numéricos.
- La salida conserva shape compatible con `recovered_documents()`.
- `HYBRID_FINAL_TOP_K` mantiene el mismo valor que `DEFAULT_TOP_K`.
- `main.py` abre Chroma y BM25 existentes; no crea índices ni colecciones.
- `build_langgraph_rag` se sigue usando con el contrato actual.
- No se modifica `pipeline/vectorization/` ni `pipeline/sparse_indexing/`.
- No se agrega Multi-Query, reranking ni filtros metadata-aware.
- Tests de hybrid retrieval y runtime wiring pasan.
- Tests de regresión de BM25, Chroma, formatting y graph siguen pasando.

## Fuentes técnicas

- BM25S: documentación de uso actual con `bm25s.tokenize`, `BM25().index`, `save(..., corpus=...)`, `BM25.load(..., load_corpus=True)` y `retrieve()`.
- Reciprocal Rank Fusion: Cormack, Clarke y Büttcher, técnica de fusión por posición de ranking.
- Implementación actual del proyecto: `agents/shared/chroma_retrieval.py`, `agents/shared/bm25_retrieval.py`, `agents/consulta_normativa/langchain_rag/graph.py`, `agents/consulta_normativa/langchain_rag/retrieval/fusion.py`.
