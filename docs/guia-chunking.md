# Guía de uso del pipeline de chunking

Esta guía explica cómo ejecutar el pipeline de chunking del corpus normativo SG-SST. El objetivo es convertir Markdown limpio en parent chunks, child chunks y documentos de tablas listos para evaluación o recuperación RAG.

## Ruta rápida recomendada

Ejecuta estos comandos desde la raíz del proyecto:

```bash
python -m pipeline.chunking.main build-parents
python -m pipeline.chunking.main build-sliding-window
python -m pipeline.chunking.main build-regex-constrained-semantic
python -m pipeline.chunking.main audit-table-references \
  --chunks-path data/processed/chunks/parents.jsonl \
  --chunks-path data/processed/chunks/regex_constrained_semantic/chunks.jsonl
python -m pipeline.chunking.main build-table-markdown
python -m pipeline.chunking.main build-table-documents
```

`build-regex-constrained-semantic` es la estrategia principal recomendada para el corpus normativo porque conserva offsets exactos y trazabilidad jurídica. `build-sliding-window` se mantiene como baseline mecánico.

## Entradas y salidas

| Tipo | Ruta por defecto |
|---|---|
| Markdown limpio | `data/processed/*.md` |
| Tablas HTML extraídas | `data/interim/tables/` |
| Parent chunks | `data/processed/chunks/parents.jsonl` |
| Child chunks sliding window | `data/processed/chunks/sliding_window/chunks.jsonl` |
| Child chunks semantic baseline | `data/processed/chunks/semantic_chunking/chunks.jsonl` |
| Child chunks híbridos | `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` |
| Tablas Markdown derivadas | `data/processed/tables_markdown/` |
| Documentos vector-ready de tablas | `data/processed/table_documents.jsonl` |

Los archivos en `data/processed/chunks/`, `data/processed/tables_markdown/` y `data/processed/table_documents.jsonl` son derivados. No los edites manualmente; regenéralos con los comandos del pipeline.

## Comandos principales

### 1. Construir parent chunks

```bash
python -m pipeline.chunking.main build-parents
```

Lee Markdown limpio y genera chunks padre por estructura normativa. Los parent chunks conservan metadata de fuente, estructura jurídica, offsets, conteo de tokens y referencias mínimas a tablas cuando el texto contiene placeholders como `<!-- TABLE_0 -->`.

Parámetros útiles:

```bash
--input-dir data/processed
--output-path data/processed/chunks/parents.jsonl
--manifest-path data/processed/metadata/source_manifest.json
--tables-root data/interim/tables
```

### 2. Construir baseline sliding window

```bash
python -m pipeline.chunking.main build-sliding-window
```

Genera child chunks mecánicos desde `parents.jsonl`. Úsalo como baseline de comparación.

Parámetros útiles:

```bash
--chunk-size 350
--chunk-overlap 70
--input-path data/processed/chunks/parents.jsonl
--output-path data/processed/chunks/sliding_window/chunks.jsonl
```

### 3. Construir baseline semantic

```bash
python -m pipeline.chunking.main build-semantic
```

Genera chunks con `SemanticChunker`. Esta estrategia se conserva como baseline experimental porque puede producir offsets no resueltos cuando reconstruye texto internamente.

Parámetros útiles:

```bash
--breakpoint-threshold-type gradient
--breakpoint-threshold-amount 95
```

### 4. Construir estrategia híbrida recomendada

```bash
python -m pipeline.chunking.main build-regex-constrained-semantic
```

Genera child chunks combinando unidades textuales con offsets exactos y cortes semánticos. Es la estrategia recomendada para el corpus SG-SST porque mantiene trazabilidad para citación normativa.

Parámetros útiles:

```bash
--breakpoint-threshold-type gradient
--breakpoint-threshold-amount 95
--min-tokens 80
--max-tokens 350
```

## Manejo de tablas

Durante la ingestión DOCX → Markdown, las tablas HTML se extraen a:

```txt
data/interim/tables/<source_stem>/table_<n>.html
```

En el Markdown queda un placeholder:

```md
<!-- TABLE_0 -->
```

Los chunks no guardan HTML ni rutas físicas. Solo guardan metadata mínima:

```json
{
  "placeholder": "<!-- TABLE_0 -->",
  "table_index": 0,
  "source_stem": "Resolución 0312 de 2019"
}
```

La ruta real se deriva cuando se necesita:

```txt
data/interim/tables/<source_stem>/table_<table_index>.html
```

### Auditar referencias de tablas

```bash
python -m pipeline.chunking.main audit-table-references \
  --chunks-path data/processed/chunks/parents.jsonl \
  --chunks-path data/processed/chunks/regex_constrained_semantic/chunks.jsonl
```

La auditoría tiene dos resultados importantes:

| Resultado | Comportamiento |
|---|---|
| Tabla referenciada inexistente | Error bloqueante |
| Tabla HTML huérfana | Warning para revisión manual |

### Convertir tablas HTML a Markdown

```bash
python -m pipeline.chunking.main build-table-markdown
```

Convierte `table_*.html` a Markdown derivado usando Pandoc/pypandoc. La salida queda en:

```txt
data/processed/tables_markdown/<source_stem>/table_<n>.md
```

### Crear documentos vector-ready de tablas

```bash
python -m pipeline.chunking.main build-table-documents
```

Genera un JSONL con documentos de tabla independientes, listos para indexación posterior:

```txt
data/processed/table_documents.jsonl
```

Cada documento conserva metadata lógica, no rutas físicas:

```json
{
  "id": "table-resolucion-0312-de-2019-0",
  "text": "| Estándar | Ítem | Modo de verificación |\n|---|---|---|...",
  "metadata": {
    "type": "table",
    "source_stem": "Resolución 0312 de 2019",
    "table_index": 0,
    "linked_placeholder": "<!-- TABLE_0 -->"
  }
}
```

## Qué estrategia usar

| Estrategia | Uso recomendado |
|---|---|
| `build-sliding-window` | Baseline mecánico rápido para comparar. |
| `build-semantic` | Baseline experimental con embeddings; no es la estrategia principal por trazabilidad débil. |
| `build-regex-constrained-semantic` | Estrategia principal recomendada para SG-SST. |

## Validación mínima

Verifica que la CLI esté disponible:

```bash
python -m pipeline.chunking.main --help
python -m pipeline.chunking.main build-parents --help
python -m pipeline.chunking.main build-regex-constrained-semantic --help
python -m pipeline.chunking.main audit-table-references --help
python -m pipeline.chunking.main build-table-markdown --help
python -m pipeline.chunking.main build-table-documents --help
```

Ejecuta pruebas enfocadas del flujo de tablas:

```bash
python -m unittest pipeline.tests.test_table_references pipeline.tests.test_table_markdown pipeline.tests.test_table_documents
```

Si el entorno tiene todas las dependencias opcionales instaladas, puedes ejecutar:

```bash
python -m unittest discover -s pipeline/tests
```

## Errores comunes

| Error | Causa probable | Acción |
|---|---|---|
| `No module named 'langchain_text_splitters'` | Falta dependencia de sliding window. | Instalar dependencias del pipeline. |
| `No module named 'langchain_experimental'` | Falta dependencia de semantic chunking. | Instalar dependencias semánticas. |
| Error de `transformers` o tokenizer | Falta dependencia o modelo no disponible. | Instalar `transformers` y permitir descarga/caché del modelo. |
| Error de Pandoc/pypandoc | Pandoc no está instalado o no está disponible. | Instalar Pandoc y verificar `pypandoc`. |
| `Missing referenced table files` | Un chunk referencia una tabla HTML que no existe. | Revisar `data/interim/tables/` y la numeración `TABLE_n`. |
| Warning de tablas huérfanas | Hay HTML extraído no referenciado por los chunks auditados. | Revisar si falta auditar otro JSONL o si hubo pérdida de placeholder. |
