# Arquitectura de vectorización SG-SST

La vectorización convierte los child chunks recomendados y los documentos de tabla en una colección ChromaDB persistente para el RAG base. La decisión central es mantener trazabilidad jurídica: cada registro indexado conserva metadatos planos suficientes para reconstruir fuente, artículo y relación lógica con tablas sin guardar rutas físicas del pipeline. La construcción completa de documentos de tabla se documenta en [`tables.md`](tables.md).

## Ruta rápida

Desde la raíz del repositorio:

```bash
python -m pipeline.chunking.main build-regex-constrained-semantic
python -m pipeline.chunking.main build-table-markdown
python -m pipeline.chunking.main build-table-documents
python -m pipeline.vectorization.main --batch-size 8
```

La ingesta escribe en `data/processed/chroma`, colección `sg_sst_base_rag`. Si se necesita una reconstrucción limpia, elimina o mueve `data/processed/chroma` antes de volver a ejecutar la vectorización.

## Entradas y salida

| Elemento | Ruta por defecto | Rol |
|---|---|---|
| Child chunks recomendados | `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` | Corpus normativo principal, con offsets exactos y jerarquía heredada. |
| Documentos vectorizables de tablas | `data/processed/table_documents.jsonl` | Tablas convertidas a documentos independientes; ver construcción y fragmentación en [`tables.md`](tables.md). |
| Persistencia ChromaDB | `data/processed/chroma` | Índice vectorial local persistente. |
| Colección ChromaDB | `sg_sst_base_rag` | Colección usada por ingesta y consulta normativa. |

Las rutas por defecto salen de `pipeline/chunking/core/config.py` y `pipeline/vectorization/ingest.py`. La CLI permite sobrescribirlas con `--chunks-path`, `--tables-path`, `--persist-path`, `--collection` y `--batch-size`, pero el flujo operativo recomendado usa los defaults del proyecto.

## Modelo de embeddings

La colección se abre con `SentenceTransformerEmbeddingFunction` y el modelo:

```text
Qwen/Qwen3-Embedding-0.6B
```

El modelo está centralizado como `DEFAULT_EMBEDDING_MODEL` en `pipeline/chunking/core/config.py`. La estrategia `regex_constrained_semantic` lo usa para calcular señales semánticas durante el chunking, y `pipeline/vectorization/chroma_store.py` lo usa como función de embeddings para ingesta y consulta en Chroma.

La consistencia importa por tres razones:

| Riesgo | Por qué importa |
|---|---|
| Cambiar embeddings entre ingesta y consulta | Las consultas se comparan contra vectores generados con otro espacio semántico y baja la calidad de recuperación. |
| Cambiar embeddings sin reconstruir Chroma | La colección queda mezclada con vectores antiguos y nuevos. |
| Evaluar con un índice no reproducible | Las métricas posteriores dejan de reflejar una configuración controlada. |

Si se cambia el modelo de embeddings, trata el cambio como una decisión de arquitectura y reconstruye `data/processed/chroma` desde cero.

## Normalización de documentos

Chroma recibe registros `ChromaRecord` con tres campos: `id`, `document` y `metadata`. La metadata se aplana porque Chroma acepta valores escalares, no estructuras anidadas arbitrarias.

### Child chunks

Cada child chunk se indexa con `document_type: child_chunk`.

Campos principales:

| Campo | Uso |
|---|---|
| `source_document_id`, `source_stem` | Identificar la norma fuente. |
| `normative_document_type`, `year` | Filtrar o auditar por tipo de norma y año cuando exista metadata heredada. |
| `parent_id` | Relacionar el child chunk con su parent chunk. |
| `title`, `chapter`, `article`, `articles`, `paragraph`, `numeral`, `literal` | Conservar jerarquía jurídica para referencias. |
| `start_char`, `end_char` | Mantener trazabilidad al Markdown limpio. |
| `has_tables`, `table_keys` | Indicar referencias lógicas a tablas asociadas. |

`table_keys` serializa una lista como texto separado por comas para mantener metadata plana.

### Documentos de tabla

Cada tabla se indexa como documento independiente con `document_type: table`.

Las tablas llegan a vectorización ya materializadas en `data/processed/table_documents.jsonl`. Una reconstrucción desde cero, o una reconstrucción después de cambiar tablas extraídas, debe ejecutar `build-table-markdown` antes de `build-table-documents`; el detalle de descubrimiento, fallback y fragmentación está en [`tables.md`](tables.md).

Campos principales:

| Campo | Uso |
|---|---|
| `source_stem` | Norma de origen. |
| `table_index` | Índice lógico de la tabla en la norma. |
| `table_key` | Relación estable `source_stem:table_index`. |
| `table_part_index`, `table_part_count` | Identificar partes cuando una tabla se divide antes de indexarse. |
| `linked_placeholder` | Placeholder Markdown asociado, por ejemplo `<!-- TABLE_0 -->`. |
| `oversized_row` | Señal de fila demasiado grande conservada como unidad. |

No se persisten rutas físicas HTML o Markdown dentro de Chroma. La relación tabla-chunk se conserva con metadata lógica (`source_stem`, `table_index`, `table_key`), lo que permite mover o regenerar artefactos sin romper las referencias indexadas.

## Política de ingesta y reconstrucción

La ingesta usa `open_or_create_collection(...)` porque su responsabilidad es crear o actualizar la colección persistente. Luego usa `upsert_records(...)`: inserta registros nuevos y actualiza registros existentes con el mismo `id`.

Esto tiene una consecuencia importante: `upsert` no elimina registros obsoletos. Si un chunk o tabla desaparece del JSONL fuente, el documento puede quedar en Chroma hasta que se haga una reconstrucción limpia.

Procedimiento recomendado para rebuild limpio:

```bash
rm -rf data/processed/chroma
python -m pipeline.chunking.main build-table-markdown
python -m pipeline.chunking.main build-table-documents
python -m pipeline.vectorization.main --batch-size 8
```

Si quieres conservar el índice anterior para comparación, muévelo en vez de borrarlo:

```bash
mv data/processed/chroma data/processed/chroma.backup
python -m pipeline.chunking.main build-table-markdown
python -m pipeline.chunking.main build-table-documents
python -m pipeline.vectorization.main --batch-size 8
```
