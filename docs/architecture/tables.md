# Arquitectura del procesamiento de tablas

Las tablas son contenido normativo de primera clase en el RAG SG-SST. En normas como la Resolución 0312 de 2019 y el Decreto 768 de 2022, obligaciones, criterios, fases, puntajes y clasificaciones aparecen en estructuras tabulares; si se tratan como texto accesorio, el sistema pierde evidencia clave para responder y diagnosticar cumplimiento.

## Ruta rápida

Ejecuta estos comandos desde la raíz del repositorio cuando ya existen Markdown limpio y chunks:

```bash
python -m pipeline.chunking.main audit-table-references
python -m pipeline.chunking.main build-table-markdown
python -m pipeline.chunking.main build-table-documents
python -m pipeline.tables.table_jsonl_to_html
```

`python -m pipeline.tables.table_jsonl_to_html` es opcional: solo genera una vista HTML para revisión humana.

En reconstrucciones desde cero, o después de cambiar la extracción de tablas, ejecuta siempre `build-table-markdown` antes de `build-table-documents`. El constructor de documentos descubre primero `data/processed/tables_markdown/*/table_*.md`; luego busca el HTML equivalente como fuente estructural preferida.

## Flujo extremo a extremo

El flujo se entiende mejor como cuatro transformaciones. Cada una produce un artefacto que la siguiente etapa reutiliza; no son pasos aislados.

| Fase | Qué hace | Artefactos principales |
|---|---|---|
| 1. Extraer y anclar | Convierte DOCX a Markdown, separa cada tabla como HTML y deja un placeholder `<!-- TABLE_n -->` en el punto exacto del texto. | Entrada: `data/raw/*.docx`.<br>Salidas: `data/interim/*.md`, `data/interim/tables/<source_stem>/table_<n>.html`. |
| 2. Referenciar y auditar | Los builders de chunking detectan placeholders y guardan referencias lógicas en `metadata.chunk.tables[]`; la auditoría compara esas referencias contra los HTML extraídos. | Entradas: `parents.jsonl`, `regex_constrained_semantic/chunks.jsonl`, `data/interim/tables/`.<br>Salida: reporte en stdout/stderr. |
| 3. Preparar documentos de tabla | Convierte HTML a Markdown derivado; luego `build-table-documents` descubre ese Markdown, prefiere el HTML equivalente para reconstruir estructura y genera documentos vectorizables. | Intermedio: `data/processed/tables_markdown/*/table_*.md`.<br>Salida: `data/processed/table_documents.jsonl`. |
| 4. Revisar e indexar | Opcionalmente genera HTML de revisión humana; después vectoriza tablas como documentos independientes junto con los child chunks. | Preview: `data/processed/tables_htlm/`.<br>Índice: `data/processed/chroma`, colección `sg_sst_base_rag`, `document_type: table`. |

La decisión central del flujo es esta: **los chunks no guardan rutas físicas de tablas**. Guardan identidad lógica (`source_stem`, `table_index`, `table_key`) y cada etapa deriva las rutas cuando necesita auditar, reconstruir o indexar.

## Decisiones de arquitectura

| Decisión | Motivo |
|---|---|
| Guardar HTML extraído en `data/interim/tables/` | El HTML conserva filas, celdas, `colspan` y `rowspan` mejor que una conversión temprana a texto plano. |
| Sustituir tablas por `<!-- TABLE_n -->` en Markdown | El chunk conserva el punto exacto donde aparece la tabla sin mezclar estructura HTML con texto normativo. |
| Usar metadata lógica en vez de rutas físicas | Las rutas locales son regenerables y no son portables; la identidad estable es `source_stem + table_index`. |
| Construir `table_key` como `source_stem:table_index` | Permite enlazar chunks, documentos de tabla y registros Chroma sin depender de ubicación en disco. |
| Usar `tables_markdown` como inventario | `build-table-documents` recorre `data/processed/tables_markdown/*/table_*.md`; por eso `build-table-markdown` debe ejecutarse antes cuando se reconstruye desde cero. |
| Preferir HTML y dejar Markdown como fallback | Cuando el HTML existe, se reconstruyen filas y celdas desde la estructura original; si no existe o no produce filas útiles, se fragmenta el Markdown derivado. |
| Dividir tablas grandes por filas | Evita documentos vectoriales excesivamente largos y repite filas de contexto para mantener interpretabilidad. |
| No dividir tablas con `rowspan` | Una celda vertical heredada puede aplicar a varias filas; dividirla podría separar el contexto que da sentido legal a las filas siguientes. |
| Indexar tablas como documentos independientes | Las consultas pueden recuperar directamente criterios, puntajes, actividades económicas o indicadores tabulares, no solo el párrafo que contiene el placeholder. |

## Metadata de referencias en chunks

`metadata.chunk.tables[]` aparece en parent chunks y child chunks cuando el texto contiene placeholders de tabla.

| Campo | Tipo | Significado |
|---|---|---|
| `placeholder` | string | Placeholder textual encontrado, por ejemplo `<!-- TABLE_0 -->`. |
| `source_stem` | string | Nombre base de la norma; identifica el subdirectorio bajo `data/interim/tables/`. |
| `table_index` | integer | Índice lógico de la tabla dentro de la norma. |

Ejemplo:

```json
{
  "placeholder": "<!-- TABLE_0 -->",
  "source_stem": "Resolución 0312 de 2019",
  "table_index": 0
}
```

La ruta física se deriva solo cuando se audita o se reconstruye: `data/interim/tables/<source_stem>/table_<table_index>.html`.

## Metadata de `table_documents.jsonl`

Cada línea de `data/processed/table_documents.jsonl` representa una tabla completa o una parte de tabla.

### Campos de primer nivel

| Campo | Tipo | Significado |
|---|---|---|
| `id` | string | Identificador estable y seguro para Chroma, por ejemplo `table-resolucion-0312-de-2019-0-part-0000`. |
| `text` | string | Texto Markdown-like que se indexa. Incluye filas de contexto, separador y filas de datos. |
| `metadata` | object | Metadata lógica de la tabla o parte. |

### Campos en `metadata`

| Campo | Tipo | Significado |
|---|---|---|
| `type` | string | Siempre `table` en documentos de tabla. |
| `source_stem` | string | Norma de origen. |
| `table_index` | integer | Índice lógico de la tabla dentro de la norma. |
| `table_key` | string | Clave estable `source_stem:table_index`. |
| `linked_placeholder` | string | Placeholder asociado en el Markdown, por ejemplo `<!-- TABLE_0 -->`. |
| `table_part_index` | integer | Índice de la parte dentro de una tabla fragmentada. |
| `table_part_count` | integer | Número total de partes de esa tabla. |
| `oversized_row` | boolean | `true` si una fila individual excede el límite y se conserva como parte propia. |

## Metadata plana en Chroma

Durante la vectorización, `pipeline/vectorization/documents.py` convierte cada documento de tabla en un registro Chroma con `document_type: table` y metadata escalar.

| Campo Chroma | Origen | Nota |
|---|---|---|
| `document_type` | constante | `table`. |
| `source_stem` | `metadata.source_stem` | Fuente normativa. |
| `table_index` | `metadata.table_index` | Convertido a entero. |
| `table_key` | `metadata.table_key` o derivado | Relación estable con chunks. |
| `linked_placeholder` | `metadata.linked_placeholder` | Placeholder del Markdown. |
| `table_part_index` | `metadata.table_part_index` | Default `0` si falta por compatibilidad. |
| `table_part_count` | `metadata.table_part_count` | Default `1` si falta por compatibilidad. |
| `oversized_row` | `metadata.oversized_row` | Booleano plano aceptado por Chroma. |

Los child chunks se indexan aparte con `document_type: child_chunk`, `has_tables` y `table_keys` como texto separado por comas cuando tienen referencias tabulares.
