# Guía operativa: procesamiento de tablas

Esta guía sirve para regenerar, auditar y previsualizar los artefactos de tablas del corpus SG-SST.

## Ruta rápida

```bash
python -m pipeline.chunking.main audit-table-references
python -m pipeline.chunking.main build-table-markdown
python -m pipeline.chunking.main build-table-documents
python -m pipeline.tables.table_jsonl_to_html
```

La vista previa HTML es opcional. En reconstrucciones desde cero, o después de cambios en la extracción de tablas, ejecuta siempre `build-table-markdown` antes de `build-table-documents`.

## Prerrequisitos

| Requisito | Cuándo aplica | Verificación práctica |
|---|---|---|
| Tablas HTML extraídas | Para todos los comandos de tablas. | Deben existir archivos `data/interim/tables/<source_stem>/table_<n>.html`. |
| Chunks con referencias | Para `audit-table-references`. | Deben existir `data/processed/chunks/parents.jsonl` y `data/processed/chunks/regex_constrained_semantic/chunks.jsonl`. |
| Markdown derivado de tablas | Para `build-table-documents` y preview completa. | Debe existir `data/processed/tables_markdown/` o generarse primero con `build-table-markdown`. |
| Dependencias Python y Pandoc | Para conversión de tablas. | Instala `requirements.txt` y confirma que Pandoc esté disponible en `PATH`. |

## Secuencia operativa

### 1. Auditar referencias de tablas

```bash
python -m pipeline.chunking.main audit-table-references
```

| Entrada | Salida |
|---|---|
| `data/processed/chunks/parents.jsonl` | Reporte en consola sobre referencias válidas, faltantes o huérfanas. |
| `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` |  |
| `data/interim/tables/` |  |

Ejecuta este paso después de reconstruir chunks o cambiar la extracción DOCX. Un error por tabla referenciada inexistente bloquea la indexación confiable.

### 2. Regenerar Markdown derivado de tablas

```bash
python -m pipeline.chunking.main build-table-markdown
```

| Entrada | Salida |
|---|---|
| `data/interim/tables/<source_stem>/table_<n>.html` | `data/processed/tables_markdown/<source_stem>/table_<n>.md` |

Este paso convierte las tablas HTML extraídas a Markdown derivado. Es obligatorio antes de `build-table-documents` cuando reconstruyes desde cero o cuando cambian los HTML extraídos.

### 3. Crear documentos vectorizables de tablas

```bash
python -m pipeline.chunking.main build-table-documents
```

| Entrada | Salida |
|---|---|
| `data/processed/tables_markdown/<source_stem>/table_<n>.md` | `data/processed/table_documents.jsonl` |
| `data/interim/tables/<source_stem>/table_<n>.html` |  |

El comando descubre primero el inventario en `tables_markdown` y usa el HTML equivalente como fuente estructural preferida cuando existe. La salida `table_documents.jsonl` es la entrada de tablas para vectorización.

### 4. Generar vista previa HTML opcional

```bash
python -m pipeline.tables.table_jsonl_to_html
```

| Entrada | Salida |
|---|---|
| `data/processed/table_documents.jsonl` | `data/processed/tables_htlm/index.html` y un HTML por registro de tabla. |

> Nota: `tables_htlm` conserva el nombre real implementado actualmente.

Usa esta salida para revisión humana rápida. No es necesaria para indexar en Chroma.

## Órdenes recomendados

| Situación | Orden mínimo |
|---|---|
| Reconstrucción desde cero después de ingesta y chunking | `audit-table-references` → `build-table-markdown` → `build-table-documents` |
| Cambió la extracción de tablas HTML | `audit-table-references` → `build-table-markdown` → `build-table-documents` |
| Solo quieres revisar visualmente documentos ya generados | `python -m pipeline.tables.table_jsonl_to_html` |
| Vas a vectorizar | Confirma que existe `data/processed/table_documents.jsonl`; si no existe, ejecuta `build-table-markdown` y luego `build-table-documents`. |

