# Guía de vectorización y RAG base

Esta guía explica cómo convertir los artefactos del chunking en una colección ChromaDB y cómo consultar el RAG base de consulta normativa SG-SST desde terminal.

## Ruta rápida

Desde la raíz del proyecto:

```bash
# Si cambió data/processed/table_documents.jsonl, regenéralo antes de vectorizar.
python -m pipeline.chunking.main build-table-documents

python -m pipeline.vectorization.main --batch-size 8
export GROQ_API_KEY="tu_api_key"
python -m agents.consulta_normativa.main ask "¿Qué debe incluir el plan anual de trabajo del SG-SST?"
```

El primer comando reconstruye los documentos vectorizables de tablas. El segundo indexa child chunks y documentos de tablas en ChromaDB. El tercero consulta la colección ya indexada usando el agente RAG base.

Vista previa opcional de tablas, útil para inspección manual antes de vectorizar:

```bash
python -m pipeline.tables.table_jsonl_to_html
```

## Entradas y salidas

| Elemento | Ruta por defecto | Uso |
|---|---|---|
| Child chunks recomendados | `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` | Corpus normativo principal. |
| Markdown derivado de tablas | `data/processed/tables_markdown` | Lista de tablas disponibles y ruta lógica por documento. |
| HTML estructural de tablas | `data/interim/tables` | Fuente preferida para reconstruir filas y celdas cuando existe. |
| Documentos vector-ready de tablas | `data/processed/table_documents.jsonl` | Tablas convertidas a documentos indexables desde HTML o fallback Markdown. |
| Vista previa HTML de tablas | `data/processed/tables_htlm` | Archivos de inspección generados desde `table_documents.jsonl`. |
| Base ChromaDB persistente | `data/processed/chroma` | Almacén vectorial local. |
| Colección ChromaDB | `sg_sst_base_rag` | Colección usada por ingesta y consulta. |

> Nota: `tables_htlm` conserva el nombre real del directorio implementado actualmente.

## Modelo de embeddings

La colección ChromaDB usa explícitamente el mismo modelo base del chunking semántico:

```txt
Qwen/Qwen3-Embedding-0.6B
```

Esto mantiene consistencia entre:

- cortes semánticos del pipeline de chunking;
- embeddings usados para recuperación en ChromaDB;
- evaluación posterior del RAG.

La función de embeddings se configura en:

```txt
pipeline/vectorization/chroma_store.py
```

mediante `SentenceTransformerEmbeddingFunction` de Chroma.

## Ingesta vectorial

### 1. Regenerar documentos de tablas cuando cambie el JSONL

```bash
python -m pipeline.chunking.main build-table-documents \
  --markdown-root data/processed/tables_markdown \
  --output-path data/processed/table_documents.jsonl
```

Este comando descubre `table_*.md` bajo `data/processed/tables_markdown`, pero la fuente estructural preferida es el HTML correspondiente bajo `data/interim/tables`. Si no hay HTML disponible, usa el Markdown como fallback.

### 2. Vista previa opcional

```bash
python -m pipeline.tables.table_jsonl_to_html \
  --input-path data/processed/table_documents.jsonl \
  --output-dir data/processed/tables_htlm
```

Genera un `index.html` y un HTML por registro de tabla para revisar contenido, partes y metadata antes de indexar.

### 3. Vectorizar en ChromaDB

Comando base:

```bash
python -m pipeline.vectorization.main --batch-size 8
```

Parámetros opcionales:

```bash
python -m pipeline.vectorization.main \
  --chunks-path data/processed/chunks/regex_constrained_semantic/chunks.jsonl \
  --tables-path data/processed/table_documents.jsonl \
  --persist-path data/processed/chroma \
  --collection sg_sst_base_rag \
  --batch-size 8
```

`--batch-size` controla cuántos documentos se envían por lote a Chroma. Un valor mayor puede acelerar la ingesta, pero consume más RAM porque agrupa más textos y embeddings en cada operación. Si el equipo se queda sin memoria, baja el valor; el valor por defecto actual es `8`.

La ingesta realiza este flujo:

```txt
child chunks JSONL
table documents JSONL
  → normalización a registros Chroma
  → metadata plana
  → validación de texto no vacío
  → open_or_create_collection(...)
  → upsert_records(...)
```

La ingesta falla de forma controlada si faltan los JSONL de entrada. Esto evita crear una colección vacía por accidente.

### Reset/rebuild de Chroma

La ingesta usa `upsert`: actualiza o inserta registros con el mismo `id`, pero no elimina de Chroma documentos que ya no existan en los JSONL fuente. Si cambiaste `chunks.jsonl` o `table_documents.jsonl` y quieres una reconstrucción limpia, elimina o mueve `data/processed/chroma` antes de volver a ejecutar la vectorización.

## Metadata indexada

### Child chunks

Cada child chunk se indexa como documento de tipo:

```txt
child_chunk
```

Metadata principal:

```json
{
  "document_type": "child_chunk",
  "source_document_id": "...",
  "source_stem": "...",
  "normative_document_type": "...",
  "year": 2019,
  "parent_id": "...",
  "title": "...",
  "chapter": "...",
  "article": "...",
  "start_char": 0,
  "end_char": 0,
  "has_tables": false,
  "table_keys": ""
}
```

### Tablas

Cada tabla se indexa como documento independiente de tipo:

```txt
table
```

Metadata principal:

```json
{
  "document_type": "table",
  "source_stem": "Resolución 0312 de 2019",
  "table_index": 0,
  "table_part_index": 0,
  "table_part_count": 1,
  "table_key": "Resolución 0312 de 2019:0",
  "linked_placeholder": "<!-- TABLE_0 -->",
  "oversized_row": false
}
```

No se guardan rutas físicas dentro de ChromaDB. La relación tabla-chunk se conserva mediante claves lógicas como `source_stem:table_index`. Cuando una tabla grande se divide, todos los registros comparten `table_key` y se diferencian por `table_part_index`.

## Generación de `table_documents.jsonl`

El JSONL de tablas no es una copia directa de `data/processed/tables_markdown/*.md`.

Flujo actual:

```txt
data/processed/tables_markdown/*/table_*.md
  → descubre documentos y table_index
  → busca HTML equivalente en data/interim/tables
  → parsea filas/celdas desde HTML cuando existe
  → genera texto tipo Markdown en table_documents.jsonl
```

Reglas importantes:

- `colspan` se expande horizontalmente repitiendo el texto de la celda, para conservar encabezados semánticos.
- Las tablas grandes sin `rowspan` se dividen en varios registros: `part-0000`, `part-0001`, etc.
- Las tablas con `rowspan` se mantienen en un solo registro para no perder contexto vertical heredado.
- El campo JSONL `text` es texto tipo Markdown generado desde HTML; no es HTML crudo y no necesariamente coincide con el `.md` en `tables_markdown`.
- Las estructuras complejas con `rowspan` quedan simplificadas: se evita partirlas, pero no se reconstruye plenamente la herencia vertical de celdas.

## Consulta del RAG base

Antes de consultar, define la clave de Groq en el entorno:

```bash
export GROQ_API_KEY="tu_api_key"
```

Luego ejecuta:

```bash
python -m agents.consulta_normativa.main ask "¿Qué debe incluir el plan anual de trabajo del SG-SST?"
```

El flujo interno es:

```txt
pregunta
  → open_existing_collection(...)
  → chroma_retriever(collection)
  → answer_question(..., top_k=5)
  → contexto recuperado
  → prompt base
  → ChatGroq
  → respuesta + referencias
```

La consulta usa `open_existing_collection(...)`, no `get_or_create_collection(...)`. Esto es intencional: consultar no debe crear una colección vacía si la ingesta no se ha ejecutado.

## LLM por defecto

El generador por defecto usa Groq:

```txt
openai/gpt-oss-120b
```

con temperatura:

```txt
0
```

La clave `GROQ_API_KEY` solo se lee desde variables de entorno. No debe guardarse en archivos del proyecto.

## Salida esperada

Formato base:

```txt
Respuesta:
<respuesta generada>

Referencias:
- <fuente usada>
- <fuente usada>
```

Si no se recupera evidencia suficiente:

```txt
Respuesta:
La evidencia recuperada es insuficiente para responder la pregunta.

Referencias:
```

## Archivos principales

| Archivo | Responsabilidad |
|---|---|
| `pipeline/vectorization/documents.py` | Normaliza chunks y tablas a registros compatibles con ChromaDB. |
| `pipeline/vectorization/chroma_store.py` | Abre colecciones ChromaDB, configura embeddings Qwen y ejecuta upsert/query. |
| `pipeline/vectorization/ingest.py` | Orquesta la ingesta vectorial y reporta conteos. |
| `pipeline/vectorization/main.py` | CLI central de ingesta vectorial. |
| `pipeline/tables/table_documents.py` | Construye `table_documents.jsonl` desde tablas Markdown/HTML y metadata de partes. |
| `pipeline/tables/table_jsonl_to_html.py` | Genera HTML de vista previa para inspeccionar registros de tablas. |
| `pipeline/chunking/main.py` | Entrypoint recomendado para comandos de chunking, incluido `build-table-documents`. |
| `pipeline/chunking/core/cli.py` | Define la CLI interna usada por `pipeline.chunking.main`. |
| `agents/consulta_normativa/main.py` | CLI `ask` para consultar el RAG base. |
| `agents/consulta_normativa/rag_base.py` | Flujo base: recuperar, construir contexto, generar respuesta y referencias. |
| `agents/consulta_normativa/prompts.py` | Prompt base del RAG. |

## Validación mínima

Ejecuta pruebas enfocadas:

```bash
python -m unittest \
  pipeline.tests.test_table_documents \
  pipeline.tests.test_vectorization_documents \
  pipeline.tests.test_vectorization_chroma_store \
  pipeline.tests.test_consulta_normativa_cli \
  pipeline.tests.test_consulta_normativa_rag_base
```

Compila los módulos principales:

```bash
python -m compileall pipeline/tables pipeline/vectorization agents/consulta_normativa
```

## Errores comunes

| Error | Causa probable | Acción |
|---|---|---|
| `Input JSONL does not exist` | No se generaron chunks o documentos de tablas. | Ejecutar primero el pipeline de chunking y tablas. |
| `ChromaDB persist path does not exist` | Se intentó consultar antes de ingestar. | Ejecutar `python -m pipeline.vectorization.main`. |
| `langchain_groq is not installed` | Falta dependencia del generador Groq. | Instalar dependencias del proyecto. |
| `GROQ_API_KEY is not configured` | No se definió la variable de entorno. | Ejecutar `export GROQ_API_KEY="..."`. |
| Error al cargar modelo Qwen | Falta dependencia/modelo o no hay acceso a descarga/cache. | Verificar `sentence-transformers`, Chroma y disponibilidad del modelo. |

## Límites de esta etapa

Este RAG base no incluye:

- expansión hacia parent chunks;
- memoria conversacional;
- contexto empresarial;
- reranking;
- recuperación híbrida;
- validación avanzada de respuestas;
- API REST o frontend.

La intención es tener una línea base simple, medible y fácil de comparar antes de introducir mejoras.
