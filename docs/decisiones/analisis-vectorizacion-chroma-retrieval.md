# Análisis de vectorización, Chroma y retrieval

Este documento resume el estado actual de la vectorización del corpus SG-SST, la configuración de Chroma y el retrieval usado por el agente de consulta normativa. Es un análisis de implementación existente; no propone cambios ni modifica comportamiento.

## Resumen ejecutivo

- `pipeline/vectorization/` es responsable del **ingest offline**: lee artefactos vector-ready, normaliza registros y escribe en Chroma.
- `agents/shared/chroma_retrieval.py` es el helper canónico de **retrieval online**: abre una colección existente y ejecuta consultas `top-k`.
- Chroma persiste en `data/processed/chroma` y usa la colección `sg_sst_base_rag`.
- La ingesta usa `upsert`; no elimina registros obsoletos si el corpus cambia.
- El runtime no crea colecciones vacías: si la colección no existe, debe fallar.
- Hay configuración y helpers para Multi-Query/RRF, pero no deben asumirse activos sin verificar el grafo cableado en ese momento.

## Flujo de vectorización

Flujo actual:

```text
JSONL de child chunks + JSONL de table documents
        ↓
pipeline.vectorization.documents
        ↓
ChromaRecord normalizado
        ↓
pipeline.vectorization.chroma_store
        ↓
Chroma persistente en data/processed/chroma
```

Entrada principal:

```bash
python -m pipeline.vectorization.main --batch-size 8
```

Responsabilidades por archivo:

| Archivo | Responsabilidad |
|---|---|
| `pipeline/vectorization/main.py` | CLI de ingesta. Resuelve argumentos y llama al flujo principal. |
| `pipeline/vectorization/ingest.py` | Orquesta validaciones, carga de registros, apertura de colección y escritura por lotes. |
| `pipeline/vectorization/documents.py` | Convierte child chunks y table documents en registros compatibles con Chroma. |
| `pipeline/vectorization/chroma_store.py` | Abre/crea colección Chroma y ejecuta `upsert`. |

## Configuración de Chroma para ingest

| Aspecto | Configuración actual |
|---|---|
| Ruta persistente | `data/processed/chroma` |
| Colección | `sg_sst_base_rag` |
| Embedding model | `Qwen/Qwen3-Embedding-0.6B` |
| Embedding function | `SentenceTransformerEmbeddingFunction` |
| Batch por defecto | `8` |
| Escritura | `collection.upsert(ids=..., documents=..., metadatas=...)` |

La constante de colección se define en `agents/shared/chroma_retrieval.py` y se importa/reexporta desde `pipeline/vectorization/chroma_store.py`. Esto evita duplicar el nombre de colección entre ingest offline y retrieval online.

### Qué se indexa

Child chunks:

- ID: `chunk_id`.
- Documento: texto del chunk.
- Metadata: tipo de documento, documento fuente, `source_stem`, tipo normativo, año, jerarquía legal, offsets, presencia de tablas y claves lógicas de tablas.

Table documents:

- ID: `id`.
- Documento: texto construido para la tabla.
- Metadata: `document_type="table"`, `source_stem`, `table_index`, `table_part_index`, `table_part_count`, `table_key`, `linked_placeholder` y `oversized_row`.

La metadata se aplana antes de enviarla a Chroma para mantener compatibilidad con los tipos escalares que acepta la base vectorial.

## Configuración del retrieval runtime

El retrieval runtime está separado de la vectorización:

```text
pipeline/vectorization/
    ingest offline, create collection, upsert

agents/shared/chroma_retrieval.py
    query-only retrieval online
```

El helper runtime abre una colección existente. No debe crear una colección durante consulta, porque eso ocultaría errores operativos y podría dejar al agente consultando una colección vacía.

Consulta base:

```text
query_texts=[question]
n_results=top_k
include=["documents", "metadatas", "distances"]
```

El `top_k` por defecto del grafo LangGraph es `5`. En el nodo de retrieval, la consulta usada sigue esta prioridad:

```text
retrieval_query si existe
si no, question original
```

Esto permite que una transformación de consulta alimente el retrieval sin perder la pregunta original.

## Formateo y fallback

Los resultados de Chroma se normalizan en `agents/consulta_normativa/langchain_rag/formatting.py`.

Responsabilidades relevantes:

- normalizar documentos recuperados desde la forma anidada de Chroma;
- conservar el ID de Chroma como metadata auxiliar cuando está disponible;
- construir el contexto textual para el LLM;
- construir referencias deduplicadas.

Si no hay documentos recuperados, el sistema construye un contexto vacío controlado y el grafo puede responder con fallback determinístico por evidencia insuficiente, sin llamar innecesariamente al LLM.

## Separación de responsabilidades

La separación actual es correcta y debe preservarse:

| Capa | Debe hacer | No debe hacer |
|---|---|---|
| `pipeline/vectorization/` | Crear/abrir colección para ingest, transformar artefactos, escribir vectores. | Ejecutar lógica runtime del agente. |
| `agents/shared/chroma_retrieval.py` | Abrir colección existente y consultar Chroma. | Crear colecciones vacías o hacer ingest. |
| `agents/consulta_normativa/langchain_rag/` | Orquestar consulta, retrieval, contexto, generación y fallback. | Regenerar corpus o modificar Chroma. |

## Gotchas verificados

### Chroma no elimina registros obsoletos

La ingesta usa `upsert`. Si un chunk o tabla deja de existir en los JSONL de entrada, el registro anterior puede permanecer en Chroma. Para una reconstrucción limpia se debe borrar o mover:

```text
data/processed/chroma
```

antes de reingestar.

### `chromadb` puede faltar en el entorno

El código usa Chroma de forma lazy, pero `chromadb` no está listado en `requirements.txt`. Antes de ejecutar una ingesta real o consultas sobre Chroma, hay que verificar que el paquete esté instalado.

### El runtime depende de una colección existente

Esto es intencional. El CLI de consulta debe fallar si `data/processed/chroma` o la colección esperada no existen. Crear una colección vacía en runtime sería un comportamiento peligroso.

### Multi-Query/RRF requiere verificación de cableado activo

Existen constantes y helpers relacionados con Multi-Query/RRF, pero no se debe asumir que esa variante está activa sin revisar el builder usado por `agents/consulta_normativa/langchain_rag/main.py` y el grafo correspondiente.

### El CLI de LangGraph puede escribir una imagen durante setup

El runtime puede escribir `data/images/base_rag_graph.png`. Si `data/images/` no existe, la inicialización puede fallar por una causa secundaria, aunque Chroma y el LLM estén correctamente configurados.

## Verificación relacionada

Pruebas focalizadas para vectorización:

```bash
python -m unittest pipeline.tests.test_vectorization_documents pipeline.tests.test_vectorization_chroma_store
```

Pruebas focalizadas para retrieval y grafo RAG:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_graph agents.consulta_normativa.tests.test_rag_base
```

Suite vector/RAG más amplia documentada para el proyecto:

```bash
python -m unittest pipeline.tests.test_vectorization_documents pipeline.tests.test_vectorization_chroma_store agents.consulta_normativa.tests.test_cli agents.consulta_normativa.tests.test_rag_base agents.consulta_normativa.tests.test_langchain_rag_main agents.consulta_normativa.tests.test_langchain_rag_graph agents.consulta_normativa.tests.test_langchain_rag_query_rewrite agents.consulta_normativa.tests.test_langchain_rag_multi_query agents.consulta_normativa.tests.test_langchain_rag_fusion
```

## Conclusión

La arquitectura actual separa bien el ingest offline y el retrieval online. El punto más importante es no mezclar responsabilidades: `pipeline/vectorization/` debe construir la base vectorial, mientras que el agente debe consultar una colección ya existente. Los riesgos principales son operativos: registros obsoletos por `upsert`, dependencia de `chromadb` fuera de `requirements.txt`, y posible confusión entre helpers experimentales y el grafo realmente activo.
