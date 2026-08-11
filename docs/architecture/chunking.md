# Arquitectura del pipeline de chunking

El pipeline de chunking convierte normas SG-SST en unidades recuperables para RAG sin romper la trazabilidad jurídica. Su salida principal recomendada es `data/processed/chunks/regex_constrained_semantic/chunks.jsonl`, complementada por `parents.jsonl` y baselines de comparación.

## Ruta operativa actual

Ejecuta los comandos desde la raíz del repositorio:

```bash
python -m pipeline.chunking.main build-parents
python -m pipeline.chunking.main build-sliding-window
python -m pipeline.chunking.main build-semantic
python -m pipeline.chunking.main build-regex-constrained-semantic
```

## Por qué existe este pipeline

El RAG normativo no puede tratar la ley como texto genérico. Una respuesta útil para SG-SST debe recuperar obligaciones con fuente, artículo, jerarquía normativa y, cuando aplique, tablas asociadas. El chunking existe para equilibrar tres necesidades:

| Necesidad | Decisión de arquitectura |
|---|---|
| Recuperación semántica | Crear child chunks suficientemente pequeños para búsqueda vectorial. |
| Trazabilidad jurídica | Mantener offsets, fuente, artículo y jerarquía heredada. |
| Evaluación reproducible | Generar artefactos deterministas y comparables entre estrategias. |

Por eso el flujo separa parent chunks jurídicos de child chunks recuperables: primero se respeta la estructura legal, luego se prueban estrategias de división fina.

## Flujo de datos

| Paso | Entrada | Salida | Rol |
|---|---|---|---|
| Parent chunks | `data/processed/*.md` + manifest opcional | `data/processed/chunks/parents.jsonl` | Divide por límites legales y conserva metadata heredada. |
| Sliding-window baseline | `parents.jsonl` | `data/processed/chunks/sliding_window/chunks.jsonl` | Baseline mecánico con ventana token-aware. |
| Semantic baseline | `parents.jsonl` | `data/processed/chunks/semantic_chunking/chunks.jsonl` | Baseline experimental con `SemanticChunker`. |
| Regex-constrained semantic | `parents.jsonl` | `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` | Estrategia recomendada: cortes semánticos con spans exactos. |
| Auditoría de tablas | `parents.jsonl` + estrategia recomendada + HTML extraído | Reporte en stdout/stderr | Verifica referencias lógicas contra tablas físicas extraídas. |
| Auditoría y documentos de tablas | Placeholders + HTML extraído | Reporte + artefactos vector-ready | Se documenta en detalle en [`tables.md`](tables.md). |


## Parent chunks y límites jurídicos

`pipeline/chunking/hierarchical_splitter/parent_builder.py` descubre Markdown limpio en `data/processed/`, excluye salidas generadas y construye parent chunks por documento. La detección estructural está en `pipeline/chunking/structural_analysis/` y usa regex conservadoras para títulos, capítulos, secciones, artículos, parágrafos, numerales y literales.

La división principal ocurre por `Artículo`. Si hay texto antes del primer artículo, se emite como preámbulo no indexable. Si un documento no tiene artículos detectables, se conserva como documento completo. Los artículos pequeños pueden agruparse con artículos contiguos cuando el tamaño lo justifica, pero el parent mantiene trazabilidad mediante `hierarchy.articles`.

Cada parent chunk conserva:

- `start_char` y `end_char` sobre el Markdown limpio.
- `source_document_id`, `source_path` y `parent_index`.
- metadata heredada de fuente y jerarquía legal.
- metadata de estrategia, razón de corte y referencias mínimas a tablas si aparecen placeholders `<!-- TABLE_n -->`.

Esta capa evita que los child chunks crucen límites normativos importantes sin contexto.

### Metadata de parent chunks

La tabla resume los campos observados en `data/processed/chunks/parents.jsonl` después de analizar los chunks generados actualmente: 138 registros padre.

| Campo | Significado |
|---|---|
| `chunk_id` | Identificador único del parent chunk. Combina el documento fuente, el índice del parent y un sufijo estable para trazabilidad. |
| `source_document_id` | Identificador normalizado del documento limpio del que proviene el chunk. Permite agrupar todos los chunks de una misma norma. |
| `source_path` | Ruta absoluta del Markdown limpio usado como fuente. Es útil para auditoría local, pero no debe tratarse como metadata portable para Chroma. |
| `parent_index` | Posición secuencial del parent dentro del documento fuente. |
| `text` | Texto completo del parent chunk. En general corresponde a un artículo, grupo de artículos, preámbulo o documento completo sin artículos detectados. |
| `start_char` | Offset inicial del parent dentro del Markdown limpio. |
| `end_char` | Offset final exclusivo del parent dentro del Markdown limpio. |
| `token_count` | Estimación de tokens del texto del parent. Sirve para controlar tamaños y comparar estrategias. |
| `metadata.inherited.document_type` | Tipo de norma inferido, por ejemplo `decreto`, `resolución` o `ley`. |
| `metadata.inherited.legal_source` | Origen/calidad de la fuente normativa según manifest o inferencia. En los datos actuales aparece como `official_candidate`. |
| `metadata.inherited.source_name` | Nombre legible de la fuente normativa. |
| `metadata.inherited.source_stem` | Nombre base usado para enlazar artefactos derivados, especialmente tablas. |
| `metadata.inherited.year` | Año de la norma inferido desde nombre, manifest o contenido. |
| `metadata.inherited.title` | Título normativo detectado cuando aplica. No aparece en todos los chunks. |
| `metadata.inherited.chapter` | Capítulo heredado cuando el documento o fragmento lo permite. No aparece en todos los chunks. |
| `metadata.inherited.hierarchy` | Objeto con la jerarquía jurídica detectada para el fragmento. Puede incluir título, capítulo, artículo, parágrafo, numeral, literal o lista de artículos agrupados. |
| `metadata.inherited.hierarchy.article` | Artículo principal detectado para el parent. Está ausente en preámbulos o fragmentos sin artículo. |
| `metadata.inherited.hierarchy.articles` | Lista de artículos cubiertos cuando un parent agrupa más de un artículo pequeño. |
| `metadata.inherited.hierarchy.paragraph` | Parágrafo detectado dentro del fragmento, si existe. |
| `metadata.inherited.hierarchy.numeral` | Numeral detectado dentro del fragmento, si existe. |
| `metadata.inherited.hierarchy.literal` | Literal detectado dentro del fragmento, si existe. |
| `metadata.chunk.parent_index` | Copia del índice secuencial dentro de la metadata específica del chunk. |
| `metadata.chunk.strategy` | Estrategia que produjo el parent, por ejemplo `parent_article_boundary` o `parent_document_preamble`. |
| `metadata.chunk.split_reason` | Razón concreta del corte, por ejemplo `article_boundary` o `document_preamble_before_first_article`. |
| `metadata.chunk.section_type` | Tipo de sección especial. En los datos actuales aparece para preámbulos. |
| `metadata.chunk.indexable` | Indica si el parent debe considerarse indexable. En preámbulos puede ser `false`. |
| `metadata.chunk.tables[]` | Lista opcional de referencias lógicas a tablas mencionadas con placeholders `<!-- TABLE_n -->`. |
| `metadata.chunk.tables[].placeholder` | Placeholder textual encontrado en el Markdown, por ejemplo `<!-- TABLE_0 -->`. |
| `metadata.chunk.tables[].table_index` | Índice lógico de la tabla dentro del documento fuente. |
| `metadata.chunk.tables[].source_stem` | Fuente usada junto con `table_index` para derivar la ruta física de la tabla extraída. |

## Estrategias de child chunks

### Sliding-window baseline

`build-sliding-window` usa `RecursiveCharacterTextSplitter.from_tiktoken_encoder` con valores fijos. Es útil como baseline porque es simple, rápido de comparar y obliga a validar que los offsets del child coincidan con el texto del parent. No es la estrategia principal porque el corte mecánico puede separar obligaciones, excepciones o condiciones jurídicas que deberían leerse juntas.

### Semantic baseline

`build-semantic` usa `SemanticChunker` con embeddings multilingües normalizados. Sirve como baseline semántico para contrastar calidad de recuperación, pero no es la salida recomendada para indexación principal: el backend puede reconstruir o normalizar texto internamente. Cuando el child emitido no aparece como substring exacto del parent, el pipeline escribe `start_char: null`, `end_char: null`, `offset_status: unresolved` y `offset_reason: semantic_chunk_text_not_exact_substring`.

Ese comportamiento es aceptable para experimentación, pero débil para citación legal y auditoría de respuestas.

### Regex-constrained semantic

`build-regex-constrained-semantic` combina señales semánticas con restricciones de spans exactos:

1. Extrae unidades textuales exactas por párrafos; si un párrafo supera el límite, lo divide en unidades tipo oración.
2. Calcula distancias semánticas entre unidades contiguas mediante embeddings.
3. Propone breakpoints semánticos por gradiente.
4. Ajusta tamaños mínimos y máximos mediante fusiones o divisiones, sin abandonar spans del texto fuente.
5. Emite child chunks con `offset_status: resolved` y exige offsets resueltos.

Es la estrategia recomendada para SG-SST porque preserva simultáneamente significado y evidencia verificable. Las respuestas RAG pueden citar un artículo o fragmento con offsets exactos, reconstruir el contexto del parent y mantener referencias a tablas vinculadas.

### Metadata de child chunks recomendados

La tabla resume los campos observados en `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` después de analizar los chunks generados actualmente: 330 registros hijo. Esta es la salida recomendada para indexación RAG.

| Campo | Significado |
|---|---|
| `chunk_id` | Identificador único del child chunk. Deriva del parent y añade el índice del child más un sufijo estable. |
| `parent_id` | Identificador del parent chunk del que proviene. Permite reconstruir contexto jurídico más amplio. |
| `source_document_id` | Identificador del documento fuente heredado desde el parent. |
| `text` | Texto recuperable que se indexa como fragmento normativo. |
| `start_char` | Offset inicial del child en el Markdown limpio. En la estrategia recomendada debe estar resuelto. |
| `end_char` | Offset final exclusivo del child en el Markdown limpio. En la estrategia recomendada debe estar resuelto. |
| `token_count` | Estimación de tokens del child. Permite validar límites de recuperación y tamaño de contexto. |
| `metadata.inherited.*` | Metadata jurídica heredada del parent: fuente, año, tipo documental y jerarquía normativa. Se conserva para que cada child sea recuperable sin perder contexto legal. |
| `metadata.inherited.hierarchy.article` | Artículo principal heredado cuando aplica. Es clave para citas normativas. |
| `metadata.inherited.hierarchy.articles` | Artículos cubiertos si el parent original agrupó más de un artículo. |
| `metadata.inherited.hierarchy.paragraph` | Parágrafo heredado o detectado en el contexto del fragmento. |
| `metadata.inherited.hierarchy.numeral` | Numeral heredado o detectado en el contexto del fragmento. |
| `metadata.inherited.hierarchy.literal` | Literal heredado o detectado en el contexto del fragmento. |
| `metadata.chunk.strategy` | Estrategia que produjo el child. En la salida recomendada es `regex_constrained_semantic`. |
| `metadata.chunk.backend` | Implementación concreta usada por la estrategia. En la salida actual es `custom_regex_constrained_semantic`. |
| `metadata.chunk.parent_chunk_id` | Copia del identificador del parent dentro de la metadata del child. Debe coincidir con `parent_id`. |
| `metadata.chunk.chunk_index` | Índice secuencial del child dentro de su parent. |
| `metadata.chunk.split_reason` | Motivo del corte. En la estrategia recomendada aparece como `semantic_breakpoint_with_regex_constraints`. |
| `metadata.chunk.offset_status` | Estado de trazabilidad de offsets. En la salida recomendada debe ser `resolved`; en baselines semánticos puede ser `unresolved`. |
| `metadata.chunk.size_adjustment` | Ajuste aplicado para cumplir límites de tamaño, por ejemplo `none`, `merged_small_chunk` o `split_oversized_chunk`. |
| `metadata.chunk.unit_count` | Número de unidades textuales exactas agregadas en el child. |
| `metadata.chunk.unit_types` | Tipos de unidades usadas para construir el child, por ejemplo párrafos u oraciones según el corte aplicado. |
| `metadata.chunk.embedding_model` | Modelo usado para calcular señales semánticas entre unidades. Actualmente `Qwen/Qwen3-Embedding-0.6B`. |
| `metadata.chunk.breakpoint_threshold_type` | Tipo de umbral usado para proponer cortes semánticos. Actualmente `gradient`. |
| `metadata.chunk.breakpoint_threshold_amount` | Valor del umbral semántico. Actualmente `95`. |
| `metadata.chunk.tables[]` | Lista opcional de referencias lógicas a tablas heredadas o presentes en el fragmento. Mantiene la relación con `data/interim/tables/` sin guardar rutas físicas. |
| `metadata.chunk.tables[].placeholder` | Placeholder de tabla encontrado en el texto del child. |
| `metadata.chunk.tables[].table_index` | Índice lógico de la tabla dentro de la fuente. |
| `metadata.chunk.tables[].source_stem` | Fuente usada para resolver la tabla física cuando se audita o se construyen documentos de tabla. |

La diferencia clave es que el parent documenta el límite jurídico amplio, mientras que el child documenta el fragmento recuperable. Por eso el child duplica metadata heredada: el retriever puede devolver un fragmento pequeño sin perder fuente, artículo, jerarquía ni vínculo con tablas.

## Configuración fija y personalización

La configuración central está en `pipeline/chunking/core/config.py`:

| Constante | Valor actual |
|---|---|
| `DEFAULT_CLEANED_MARKDOWN_DIR` | `data/processed` |
| `DEFAULT_TABLES_ROOT` | `data/interim/tables` |
| `DEFAULT_TABLE_MARKDOWN_ROOT` | `data/processed/tables_markdown` |
| `DEFAULT_TABLE_DOCUMENTS_PATH` | `data/processed/table_documents.jsonl` |
| `DEFAULT_PARENT_CHUNKS_PATH` | `data/processed/chunks/parents.jsonl` |
| `DEFAULT_SLIDING_WINDOW_CHUNKS_PATH` | `data/processed/chunks/sliding_window/chunks.jsonl` |
| `DEFAULT_SEMANTIC_CHUNKS_PATH` | `data/processed/chunks/semantic_chunking/chunks.jsonl` |
| `DEFAULT_REGEX_CONSTRAINED_SEMANTIC_CHUNKS_PATH` | `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` |
| `DEFAULT_MIN_TOKENS` | `80` |
| `DEFAULT_MAX_TOKENS` | `350` |
| `DEFAULT_SLIDING_WINDOW_CHUNK_SIZE` | `350` |
| `DEFAULT_SLIDING_WINDOW_CHUNK_OVERLAP` | `70` |
| `DEFAULT_EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-0.6B` |
| `DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE` | `gradient` |
| `DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT` | `95` |

## Relación con tablas

El chunking conserva solo la relación mínima entre texto y tablas. Cuando un fragmento contiene placeholders `<!-- TABLE_n -->`, `metadata.chunk.tables[]` guarda `placeholder`, `source_stem` y `table_index`; no guarda rutas físicas.

Esa metadata permite auditar referencias y enlazar los chunks con documentos vectoriales de tabla mediante `source_stem + table_index`. La extracción, conversión, fragmentación e indexación de tablas se documenta en [`tables.md`](tables.md).
