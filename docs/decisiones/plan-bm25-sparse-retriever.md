# Plan de implementación BM25 Sparse Retriever

Este plan cubre únicamente la implementación de BM25 como sparse retriever. No incluye cambios en LangGraph ni evaluación ARES. La intención es construir primero una pieza aislada, verificable y alineada con la arquitectura actual.

## 1. Objetivo

Implementar una primera fase de **Sparse Retrieval con BM25S** para el corpus SG-SST.

Resultado esperado:

```text
JSONL child chunks + table documents
        ↓
pipeline/sparse_indexing/
        ↓
BM25 index persistido
        ↓
agents/shared/bm25_retrieval.py
        ↓
query-only sparse retrieval
```

Esta fase debe dejar listo un índice BM25 consultable, sin cambiar el flujo RAG activo.

## 2. Estado actual

La arquitectura actual separa bien el ingest offline y el retrieval online:

```text
pipeline/vectorization/
    ingest offline hacia Chroma

agents/shared/chroma_retrieval.py
    retrieval online query-only
```

BM25 debe seguir el mismo patrón, pero en una rama paralela:

```text
pipeline/sparse_indexing/
    ingest offline hacia BM25

agents/shared/bm25_retrieval.py
    retrieval online query-only
```

Fuentes canónicas actuales:

```text
data/processed/chunks/regex_constrained_semantic/chunks.jsonl
data/processed/table_documents.jsonl
```

La carga de estos artefactos ya existe en:

```python
pipeline.vectorization.documents.load_vector_record_batch
```

Esa función ya preserva lo necesario para BM25:

- child chunks: `chunk_id` como ID;
- table documents: `id` como ID;
- texto indexable desde `text`;
- metadata plana reutilizable por el runtime.

BM25S soporta el flujo requerido:

```python
bm25s.tokenize(...)
BM25().index(...)
retriever.save(..., corpus=corpus)
BM25.load(..., load_corpus=True)
retriever.retrieve(...)
```

## 3. Problemas detectados

### BM25 no debe construirse desde Chroma

Chroma no es la fuente de verdad. BM25 debe construirse desde los mismos JSONL que alimentan la vectorización actual. Esto evita depender de una base Chroma que puede contener registros obsoletos por `upsert`.

### No conviene tocar LangGraph

Integrar BM25 al grafo mezclaría dos responsabilidades:

```text
construir sparse retriever
+
orquestar el flujo RAG
```

Primero debe existir BM25 aislado y probado.

## 4. Diseño propuesto

Flujo offline:

```text
child chunks JSONL
table documents JSONL
        ↓
load_vector_record_batch
        ↓
Sparse/BM25 corpus records
        ↓
bm25s.tokenize
        ↓
BM25.index
        ↓
save index + corpus
        ↓
data/processed/bm25
```

Flujo runtime:

```text
question / retrieval_query
        ↓
agents/shared/bm25_retrieval.py
        ↓
load existing BM25 index
        ↓
tokenize query
        ↓
retrieve top_k
        ↓
Chroma-like result dict
```

Salida runtime compatible con el formateo actual:

```python
{
    "ids": [[...]],
    "documents": [[...]],
    "metadatas": [[...]],
    "scores": [[...]],
}
```

No usar en este plan:

- cambios en LangGraph;
- Multi-Query;
- reranking;
- filtros metadata-aware.

## 5. Componentes afectados

### Archivos nuevos

```text
pipeline/sparse_indexing/__init__.py
pipeline/sparse_indexing/bm25_store.py
pipeline/sparse_indexing/ingest.py
pipeline/sparse_indexing/main.py
agents/shared/bm25_retrieval.py
```

Responsabilidades:

| Archivo | Responsabilidad |
|---|---|
| `pipeline/sparse_indexing/__init__.py` | Declarar el paquete de indexación sparse. |
| `pipeline/sparse_indexing/bm25_store.py` | Encapsular BM25S: tokenización, construcción, persistencia. |
| `pipeline/sparse_indexing/ingest.py` | Orquestar indexación BM25 desde los JSONL canónicos. |
| `pipeline/sparse_indexing/main.py` | Exponer CLI offline `python -m pipeline.sparse_indexing.main`. |
| `agents/shared/bm25_retrieval.py` | Helper runtime query-only para abrir índice existente y consultar. |

### Archivos a modificar

```text
requirements.txt
```

Agregar dependencia `bm25s`.

### Tests nuevos

```text
pipeline/tests/test_sparse_indexing_ingest.py
pipeline/tests/test_sparse_indexing_bm25_store.py
agents/consulta_normativa/tests/test_bm25_retrieval.py
```

### Archivos que no deben modificarse

```text
pipeline/vectorization/
agents/consulta_normativa/langchain_rag/graph.py
agents/consulta_normativa/langchain_rag/main.py
```

Este plan solo implementa BM25 como sparse retriever aislado.

## 6. Plan de implementación

### 1. Agregar dependencia BM25S

**Acción**  
Agregar la dependencia de BM25S a `requirements.txt`.

Antes de fijar la línea exacta, verificar el nombre de paquete vigente en PyPI. La documentación de BM25S y Context7 siguen usando `import bm25s`; el blog de Hugging Face indica una actualización de marzo de 2026 donde también menciona instalación con `pip install bm25`. No cambiar el import planeado sin confirmar que el paquete instalado expone la API `bm25s` usada por la implementación.

**Ubicación**  
`requirements.txt`

**Motivo**  
BM25S será la librería responsable de indexar, guardar, cargar y consultar el índice sparse.

**Dependencias**  
Ninguna.

### 2. Crear paquete `pipeline/sparse_indexing`

**Acción**  
Crear `pipeline/sparse_indexing/__init__.py`.

**Ubicación**  
`pipeline/sparse_indexing/`

**Motivo**  
BM25 no es vectorización; debe vivir en una capa offline paralela, no dentro de `pipeline/vectorization/`.

**Dependencias**  
Paso 1.

### 3. Definir path y resultado de ingest BM25

**Acción**  
Crear en `pipeline/sparse_indexing/ingest.py`:

```python
DEFAULT_BM25_PATH = PROJECT_ROOT / "data" / "processed" / "bm25"
```

y un resultado tipo:

```python
@dataclass(frozen=True)
class SparseIndexResult:
    total_count: int
    child_chunk_count: int
    table_count: int
    skipped_child_chunk_count: int
    skipped_table_count: int
    persist_path: Path
```

**Ubicación**  
`pipeline/sparse_indexing/ingest.py`

**Motivo**  
Mantener trazabilidad equivalente a `IngestResult` de vectorización.

**Dependencias**  
Paso 2.

### 4. Reutilizar la carga canónica de documentos

**Acción**  
En `pipeline/sparse_indexing/ingest.py`, usar:

```python
load_vector_record_batch(chunks_path, tables_path)
```

desde:

```text
pipeline/vectorization/documents.py
```

**Ubicación**  
`pipeline/sparse_indexing/ingest.py`

**Motivo**  
Garantizar que BM25 use exactamente los mismos IDs, textos y metadata que Chroma.

**Dependencias**  
Paso 3.

### 5. Crear contrato de corpus BM25

**Acción**  
Transformar cada `ChromaRecord` en un corpus record simple:

```python
{
    "id": record.id,
    "document": record.document,
    "metadata": record.metadata,
}
```

**Ubicación**  
`pipeline/sparse_indexing/bm25_store.py`

**Motivo**  
BM25S separa los textos tokenizados del corpus retornable. El corpus debe conservar el mismo orden que los documentos indexados.

**Dependencias**  
Paso 4.

### 6. Implementar construcción y persistencia BM25

**Acción**  
Crear funciones en `bm25_store.py`:

```python
build_bm25_index(records)
save_bm25_index(retriever, persist_path, corpus)
```

Internamente:

```python
texts = [record.document for record in records]
tokens = bm25s.tokenize(texts)
retriever = bm25s.BM25()
retriever.index(tokens)
retriever.save(persist_path, corpus=corpus)
```

Usar inicialmente la variante por defecto de BM25S. Según la documentación consultada, BM25S soporta variantes como `robertson`, `atire`, `bm25l`, `bm25+` y `lucene`; el default documentado es `lucene`. No cambiar el método BM25 en esta fase para evitar introducir otra variable experimental.

**Ubicación**  
`pipeline/sparse_indexing/bm25_store.py`

**Motivo**  
Encapsular BM25S y no contaminar la orquestación con detalles de librería.

**Dependencias**  
Paso 5.

### 7. Implementar CLI offline

**Acción**  
Crear `pipeline/sparse_indexing/main.py` con argumentos:

```text
--chunks-path
--tables-path
--persist-path
```

Comando esperado:

```bash
python -m pipeline.sparse_indexing.main
```

**Ubicación**  
`pipeline/sparse_indexing/main.py`

**Motivo**  
Mantener simetría operativa con `python -m pipeline.vectorization.main`.

**Dependencias**  
Pasos 3-6.

### 8. Crear helper runtime query-only

**Acción**  
Crear `agents/shared/bm25_retrieval.py` con funciones:

```python
open_existing_index(persist_path: Path)
query_top_k(index, question: str, top_k: int = 5) -> dict[str, Any]
```

**Ubicación**  
`agents/shared/bm25_retrieval.py`

**Motivo**  
Mantener el mismo principio de `agents/shared/chroma_retrieval.py`: runtime abre algo existente, consulta y no escribe.

**Dependencias**  
Paso 6.

### 9. Normalizar salida BM25 a shape compatible

**Acción**  
`query_top_k` debe devolver:

```python
{
    "ids": [[record["id"], ...]],
    "documents": [[record["document"], ...]],
    "metadatas": [[record["metadata"], ...]],
    "scores": [[score, ...]],
}
```

**Ubicación**  
`agents/shared/bm25_retrieval.py`

**Motivo**  
Permite reutilizar `recovered_documents(...)` sin modificar `formatting.py`.

**Dependencias**  
Paso 8.

### 10. Proteger caso `top_k > corpus_size`

**Acción**  
Ajustar internamente:

```python
effective_top_k = min(top_k, document_count)
```

**Ubicación**  
`agents/shared/bm25_retrieval.py`

**Motivo**  
BM25S puede fallar si se piden más resultados que documentos indexados. Este fallback es determinístico y no oculta errores reales.

**Dependencias**  
Paso 9.

## 7. Cambios de estado o contratos

### Nuevo índice persistente

```text
data/processed/bm25/
```

### Nuevo contrato runtime BM25

```python
query_top_k(index, question, top_k=5) -> dict[str, Any]
```

Shape:

```python
{
    "ids": [[str]],
    "documents": [[str]],
    "metadatas": [[dict]],
    "scores": [[float]],
}
```

### Sin cambios en LangGraph

No agregar campos al estado todavía.

No agregar nodos todavía.

No agregar aristas todavía.

Este plan no define estado de grafo porque BM25 queda aislado como helper query-only.

## 8. Testing

### Unit tests

```bash
python -m unittest pipeline.tests.test_sparse_indexing_bm25_store
```

Debe validar:

- corpus conserva `id`;
- corpus conserva `document`;
- corpus conserva `metadata`;
- orden de corpus coincide con orden de textos tokenizados;
- save se llama con `corpus=...`.

```bash
python -m unittest agents.consulta_normativa.tests.test_bm25_retrieval
```

Debe validar:

- falla si `data/processed/bm25` no existe;
- carga índice existente;
- tokeniza query;
- respeta `top_k`;
- ajusta `top_k` si el corpus es menor;
- devuelve `ids`, `documents`, `metadatas`, `scores`.

### Integration tests

```bash
python -m unittest pipeline.tests.test_sparse_indexing_ingest
```

Debe validar:

- usa los mismos JSONL que vectorización;
- preserva IDs de child chunks y tablas;
- reporta conteos;
- no abre BM25 si faltan archivos fuente.

### Regression tests

```bash
python -m unittest pipeline.tests.test_vectorization_documents pipeline.tests.test_vectorization_chroma_store
```

```bash
python -m unittest agents.consulta_normativa.tests.test_rag_base agents.consulta_normativa.tests.test_langchain_rag_formatting
```

### Compile check

```bash
python -m compileall pipeline/vectorization pipeline/sparse_indexing agents/shared agents/consulta_normativa
```

## 9. Riesgos

### Alto — Destruir señales normativas con tokenización agresiva

No usar todavía:

```text
stemming
lemmatization
stopwords agresivas
sinónimos
query expansion
```

BM25 debe mejorar coincidencias como:

```text
Resolución 0312
Decreto 1072
COPASST
SG-SST
2.2.4.6.12
```

### Medio — Corpus diferente al almacenado en Chroma

BM25 se reconstruirá limpio desde JSONL. Chroma puede conservar registros viejos por `upsert`.

No bloquea este plan porque BM25 se valida de forma aislada, pero debe quedar documentado para no interpretar resultados BM25 como si describieran automáticamente el estado de Chroma.

### Medio — Acoplar BM25 a LangGraph antes de tiempo

Si se toca el grafo ahora, se mezclan dos problemas:

```text
construir sparse retriever
+
orquestar el flujo RAG
```

Eso dificulta depurar.

### Bajo — Dependencia nueva

La dependencia BM25S debe agregarse explícitamente a `requirements.txt`. Antes de fijar versión o nombre de paquete, verificar el estado actual de PyPI porque la documentación conserva `import bm25s`, mientras que el blog menciona una opción de instalación más reciente.

### Bajo — Optimización prematura con `mmap`

BM25S permite cargar índices con `mmap=True` para casos grandes. No usarlo en esta primera implementación; dejarlo como optimización posterior si el tamaño del índice lo exige.

### Bajo — Hugging Face Hub fuera de alcance

BM25S documenta integración con Hugging Face Hub mediante `BM25HF`. No usarla en este proyecto por ahora: el índice debe persistirse localmente en `data/processed/bm25/`.

## 10. Criterios de aceptación

- Existe `pipeline/sparse_indexing/`.
- BM25 se construye desde los mismos JSONL que Chroma.
- BM25 conserva IDs canónicos:
  - `chunk_id` para child chunks;
  - `id` para table documents.
- El índice se guarda en `data/processed/bm25/`.
- Runtime BM25 abre índice existente; no crea índice vacío.
- `agents/shared/bm25_retrieval.py` devuelve resultados compatibles con el formato actual.
- No se modifica `pipeline/vectorization/`.
- No se modifica LangGraph.
- Tests nuevos de BM25 pasan.
- Tests de regresión de vectorización y formatting siguen pasando.
