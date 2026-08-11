# Guía operativa: reconstrucción del corpus SG-SST

Esta guía reconstruye los artefactos del corpus desde DOCX normativos hasta documentos de tabla listos para vectorización. Ejecútala desde la raíz del repositorio y no edites manualmente las salidas bajo `data/interim/` o `data/processed/`. Para regenerar, auditar o previsualizar tablas de forma aislada, consulta [`table-processing.md`](table-processing.md); las decisiones completas están en [`tables.md`](../architecture/tables.md).

## Ruta rápida

```bash
python pipeline/ingestion/docx_to_markdown.py
python pipeline/cleaning/markdown_cleaner.py

python -m pipeline.chunking.main build-parents
python -m pipeline.chunking.main build-sliding-window
python -m pipeline.chunking.main build-regex-constrained-semantic
python -m pipeline.tables.main audit-table-references
python -m pipeline.tables.main build-table-markdown
python -m pipeline.tables.main build-table-documents
```


## Prerrequisitos

| Requisito | Verificación práctica |
|---|---|
| DOCX fuente | Deben existir archivos `*.docx` en `data/raw/`. Esta carpeta puede ser local/regenerable y no necesariamente está versionada. |
| Dependencias Python | Instala `requirements.txt` en el entorno activo. |
| Pandoc | Debe estar instalado como binario del sistema y disponible en `PATH`. |
| `pypandoc` | Está declarado en `requirements.txt`, pero no reemplaza la instalación del binario Pandoc. |
| Ejecución desde raíz | Los comandos asumen rutas relativas del proyecto. |

## Secuencia operativa

### 1. Convertir DOCX a Markdown intermedio

```bash
python pipeline/ingestion/docx_to_markdown.py
```

Entradas y salidas:

| Entrada | Salidas |
|---|---|
| `data/raw/*.docx` | `data/interim/*.md` y `data/interim/tables/<source_stem>/table_<n>.html` |

La ingesta usa Pandoc mediante `pypandoc`. Cuando detecta tablas HTML, las separa y deja placeholders `<!-- TABLE_n -->`; ver decisiones en [`tables.md`](../architecture/tables.md).

### 2. Limpiar Markdown

```bash
python pipeline/cleaning/markdown_cleaner.py
```

Entrada y salida:

| Entrada | Salida |
|---|---|
| `data/interim/*.md` | `data/processed/*.md` |

La limpieza normaliza artefactos de Pandoc, listas escapadas, saltos duros, imágenes y espaciado. Si una salida queda mal, corrige el limpiador y regenera; no modifiques el Markdown procesado a mano.

### 3. Construir parent chunks

```bash
python -m pipeline.chunking.main build-parents
```

Salida principal: `data/processed/chunks/parents.jsonl`.

Los parent chunks respetan estructura normativa, offsets sobre Markdown limpio y referencias lógicas mínimas a tablas.

### 4. Construir baseline sliding window

```bash
python -m pipeline.chunking.main build-sliding-window
```

Salida principal: `data/processed/chunks/sliding_window/chunks.jsonl`.

Este baseline sirve para comparación. No es la salida recomendada para indexación principal.

### 5. Construir child chunks recomendados

```bash
python -m pipeline.chunking.main build-regex-constrained-semantic
```

Salida principal: `data/processed/chunks/regex_constrained_semantic/chunks.jsonl`.

Esta es la estrategia recomendada para SG-SST porque conserva spans exactos y trazabilidad legal. No sustituyas este paso por `semantic_chunking` puro en el flujo principal.

### 6. Auditar referencias de tablas

```bash
python -m pipeline.tables.main audit-table-references
```

La auditoría compara `parents.jsonl` y `regex_constrained_semantic/chunks.jsonl` contra `data/interim/tables/`.

| Resultado | Acción |
|---|---|
| Tabla referenciada inexistente | Error bloqueante; revisar extracción DOCX, placeholders y numeración `TABLE_n`. |
| Tabla HTML huérfana | Warning; revisar si la tabla pertenece a un JSONL no auditado o si se perdió el placeholder. |

### 7. Convertir tablas HTML a Markdown derivado

```bash
python -m pipeline.tables.main build-table-markdown
```

Salida principal: `data/processed/tables_markdown/<source_stem>/table_<n>.md`.

Este paso también depende de Pandoc/pypandoc y debe ejecutarse antes de `build-table-documents` en reconstrucciones desde cero o tras cambios de extracción de tablas.

### 8. Crear documentos vector-ready de tablas

```bash
python -m pipeline.tables.main build-table-documents
```

Salida principal: `data/processed/table_documents.jsonl`.

Los documentos de tabla conservan metadata lógica (`source_stem`, `table_index`, `table_key`) y no guardan rutas físicas; ver metadata completa en [`tables.md`](../architecture/tables.md).

## Artefactos esperados

| Artefacto | Debe existir después de |
|---|---|
| `data/interim/*.md` | Ingesta DOCX |
| `data/interim/tables/<source_stem>/table_<n>.html` | Ingesta DOCX, si la norma contiene tablas |
| `data/processed/*.md` | Limpieza Markdown |
| `data/processed/chunks/parents.jsonl` | `build-parents` |
| `data/processed/chunks/sliding_window/chunks.jsonl` | `build-sliding-window` |
| `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` | `build-regex-constrained-semantic` |
| `data/processed/tables_markdown/` | `build-table-markdown` |
| `data/processed/table_documents.jsonl` | `build-table-documents` |

## Troubleshooting

| Síntoma | Causa probable | Acción |
|---|---|---|
| `No se encontraron .docx en: data/raw` | Faltan fuentes locales. | Copiar los DOCX oficiales a `data/raw/`. |
| Fallo de Pandoc durante DOCX o tablas | Pandoc no está instalado o no está en `PATH`. | Instalar Pandoc y verificar que `pypandoc` pueda invocarlo. |
| `No se encontraron .md en: data/interim` | No se ejecutó la ingesta o falló toda la conversión. | Revisar logs de `docx_to_markdown.py` y repetir desde el paso 1. |
| `No module named ...` | Dependencia Python ausente. | Instalar `requirements.txt` en el entorno activo. |
| `Missing referenced table files` | Un chunk cita una tabla HTML inexistente. | Revisar `data/interim/tables/<source_stem>/` y la numeración de placeholders. |
| Advertencias de tablas huérfanas | Existen HTML extraídos no referenciados por los JSONL auditados. | Revisar si es una pérdida real de placeholder o un artefacto fuera del alcance auditado. |
| Error por flags en chunking | La CLI actual no acepta flags operacionales. | Ejecutar únicamente los subcomandos documentados y cambiar rutas desde código/configuración si es deliberado. |

## Verificación mínima

```bash
python -m pipeline.chunking.main --help
python -m pipeline.chunking.main build-parents --help
python -m pipeline.chunking.main build-regex-constrained-semantic --help
python -m pipeline.tables.main audit-table-references --help
python -m pipeline.tables.main build-table-markdown --help
python -m pipeline.tables.main build-table-documents --help
```
