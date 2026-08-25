# Plan de ajuste para Hybrid Retrieval: `top_k` único e identidad canónica

## Objetivo

Dejar el retrieval híbrido con una sola fuente de verdad para el número final de documentos recuperados y una identidad canónica de documento independiente de Chroma o BM25.

El cambio debe preservar el flujo actual:

```text
consulta del usuario
  ↓
query expansion
  ↓
retriever híbrido
  ├─ Chroma / dense retrieval
  └─ BM25 / sparse retrieval
  ↓
RRF fusion
  ↓
documentos finales para el grafo RAG
```

## Problemas a resolver

### 1. Hay más de una fuente de verdad para el top-k final

Actualmente el sistema tiene varios valores que pueden limitar la cantidad final de documentos:

- `DEFAULT_TOP_K` en `agents/consulta_normativa/langchain_rag/config.py`.
- `HYBRID_FINAL_TOP_K` en `agents/consulta_normativa/langchain_rag/config.py`.
- `top_k` recibido por `build_langgraph_rag(...)`.
- `top_k` pasado por `retrieve_node(...)` al retriever.
- `final_top_k` recibido por `hybrid_retriever(...)`.
- `effective_final_top_k(top_k, final_top_k)` dentro de `agents/shared/hybrid_retrieval.py`.

Esto produce una doble autoridad:

```python
effective_top_k = min(top_k, final_top_k)
```

Aunque el comportamiento es seguro, no es claro. El grafo pide una cantidad final y el retriever híbrido vuelve a limitarla.

### 2. La identidad de documento está acoplada a `_chroma_id`

La función actual de identidad está en:

```text
agents/consulta_normativa/langchain_rag/retrieval/fusion.py
```

Actualmente prioriza:

```python
metadata.get("_chroma_id")
```

Ese nombre era aceptable cuando el único motor era Chroma, pero ahora hay dos motores:

- Chroma.
- BM25.

El ID usado para deduplicar en RRF debe representar el documento o chunk, no el motor que lo recuperó.

### 3. La trazabilidad de fuentes existe, pero depende de la identidad actual

`agents/shared/hybrid_retrieval.py` ya agrega metadata interna:

```python
_retrieved_by_chroma
_retrieved_by_bm25
_retrieval_sources
```

Eso es útil, pero la agrupación se basa en `document_identity(...)`. Si la identidad no es estable entre Chroma y BM25, la trazabilidad también queda mal.

### 4. BM25 debe mantener tokenización consistente en español

El índice BM25 se construye con:

```python
bm25s.tokenize(texts, stopwords="es")
```

La consulta runtime también debe usar:

```python
bm25s.tokenize([question], stopwords="es")
```

Los tests con fakes deben aceptar y verificar ese parámetro.

## Decisiones de diseño

### Decisión 1: un solo top-k final

El único valor que define cuántos documentos llegan al prompt debe ser:

```python
RETRIEVAL_TOP_K
```

Ese valor se pasa al grafo:

```python
graph = build_langgraph_rag(
    llm,
    retriever,
    top_k=RETRIEVAL_TOP_K,
)
```

El retriever híbrido debe recibir ese `top_k` en runtime y respetarlo directamente.

El retriever híbrido solo debe tener una configuración propia para el tamaño del pool candidato por motor:

```python
HYBRID_CANDIDATE_TOP_K
```

Separación conceptual:

```text
HYBRID_CANDIDATE_TOP_K
  = cuántos candidatos pide a Chroma y BM25 antes de fusionar.

RETRIEVAL_TOP_K
  = cuántos documentos finales pasan al contexto del RAG.
```

### Decisión 2: identidad canónica neutral

Usar una metadata interna neutral:

```python
_document_id
```

Esta debe representar el ID estable del chunk o documento indexado, sin importar si fue recuperado por Chroma o por BM25.

Ejemplo:

```python
{
    "_document_id": "table-decreto-768-de-2022-0-part-0001",
    "document_type": "table",
    "source_stem": "Decreto 768 de 2022",
}
```

No usar `_chroma_id` como identidad principal de deduplicación.

### Decisión 3: compatibilidad temporal con `_chroma_id`

Durante la transición, `document_identity(...)` puede aceptar `_chroma_id` como fallback para no romper rutas existentes.

Prioridad recomendada:

```text
_document_id
  ↓
document_id
  ↓
_chroma_id
  ↓
fallback por referencia + hash de texto
```

### Decisión 4: la trazabilidad de fuentes se mantiene como metadata interna

Mantener:

```python
_retrieved_by_chroma: bool
_retrieved_by_bm25: bool
_retrieval_sources: list[str]
```

Esto permite inspeccionar de dónde salió cada chunk sin mezclar scores de Chroma y BM25.

No renderizar estos campos como información normativa para el usuario final.

## Cambios por archivo

### 1. `agents/consulta_normativa/langchain_rag/config.py`

#### Cambiar

Reemplazar el control actual:

```python
DEFAULT_TOP_K = ...
HYBRID_CANDIDATE_TOP_K = ...
HYBRID_FINAL_TOP_K = DEFAULT_TOP_K
```

por:

```python
RETRIEVAL_FINAL_TOP_K = 5
HYBRID_CANDIDATE_TOP_K = 10
HYBRID_RRF_K = RRF_K
```

Si se conserva `DEFAULT_TOP_K` por compatibilidad, debe ser alias explícito:

```python
DEFAULT_TOP_K = RETRIEVAL_FINAL_TOP_K
```

#### Eliminar

Eliminar:

```python
HYBRID_FINAL_TOP_K
```

#### Criterio de aceptación

Debe quedar claro que:

```text
RETRIEVAL_FINAL_TOP_K controla salida final.
HYBRID_CANDIDATE_TOP_K controla recall previo a fusión.
```

---

### 2. `agents/consulta_normativa/langchain_rag/main.py`

#### Cambiar imports

Importar:

```python
RETRIEVAL_FINAL_TOP_K
HYBRID_CANDIDATE_TOP_K
HYBRID_RRF_K
```

No importar:

```python
HYBRID_FINAL_TOP_K
```

#### Cambiar construcción del retriever

Dejar el retriever híbrido sin `final_top_k`:

```python
retriever = dependencies.hybrid_retriever(
    collection,
    sparse_index,
    candidate_top_k=HYBRID_CANDIDATE_TOP_K,
    rrf_k=HYBRID_RRF_K,
)
```

#### Cambiar construcción del grafo

Pasar el top-k final al grafo:

```python
graph = dependencies.build_langgraph_rag(
    llm,
    retriever,
    top_k=RETRIEVAL_FINAL_TOP_K,
)
```

#### Criterio de aceptación

`build_runtime()` debe tener un solo punto donde se define la cantidad final de documentos: el argumento `top_k` del grafo.

---

### 3. `agents/shared/hybrid_retrieval.py`

#### Cambiar firma

De:

```python
def hybrid_retriever(
    dense_collection: Any,
    sparse_index: Any,
    *,
    candidate_top_k: int,
    final_top_k: int,
    rrf_k: int,
) -> Callable[[str, int], dict[str, Any]]:
```

A:

```python
def hybrid_retriever(
    dense_collection: Any,
    sparse_index: Any,
    *,
    candidate_top_k: int,
    rrf_k: int,
) -> Callable[[str, int], dict[str, Any]]:
```

#### Eliminar función

Eliminar:

```python
effective_final_top_k(...)
```

#### Cambiar `retrieve(...)`

La validación debe depender solo del `top_k` recibido:

```python
if top_k <= 0:
    return empty_hybrid_result()
```

La salida final debe usar:

```python
fused_documents[:top_k]
```

#### Mantener candidate retrieval

Chroma y BM25 deben seguir consultándose con:

```python
candidate_top_k
```

Ejemplo:

```python
dense_raw = chroma_retrieval.query_top_k(dense_collection, query, candidate_top_k)
sparse_raw = bm25_retrieval.query_top_k(sparse_index, query, candidate_top_k)
```

#### Criterio de aceptación

Entrada:

```python
retriever("CIIU 4711", top_k=3)
```

Salida:

```python
{
    "ids": [["...", "...", "..."]],
    "documents": [[...]],
    "metadatas": [[...]],
}
```

Debe haber máximo 3 documentos finales.

---

### 4. `agents/consulta_normativa/langchain_rag/formatting.py`

#### Objetivo

Normalizar los IDs crudos de cada motor hacia `_document_id`.

#### Cambio recomendado

En la función que convierte resultados raw a `RetrievedDocument`, cuando exista `ids[index]`, agregar:

```python
metadata.setdefault("_document_id", str(ids[index]))
```

Si se necesita mantener compatibilidad con código existente, conservar:

```python
metadata.setdefault("_chroma_id", str(ids[index]))
```

pero no usar `_chroma_id` como identidad conceptual principal.

#### Input esperado

```python
{
    "ids": [["table-decreto-768-de-2022-0-part-0001"]],
    "documents": [["| 1 | 4711 | ... |"]],
    "metadatas": [[{"document_type": "table"}]],
}
```

#### Output esperado

```python
RetrievedDocument(
    document="| 1 | 4711 | ... |",
    metadata={
        "document_type": "table",
        "_document_id": "table-decreto-768-de-2022-0-part-0001",
    },
)
```

#### Criterio de aceptación

Todo resultado con `ids` debe producir documentos con `_document_id`.

---

### 5. `agents/consulta_normativa/langchain_rag/retrieval/fusion.py`

#### Cambiar `document_identity(...)`

Debe priorizar `_document_id`:

```python
document_id = metadata.get("_document_id") or metadata.get("document_id")
if has_value(document_id):
    return f"id:{document_id}"
```

Luego mantener fallback temporal:

```python
chroma_id = metadata.get("_chroma_id")
if has_value(chroma_id):
    return f"id:{chroma_id}"
```

Y finalmente conservar fallback por referencia + hash:

```python
text_hash = hashlib.sha256(document.document.encode("utf-8")).hexdigest()[:12]
return f"fallback:{reference_from_metadata(metadata)}:{text_hash}"
```

#### Criterio de aceptación

Dos documentos recuperados por motores distintos deben deduplicarse si tienen el mismo `_document_id`.

Ejemplo:

```python
RetrievedDocument(
    document="Texto 4711",
    metadata={"_document_id": "table-4711", "_retrieval_sources": ["chroma"]},
)
```

y:

```python
RetrievedDocument(
    document="Texto 4711",
    metadata={"_document_id": "table-4711", "_retrieval_sources": ["bm25"]},
)
```

deben tener la misma identidad:

```python
"id:table-4711"
```

---

### 6. `agents/shared/bm25_retrieval.py`

#### Mantener tokenización en español

La consulta debe tokenizarse con:

```python
bm25s_module().tokenize([question], stopwords="es")
```

#### Top-k explícito

Preferir que `top_k` sea obligatorio:

```python
def query_top_k(index: Any, question: str, top_k: int) -> dict[str, Any]:
```

Si se conserva default por compatibilidad, no debe ser otra fuente de verdad del grafo; solo un fallback local.

#### Criterio de aceptación

BM25 runtime debe usar la misma configuración de stopwords que BM25 indexing.

---

### 7. `pipeline/sparse_indexing/bm25_store.py`

#### Mantener tokenización en español

Mantener:

```python
tokens = bm25s.tokenize(texts, stopwords="es")
```

#### Constructor BM25

No pasar `stopwords` al constructor de BM25 si la versión documentada de BM25S no lo soporta.

Debe quedar:

```python
retriever = bm25s.BM25()
```

No:

```python
retriever = bm25s.BM25(stopwords="es")
```

#### Criterio de aceptación

El índice se construye con tokens en español y no falla por argumentos inválidos en `BM25(...)`.

---

### 8. `pipeline/vectorization/documents.py`

#### Objetivo

Hacer explícito el ID canónico desde la fuente de vectorización.

#### Cambio recomendado

Agregar `document_id` a la metadata plana generada para child chunks y table documents.

Para child chunks:

```python
"document_id": record_id
```

Para table documents:

```python
"document_id": record_id
```

#### Criterio de aceptación

Tanto Chroma como BM25 deben poder transportar el mismo ID canónico desde `ChromaRecord.id` y/o `metadata["document_id"]`.

---

## Tests a actualizar o agregar

### `agents/consulta_normativa/tests/test_hybrid_retrieval.py`

Actualizar tests para que `hybrid_retriever(...)` ya no reciba `final_top_k`.

Agregar casos:

1. El `top_k` del caller controla la cantidad final.
2. `candidate_top_k` se usa para consultar Chroma y BM25.
3. Documentos con el mismo `_document_id` se deduplican.
4. Metadata de trazabilidad distingue:
   - solo Chroma;
   - solo BM25;
   - ambos motores.

### `agents/consulta_normativa/tests/test_langchain_rag_main.py`

Actualizar expectativas de `build_runtime()`:

- `hybrid_retriever(...)` recibe `candidate_top_k` y `rrf_k`.
- `build_langgraph_rag(...)` recibe `top_k=RETRIEVAL_FINAL_TOP_K`.
- No se espera `final_top_k` en el retriever híbrido.

### `agents/consulta_normativa/tests/test_langchain_rag_fusion.py`

Agregar tests para `document_identity(...)`:

1. Prioriza `_document_id`.
2. Usa `document_id` como fallback.
3. Mantiene compatibilidad con `_chroma_id`.
4. Usa fallback por referencia + hash si no hay ID.

### `agents/consulta_normativa/tests/test_langchain_rag_formatting.py`

Agregar o actualizar tests para `recovered_documents(...)`:

1. Convierte raw `ids` en metadata `"_document_id"`.
2. Preserva `document_id` si ya venía en metadata.
3. No sobrescribe metadata existente innecesariamente.

### `agents/consulta_normativa/tests/test_bm25_retrieval.py`

Actualizar fake tokenizer para aceptar:

```python
stopwords="es"
```

Agregar aserción de que runtime BM25 consulta con stopwords en español.

### `pipeline/tests/test_sparse_indexing_bm25_store.py`

Actualizar fake tokenizer para aceptar:

```python
stopwords="es"
```

Agregar aserción de que indexación BM25 usa stopwords en español.

Verificar que `BM25()` se construye sin `stopwords`.

### `pipeline/tests/test_vectorization_documents.py`

Si se agrega `document_id` a metadata, actualizar expectativas para child chunks y table documents.

## Verificación recomendada

Ejecutar tests enfocados:

```bash
python -m unittest \
  agents.consulta_normativa.tests.test_bm25_retrieval \
  agents.consulta_normativa.tests.test_hybrid_retrieval \
  agents.consulta_normativa.tests.test_langchain_rag_main \
  agents.consulta_normativa.tests.test_langchain_rag_graph \
  agents.consulta_normativa.tests.test_langchain_rag_formatting \
  agents.consulta_normativa.tests.test_langchain_rag_fusion \
  pipeline.tests.test_sparse_indexing_bm25_store \
  pipeline.tests.test_sparse_indexing_ingest \
  pipeline.tests.test_vectorization_documents
```

Ejecutar compile check:

```bash
python -m compileall \
  pipeline/sparse_indexing \
  pipeline/vectorization \
  agents/consulta_normativa \
  agents/shared
```

Si se modifican rutas de indexación o records vectoriales, ejecutar además:

```bash
python -m unittest discover -s pipeline/tests
```

## Resultado esperado

Después del cambio, el flujo debe quedar así:

```text
RETRIEVAL_FINAL_TOP_K
  ↓
build_langgraph_rag(..., top_k=RETRIEVAL_FINAL_TOP_K)
  ↓
retrieve_node(...)
  ↓
hybrid_retriever.retrieve(query, top_k)
  ↓
Chroma top HYBRID_CANDIDATE_TOP_K
BM25 top HYBRID_CANDIDATE_TOP_K
  ↓
RRF deduplica por _document_id
  ↓
devuelve top_k final
```

Ejemplo con `CIIU 4711`:

```python
query = "A qué corresponde el CIIU 4711 en Colombia?"
top_k = 5
```

Chroma puede devolver:

```python
[
    {"_document_id": "chunk-definicion-ciiu"},
    {"_document_id": "table-decreto-768-de-2022-0-part-0048"},
]
```

BM25 puede devolver:

```python
[
    {"_document_id": "table-decreto-768-de-2022-0-part-0001"},
    {"_document_id": "chunk-definicion-ciiu"},
]
```

RRF debe fusionar y deduplicar por `_document_id`:

```python
[
    {"_document_id": "chunk-definicion-ciiu", "_retrieval_sources": ["chroma", "bm25"]},
    {"_document_id": "table-decreto-768-de-2022-0-part-0001", "_retrieval_sources": ["bm25"]},
    {"_document_id": "table-decreto-768-de-2022-0-part-0048", "_retrieval_sources": ["chroma"]},
]
```

La salida final debe contener máximo `top_k` documentos y mantener metadata suficiente para diagnosticar si un chunk vino de Chroma, BM25 o ambos.

## Riesgos y notas

- No mezclar scores de Chroma y BM25. Chroma usa distancias/similitudes y BM25 usa scores lexicales; no están en la misma escala.
- RRF debe seguir usando posiciones de ranking, no scores crudos.
- No convertir `_retrieval_sources` en contenido visible para el LLM como evidencia normativa.
- Si se cambia metadata de vectorización, puede requerirse reconstruir Chroma y BM25 para que los índices persistidos reflejen `document_id`.
- Mantener `pipeline/` como transformación/indexación offline. La lógica runtime debe permanecer en `agents/` o `agents/shared/`.
