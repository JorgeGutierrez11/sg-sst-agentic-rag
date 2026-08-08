# Plan de implementación: fragmentación de tablas vectoriales

Este plan corrige un problema crítico del RAG base: algunas tablas se están indexando como documentos gigantes, lo que degrada la recuperación y puede hacer que el prompt enviado al LLM exceda el límite del proveedor.

## Problema confirmado

Actualmente `pipeline/tables/table_documents.py` convierte cada tabla derivada en un único documento vector-ready:

```txt
data/processed/tables_markdown/<source_stem>/table_<n>.md
  → 1 documento en data/processed/table_documents.jsonl
```

Esto falla cuando una tabla es muy grande. Se detectó un caso de más de un millón de caracteres:

```txt
table-decreto-768-de-2022-0
≈ 1.186.470 caracteres
```

Consecuencias:

- Chroma puede recuperar un documento demasiado grande;
- el prompt enviado a Groq puede exceder el límite de mensajes;
- truncar el contexto no es solución suficiente porque puede cortar justo la fila relevante;
- el embedding de una tabla gigante pierde granularidad semántica;
- preguntas legítimas sobre tablas pueden fallar.

## Decisión técnica

Las tablas grandes deben dividirse antes de indexarse. La salida seguirá siendo el mismo artefacto JSONL:

```txt
data/processed/table_documents.jsonl
```

JSONL significa un documento JSON por línea. Después del cambio:

```txt
1 tabla pequeña → 1 línea JSONL
1 tabla grande  → N líneas JSONL
```

En vez de:

```txt
1 tabla → 1 documento vectorial gigante
```

usar:

```txt
1 tabla → N documentos vectoriales pequeños
```

Cada fragmento debe conservar metadata lógica suficiente para reconstruir la relación con la tabla original.

## Estructura real observada

Se analizaron las 10 tablas actuales en:

```txt
data/processed/tables_markdown/
data/interim/tables/
```

Hallazgo clave: el Markdown derivado no tiene un formato uniforme. Algunas tablas salen como grid tables con `+---+`, otras como simple tables con líneas `-----`, y varias no tienen filas pipe `|---|` detectables.

En cambio, los HTML extraídos conservan estructura consistente con `<tr>`, `<td>` y `<th>` en las 10 tablas.

| Tabla | Tamaño Markdown | Filas HTML aprox. | Estrategia |
|---|---:|---:|---|
| Decreto 1072 `table_0` | 6.106 chars | 6 filas | Dividir solo si supera límite. |
| Decreto 768 `table_0` | 1.186.470 chars | 1.109 filas | Fragmentar obligatorio por filas. |
| Res. 0312 `table_0` | 5.303 chars | 8 filas | No dividir inicialmente. |
| Res. 0312 `table_1` | 22.032 chars | 22 filas | Fragmentar por filas. |
| Res. 0312 `table_2` | 73.982 chars | 61 filas | Fragmentar por filas. |
| Res. 0312 `table_3` | 7.848 chars | 6 filas | Dividir solo si supera límite. |
| Res. 0312 `table_4` | 50.303 chars | 71 filas | Fragmentar por filas, preservando filas de contexto/título. |
| Res. 0312 `table_5` | 3.720 chars | 4 filas | No dividir inicialmente. |
| Res. 0312 `table_6` | 5.468 chars | 7 filas | No dividir inicialmente. |
| Res. 2013 `table_0` | 636 chars | 4 filas | No dividir. |

## Criterio de fragmentación

### Regla principal

Dividir tablas por filas HTML, no por caracteres ciegos ni por parsing del Markdown derivado.

Fuente estructural preferida:

```txt
data/interim/tables/<source_stem>/table_<n>.html
```

El HTML se usa para detectar filas y celdas. El texto final de cada fragmento se emite como Markdown simple indexable.

Cada fragmento debe:

- conservar el encabezado o filas de contexto de la tabla;
- incluir un grupo de filas de datos;
- mantenerse por debajo de un límite configurable de caracteres.

### Límite inicial recomendado

```txt
MAX_TABLE_DOCUMENT_CHARS = 6000
```

Este límite no es un límite final del prompt; es el tamaño máximo aproximado de cada documento de tabla indexable.

Si una fila individual supera el límite, debe emitirse sola con encabezado y una marca metadata controlada.

## Metadata esperada

Cada fragmento debe mantener la identidad de la tabla original:

```json
{
  "type": "table",
  "source_stem": "Decreto 768 de 2022",
  "table_index": 0,
  "table_part_index": 0,
  "table_part_count": 12,
  "table_key": "Decreto 768 de 2022:0",
  "linked_placeholder": "<!-- TABLE_0 -->",
  "oversized_row": false
}
```

Reglas:

- `table_index` identifica la tabla dentro del documento fuente;
- `table_part_index` identifica el fragmento;
- `table_part_count` permite saber cuántos fragmentos existen;
- `table_key` conserva la relación lógica con chunks que referencian la tabla;
- no guardar rutas físicas en metadata;
- no guardar HTML crudo;
- `oversized_row` solo se marca cuando una fila individual supera el límite y debe emitirse sola.

## Identificadores

Para tablas no fragmentadas se puede conservar el patrón actual si solo hay una parte:

```txt
table-<source_slug>-<table_index>
```

Para tablas fragmentadas:

```txt
table-<source_slug>-<table_index>-part-0000
table-<source_slug>-<table_index>-part-0001
```

La decisión preferida es usar siempre sufijo `part` para uniformidad:

```txt
table-<source_slug>-<table_index>-part-0000
```

Esto evita tener dos formas distintas de ID.

## Fase 1 — Parser simple de tabla HTML

Archivo:

```txt
pipeline/tables/table_documents.py
```

Agregar helpers pequeños usando `html.parser` de la biblioteca estándar:

```python
table_rows_from_html(html: str) -> list[list[str]]
```

Responsabilidad:

- extraer filas `<tr>`;
- extraer celdas `<th>` y `<td>`;
- limpiar espacios internos;
- preservar el orden original;
- no depender de BeautifulSoup ni de librerías nuevas.

No crear parser HTML complejo. Usar solo lo necesario para estas tablas.

## Fase 2 — Fragmentación por filas

Agregar función:

```python
table_document_parts(rows: list[list[str]], max_chars: int = MAX_TABLE_DOCUMENT_CHARS) -> list[str]
```

Reglas:

- repetir encabezado/contexto + separador en cada parte;
- acumular filas hasta acercarse al límite;
- nunca emitir partes vacías;
- si una fila supera el límite, emitirla sola con encabezado;
- conservar orden original.

### Detección de encabezado/contexto

Reglas iniciales:

- si la primera fila HTML contiene `<th>`, usarla como encabezado;
- si no hay `<th>`, usar la primera fila no vacía como contexto/encabezado;
- para tablas con títulos previos, como Res. 0312 `table_4`, conservar filas iniciales cortas como contexto hasta encontrar la fila con mayor número de columnas;
- mantener KISS: si la heurística no identifica algo especial, usar primera fila como encabezado y el resto como datos.

## Fase 3 — Generación de documentos vector-ready fragmentados

Modificar o reemplazar:

```python
table_document_from_markdown_path(...)
```

por una función que devuelva varios documentos por tabla:

```python
table_documents_from_table_path(...) -> list[JsonDict]
```

Cada parte debe incluir:

- `id` estable;
- `text` de la parte;
- metadata lógica plana.

`build_table_documents(...)` debe aplanar los documentos generados por cada archivo Markdown.

La función puede recibir `markdown_root` para mantener compatibilidad del comando actual, pero debe resolver el HTML estructural correspondiente desde `data/interim/tables/` o desde una constante/configuración equivalente.

## Fase 4 — CLI y configuración

Mantener el comando existente:

```bash
python -m pipeline.chunking.main build-table-documents
```

Mantener el mismo comando en CLI existente. La partición de tablas debe ser automática; por eso existe el límite en caracteres.

No cambiar la salida:

```txt
data/processed/table_documents.jsonl
```

No crear un nuevo formato JSON. El resultado sigue siendo JSONL.

## Fase 5 — Pruebas

Agregar pruebas en:

```txt
pipeline/tests/test_table_documents.py
```

Casos mínimos:

- tabla pequeña produce una sola parte;
- tabla grande produce múltiples partes;
- cada parte conserva header y separador;
- IDs incluyen `part-0000`, `part-0001`, etc.;
- metadata incluye `table_part_index`, `table_part_count` y `table_key`;
- metadata incluye `oversized_row` cuando aplique;
- ninguna parte supera el límite salvo fila individual demasiado grande;
- parser HTML conserva filas y celdas en orden;
- fallback controlado si el HTML no contiene filas válidas.

## Fuera de alcance

- No implementar reranking.
- No implementar validación de relevancia.
- No implementar guardrails de prompt injection.
- No cambiar el modelo de embeddings.
- No reemplazar ChromaDB.
- No crear parser HTML complejo ni agregar dependencias nuevas; usar `html.parser` estándar si se necesita extraer filas.

## Resultado esperado

El RAG debe poder recuperar información de tablas grandes sin enviar documentos gigantes al LLM. La recuperación será más granular, el prompt será más estable y las preguntas legítimas sobre tablas no deberían fallar por exceso de longitud.

## Checklist de aceptación

- [ ] `table_documents.py` genera múltiples documentos para tablas grandes.
- [ ] La salida sigue siendo `data/processed/table_documents.jsonl`.
- [ ] Cada fragmento conserva encabezado y trazabilidad.
- [ ] La metadata no guarda rutas físicas.
- [ ] `table_key` sigue relacionando chunks y tablas.
- [ ] No hay documentos de tabla gigantes en `table_documents.jsonl`.
- [ ] La vectorización con Chroma se completa con `--batch-size 32`.
- [ ] El RAG no falla por longitud al recuperar una tabla grande.
