# Arquitectura de recuperación sparse BM25

BM25 agrega recuperación léxica al corpus SG-SST sin cambiar el flujo RAG activo. Su responsabilidad es construir un índice sparse local desde los artefactos JSONL canónicos y exponer una consulta runtime de solo lectura con una forma compatible con los resultados actuales de recuperación.

## Ruta rápida

Desde la raíz del repositorio:

```bash
python -m pipeline.sparse_indexing.main
```

El índice se persiste en `data/processed/bm25/`. En runtime, `agents/shared/bm25_retrieval.py` abre ese índice existente y ejecuta consultas `top_k`; no crea índices ni modifica el grafo LangGraph.

## Límite arquitectónico

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Indexación offline | `pipeline/sparse_indexing/` | Leer JSONL canónicos, construir corpus BM25, tokenizar, indexar y persistir con BM25S. |
| Recuperación runtime | `agents/shared/bm25_retrieval.py` | Abrir un índice BM25 existente y devolver resultados en forma Chroma-like. |
| Fuente de verdad | JSONL procesados | `chunks.jsonl` y `table_documents.jsonl`, no Chroma. |

BM25 no se construye desde ChromaDB. Chroma usa `upsert` y puede conservar registros obsoletos; por eso BM25 se reconstruye desde los mismos JSONL que alimentan la vectorización.

## Flujo de datos

```text
data/processed/chunks/regex_constrained_semantic/chunks.jsonl
data/processed/table_documents.jsonl
        ↓
pipeline.vectorization.documents.load_vector_record_batch
        ↓
registros BM25 {id, document, metadata}
        ↓
bm25s.tokenize(..., stopwords="es")
        ↓
bm25s.BM25().index(...)
        ↓
retriever.save(..., corpus=corpus)
        ↓
data/processed/bm25/
        ↓
open_existing_index(...) + query_top_k(...)
```

`load_vector_record_batch` conserva el contrato ya usado por Chroma: IDs canónicos, texto indexable y metadata plana. La capa BM25 transforma esos registros en un corpus ordenado para que los resultados devueltos por BM25S puedan mapearse de nuevo a documentos recuperables.

## Contratos principales

### Resultado de indexación

`pipeline/sparse_indexing/ingest.py` define `SparseIndexResult`:

| Campo | Significado |
|---|---|
| `total_count` | Total de registros indexados. |
| `child_chunk_count` | Registros de tipo `child_chunk`. |
| `table_count` | Registros de tipo `table`. |
| `skipped_child_chunk_count` | Child chunks inválidos o vacíos descartados por la carga canónica. |
| `skipped_table_count` | Documentos de tabla inválidos o vacíos descartados por la carga canónica. |
| `persist_path` | Ruta donde se guarda el índice BM25. |
| `skipped_count` | Propiedad calculada con el total de registros omitidos. |

### Registro de corpus BM25

Cada `ChromaRecord` se convierte a:

```python
{
    "id": record.id,
    "document": record.document,
    "metadata": record.metadata,
}
```

El orden del corpus coincide con el orden de los textos tokenizados. Ese orden es parte del contrato porque BM25S devuelve documentos desde el corpus guardado.

### Resultado runtime

`query_top_k(index, question, top_k=5)` devuelve:

```python
{
    "ids": [[...]],
    "documents": [[...]],
    "metadatas": [[...]],
    "scores": [[...]],
}
```

La forma sigue el patrón de Chroma, pero `scores` corresponde a puntajes BM25. Si el índice no tiene corpus o `top_k <= 0`, se retorna la misma estructura vacía.

## Decisiones de diseño

| Decisión | Motivo |
|---|---|
| Construir desde JSONL, no desde Chroma | Evita heredar registros obsoletos de una colección Chroma persistida con `upsert`. |
| Mantener BM25 fuera de LangGraph en esta fase | La fase solo entrega un sparse retriever aislado y verificable. La integración híbrida queda fuera de alcance. |
| Abrir índice existente en runtime | `open_existing_index(...)` falla si la ruta no existe; runtime no crea índices vacíos. |
| Usar BM25S detrás de una frontera pequeña | `bm25_store.py` y `bm25_retrieval.py` importan `bm25s` de forma diferida para facilitar pruebas y aislar la dependencia. |
| Normalizar resultados BM25S | Se aceptan salidas tipo `Results` o tuplas `(documents, scores)` para mantener compatibilidad con variantes de la API. |
| Limitar `top_k` al tamaño del corpus | Evita pedir más resultados que documentos indexados. |
| No aplicar stemming, lematización, stopwords agresivas ni expansión de consulta | La primera fase prioriza trazabilidad y recuperación literal de señales jurídicas como normas, siglas y numerales. |

La implementación actual usa `stopwords="es"` en la tokenización de BM25S. No introduce stemming, lematización, sinónimos, query expansion, reranking ni filtros metadata-aware.

## Pruebas y criterios de aceptación

| Área | Pruebas |
|---|---|
| Corpus, orden y persistencia BM25S | `python -m unittest pipeline.tests.test_sparse_indexing_bm25_store` |
| Orquestación de ingest y conteos | `python -m unittest pipeline.tests.test_sparse_indexing_ingest` |
| Runtime query-only y forma de salida | `python -m unittest agents.consulta_normativa.tests.test_bm25_retrieval` |

Criterios clave:

- BM25 se construye desde `chunks.jsonl` y `table_documents.jsonl`.
- El índice se guarda en `data/processed/bm25/` con corpus persistido.
- Los IDs de child chunks y tablas se preservan.
- Runtime abre un índice existente y no escribe en disco.
- La salida contiene `ids`, `documents`, `metadatas` y `scores`.
- No hay cambios de grafo, Multi-Query, RRF ni fusión híbrida en esta documentación.

## Fuera de alcance

La conexión de BM25 con un flujo híbrido o con LangGraph corresponde a una fase posterior. Este documento solo cubre el componente BM25 ya implementado.
