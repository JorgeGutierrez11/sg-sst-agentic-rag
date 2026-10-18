# Plan de la Fase 5 — Validación de artefactos locales

> **Status:** `Current`
> **Audience:** maintainer
> **Verified against:** `agents/consulta_normativa/langchain_rag/main.py`, `retrieval/chroma_retrieval.py`, `retrieval/bm25_retrieval.py`, `retrieval/table_complement.py`, `retrieval/parent_document_retrieval.py`, `pipeline/chunking/io_jsonl.py`, `agents/api/main.py`, `agents/diagnostico_cumplimiento/api/service.py`, `agents/diagnostico_cumplimiento/catalog/loader.py`, `chromadb==1.5.9`
> **Last verified:** 2026-10-18
> **Replacement:** N/A

Este plan completa la Fase 5 de [`plan-docker.md`](plan-docker.md). El objetivo es que la API **no quede disponible** si un índice, un documento o un catálogo falta, está vacío, es ilegible o es incoherente, y que el log nombre el artefacto y la ruta exactos. Se divide en cinco partes independientes; cada una se aprueba, implementa y verifica por separado.

## Resumen

| Parte | Resuelve | Resultado observable |
|---|---|---|
| 1. Comprobación previa de artefactos | Directorio Chroma vacío, tablas ausentes sin aviso, ruta relativa, errores opacos | La API no arranca y el log dice qué falta y dónde |
| 2. Catálogos de diagnóstico al arrancar | Catálogo dañado detectado solo en la primera petición | Un catálogo inválido impide la readiness |
| 3. Coherencia entre índices | Chroma, BM25 y padres solo coinciden por casualidad | Un desajuste impide el arranque |
| 4. Copia de trabajo de Chroma | Chroma escribe al abrir y falla en solo lectura | El índice publicado nunca se modifica |
| 5. Política de modelos y documentación | Caché y versión de modelos sin definir | Arranque reproducible y sin red |

Orden recomendado: 1 → 4 → 3 → 2 → 5. La parte 4 va antes que la 3 porque la 3 consulta Chroma y debe hacerlo sobre la copia de trabajo.

## Estado verificado (2026-10-18)

Comprobación del diagnóstico de una sesión anterior frente al código actual. Las pruebas en vivo se hicieron sobre copias de los índices en un directorio temporal, nunca sobre `data/processed/`.

| # | Afirmación previa | Veredicto | Evidencia |
|---|---|---|---|
| A | Chroma y BM25 tienen los mismos 400 IDs (313 chunks + 87 tablas) y los 313 hijos encuentran a su padre | **Confirmado** | Conteo directo: Chroma 400, BM25 400, conjuntos iguales; `ParentChildConsistencyReport(313, 313, 0)` con 99 padres |
| B | El runtime no crea ni actualiza índices | **Confirmado** | Sin `get_or_create`, `upsert` ni `add` de colecciones en `agents/` |
| C | Si falta Chroma, BM25 o `parents.jsonl`, la API no arranca | **Confirmado** | `chroma_retrieval.py:19`, `bm25_retrieval.py:15`, `parent_document_retrieval.py:37` |
| D | Qwen y ALIA cargan sin conexión desde la caché | **Confirmado** | Carga correcta con `HF_HUB_OFFLINE=1` |
| 1 | Un directorio Chroma vacío hace que Chroma cree `chroma.sqlite3` | **Confirmado** | Prueba en vivo: queda `chroma.sqlite3` y luego falla con `NotFoundError` |
| 2 | Sin `table_documents.jsonl` la API arranca sin tablas y sin aviso | **Confirmado** | `io_jsonl.py:30` devuelve `[]` si el archivo no existe |
| 3 | `table_complement.py:13` usa una ruta relativa al directorio actual | **Confirmado** | `Path("data/processed/table_documents.jsonl")`; ya existe la versión absoluta en `pipeline/chunking/config.py:13` |
| 4 | Los errores llegan como traza de Uvicorn y `main.py:245` pierde la traza original | **Parcial** | `main.py:244` sí usa `raise ... from error`, así que la traza original **se conserva**. Lo cierto: el mensaje solo lleva `str(error)` sin el tipo, y el `lifespan` (`agents/api/main.py:29`) no registra ningún log |
| 5 | Los catálogos solo se validan con la primera petición y acaban en un 503 genérico | **Confirmado** | `service.py:98` carga el catálogo en cada petición; `CatalogLoadError` hereda de `Exception` y cae en el `except Exception` → 503 de `routes.py:120`. Corrección menor: los catálogos pesan entre 10 y 134 KB (unos 240 KB en total), no 30 KB cada uno |
| 6 | Nadie comprueba la coherencia entre índices | **Confirmado** | `parent_child_consistency_report` solo se usa en `tests/test_parent_document_retrieval.py` |
| 7 | Abrir Chroma reescribe `chroma.sqlite3` | **Confirmado y más grave** | También reescribe `data_level0.bin` y `length.bin` (hashes distintos tras solo abrir y contar) |
| 7b | La protección real es montar el índice en solo lectura en Docker | **Negado** | Con permisos de solo lectura Chroma falla: `InternalError: attempt to write a readonly database`. BM25 sí funciona en solo lectura |
| 8 | Qwen se carga dos veces (unos 1,2 GB extra) | **Negado** | `SentenceTransformerEmbeddingFunction` de `chromadb` guarda los modelos en una caché de clase indexada por `model_name`; las dos instancias comparten el mismo objeto (`a._model is b._model` → `True`). Queda un acoplamiento frágil: `QwenMemoryEmbeddings` lee el atributo privado `_model` |
| 9 | `AGENTS.md` nombra el reranker `bge-reranker-v2-m3` | **Ya corregido** | `AGENTS.md`, `README.md` y `docs/` (salvo `historical/`) ya nombran `SINAI/ALIA-MrBERT-es-legal-administrative-reranker` |

Hallazgos nuevos:

- **La versión de los modelos no está fijada.** `qwen_embedding_function()` solo pasa `model_name`. Una imagen nueva que descargue Qwen del Hub puede recibir pesos distintos de los que generaron el índice Chroma, y las búsquedas densas se degradarían sin ningún error.
- **El pipeline puede leer tablas vacías sin aviso.** `read_jsonl` lo comparte el pipeline offline; su comportamiento de devolver `[]` no se cambia en este plan (ver Parte 1).

## Decisiones

| Tema | Decisión | Motivo |
|---|---|---|
| Fallo de arranque | **Fallar rápido**: registrar el error y dejar que el proceso termine | Un artefacto ausente no se arregla reiniciando. Un 503 permanente con `/health` en verde oculta el problema a la plataforma |
| Índice Chroma en producción | **Copia de trabajo** al arrancar, desde un índice publicado de solo lectura | Chroma no funciona en solo lectura (7b) y escribe al abrir (7). Copiar 9,5 MB cuesta menos de un segundo |
| Coherencia | Usar el corpus de BM25 (ya trae `parent_id`) en lugar de leer `chunks.jsonl` | No añade un artefacto nuevo al runtime ni a la imagen |
| `read_jsonl` | No modificarlo; validar existencia en el llamador del runtime | Es código compartido con el pipeline; cambiarlo alteraría comandos existentes |
| Qwen duplicado | No es un problema; solo se propone una limpieza opcional | La evidencia muestra una sola instancia |

## Parte 1 — Comprobación previa de artefactos

**Estado:** implementada el 2026-10-18 en el commit `68843d7`. Suites en verde: pipeline 124, consulta 176, API 14, diagnóstico 197.

**Resuelve:** 1, 2, 3 y 4.

**Cambios:**

1. Añadir en el runtime de consulta una función de comprobación previa que se ejecute **antes** de abrir Chroma o cargar modelos. Debe exigir:
   - `data/processed/chroma/chroma.sqlite3` existe y no está vacío.
   - `data/processed/bm25/` contiene los archivos que `bm25s` carga: `params.index.json`, `vocab.index.json`, `data.csc.index.npy`, `indices.csc.index.npy`, `indptr.csc.index.npy`, `corpus.jsonl`.
   - `data/processed/chunks/parents.jsonl` existe y no está vacío.
   - `data/processed/table_documents.jsonl` existe, pero es posible que este basio, depende del corpus.
2. Si algo falla, lanzar un único `OperationalError` cuyo mensaje nombre el artefacto y la ruta absoluta, por ejemplo `Missing runtime artifact: table documents (/app/data/processed/table_documents.jsonl)`.
3. En `build_runtime`, incluir el tipo de la excepción original en el mensaje (`f"{type(error).__name__}: {error}"`) y conservar `from error`.
4. En el `lifespan` de `agents/api/main.py`, añadir `except Exception` que registre `logger.exception("Runtime initialization failed: ...")` y vuelva a lanzar el error. El log no debe incluir valores de variables de entorno.

**Pruebas** (`agents/consulta_normativa/tests/test_langchain_rag_main.py`, `test_table_complement.py`, `agents/api/tests/test_main.py`):

- [x] Falta cada artefacto → `OperationalError` que nombra artefacto y ruta.
- [x] Un directorio Chroma vacío no crea ningún archivo.
- [x] Un fallo de inicialización queda registrado en el log y `/health/ready` nunca devuelve 200.
- [x] Regresión: con todos los artefactos presentes, el arranque se comporta igual que antes.

**Riesgo:** item 3 (cambia el comportamiento del arranque: la ausencia de tablas, antes silenciosa, pasa a impedirlo; es el cambio pedido por la Fase 5).

## Parte 2 — Catálogos de diagnóstico al arrancar

**Resuelve:** 5.

**Cambios:**

1. Al construir `DiagnosticService`, cargar y validar con `load_catalog` los cuatro catálogos `res0312_riesgo_i_*.json` de `catalog/data/`. Se excluyen `catalog_schema_reference_v2_1.json` y la carpeta `Respaldo/`.
2. Un `CatalogLoadError` impide el arranque, con el mismo patrón de log de la Parte 1.
3. Guardar los catálogos validados en memoria y servirlos desde ahí en `create_diagnostic`, en lugar de leer el JSON en cada petición.

**Pruebas** (`agents/diagnostico_cumplimiento/tests/test_api.py`, con `pytest`):

- [ ] Un catálogo con JSON inválido o fuera del schema impide construir el servicio.
- [ ] Regresión: crear un diagnóstico devuelve el mismo `catalog_id` y la misma primera pregunta para cada tramo de trabajadores.

**Riesgo:** item 3. Editar un catálogo con la API en marcha ya no tiene efecto hasta reiniciarla. Hay que documentarlo.

## Parte 3 — Coherencia entre índices

**Resuelve:** 6. Depende de la Parte 4.

**Cambios:**

1. Después de abrir Chroma y BM25, y antes de construir el grafo, comprobar:
   - `collection.count()` es igual a `len(bm25_index.corpus)`.
   - El conjunto de IDs de Chroma (`collection.get(include=[])["ids"]`) es igual al de BM25.
   - Todos los documentos del corpus BM25 con `parent_id` encuentran a su padre, reutilizando `parent_child_consistency_report`.
2. Cualquier desajuste lanza un `OperationalError` con los conteos y como máximo 5 IDs de ejemplo.
3. No se crea un manifiesto nuevo ni se cambia el pipeline.

**Pruebas:**

- [ ] Conteos distintos → error.
- [ ] Mismos conteos con IDs distintos → error.
- [ ] Hijo sin padre → error.
- [ ] Índices coherentes → arranque normal.

**Riesgo:** none (validación de solo lectura cubierta por las pruebas).

## Parte 4 — Copia de trabajo de Chroma

**Estado:** implementada el 2026-10-18, sin commit. Suites en verde: pipeline 124, consulta 184, API 14, diagnóstico 197. Prueba real con Uvicorn: `/health/ready` 200, índice publicado sin cambios y copia borrada al cerrar.

**Detalle verificado durante la implementación:** `shutil.copytree` copia también los permisos, así que una copia de un origen de solo lectura falla igual que el original. La copia usa `copyfile` y restaura el permiso de escritura del propietario.

**Variable:** `RAG_CHROMA_WORKING_DIR` es el directorio padre; cada arranque crea dentro una subcarpeta `sg-sst-chroma-*` nueva, así que nunca se borra contenido que ya existiera ahí.

**Resuelve:** 7 y 7b.

**Cambios:**

1. Nueva variable opcional `RAG_CHROMA_WORKING_DIR`. Al arrancar, el runtime copia `data/processed/chroma/` a ese directorio y abre la copia. Si la variable no está definida, usa un directorio temporal creado con `tempfile.mkdtemp()`, que se borra al cerrar.
2. El índice publicado se abre únicamente para copiarlo; nunca con `PersistentClient`.
3. Efecto en local: `data/processed/chroma/` deja de aparecer modificado en `git status` después de ejecutar la API o la CLI.
4. Corregir en `plan-docker.md`, Fase 6, el requisito "Montar los índices RAG como volúmenes de solo lectura": el índice publicado puede ir en solo lectura, pero Chroma necesita la copia de trabajo en un volumen o `tmpfs` con escritura.

**Pruebas** (`test_chroma_retrieval.py`):

- [x] Abrir y consultar no cambia ningún hash del índice de origen.
- [x] Funciona con un índice de origen sin permisos de escritura.
- [x] Origen vacío o ausente → mismo error que en la Parte 1.

**Riesgo:** none. Solo se añade una variable opcional, sin cambiar archivos de despliegue. El `rmtree` de limpieza solo acepta directorios `sg-sst-chroma-*` creados por el propio runtime, y los tests lo cubren.

**Fuera de alcance:** decidir si `data/processed/chroma/` debe seguir versionado en git. Esto corresponde a la Fase 7 (publicación de índices). Los cambios actuales en esos archivos son el efecto del problema 7; restaurarlos es decisión tuya.

## Parte 5 — Política de modelos y documentación

**Resuelve:** la actividad 4 de la Fase 5 y el hallazgo de versión sin fijar.

**Cambios:**

1. Fijar la revisión (hash de commit en Hugging Face) de Qwen y ALIA en `config.py` y pasarla a `SentenceTransformer` y `CrossEncoder` con `revision=`. La revisión de Qwen debe ser la que generó el índice actual, que es la que está hoy en la caché local.
2. Documentar la política:
   - Los modelos se descargan a `HF_HOME` (por defecto `~/.cache/huggingface`).
   - En producción se descargan durante la construcción o en un paso previo, y el runtime arranca con `HF_HUB_OFFLINE=1`.
   - Si falta un modelo en modo sin conexión, el arranque falla con el mismo patrón de log.
3. Limpieza opcional: pasar la función de embeddings de Chroma a `QwenMemoryEmbeddings` en lugar de crear otra instancia y leer `_model`, para no depender de la caché interna de `chromadb`.
4. Actualizar documentación:
   - [`getting-started.md`](../getting-started.md): artefactos obligatorios, mensajes de error, `RAG_CHROMA_WORKING_DIR`, `HF_HOME` y `HF_HUB_OFFLINE`.
   - [`operations/rag-langgraph.md`](../operations/rag-langgraph.md): comprobaciones de arranque.
   - [`plan-docker.md`](plan-docker.md): Fase 5 marcada como completada y `.env.example` de la Fase 3 con `CORS_ALLOWED_ORIGINS` en vez de `IP_ADDRESS`.

**Pruebas:**

- [ ] Las funciones de embeddings y de reranking reciben la revisión configurada.
- [ ] Arranque con `HF_HUB_OFFLINE=1` y la caché presente → correcto.

**Riesgo:** item 5 (fija versiones de dependencias de modelo).

## Revisiones de gentle-ai

Límite de revisión vigente: `e414c19`. Los commits anteriores a ese punto no se revisan. Cada commit nuevo de esta fase se evalúa contra el último límite revisado:

```bash
gentle-ai review assess --cwd . --agent claude-code --base-ref <último límite> --committed-only --json
```

Solo se revisa cuando `review_due` es `true` (`high_risk`) o cuando se pide de forma explícita. El límite avanza cuando la evaluación sale `passive` o cuando una revisión queda aprobada; un resultado `under_budget` sigue acumulándose hasta que se revise.

| Commits evaluados | Parte | Evaluación | Resultado |
|---|---|---|---|
| `cc60500` (documentación) + `68843d7` (Parte 1) | 1 | `medium` | `under_budget`: sin revisión, queda acumulado |

## Verificación de cada parte

Cada parte termina con estas suites en verde:

```bash
python -m unittest discover -s pipeline/tests
python -m unittest discover -s agents/consulta_normativa/tests
python -m unittest discover -s agents/api/tests
pytest agents/diagnostico_cumplimiento/tests
python -m compileall pipeline agents
```

Además, al cerrar la fase:

- [ ] `uvicorn agents.api.main:app` con todos los artefactos → `/health/ready` devuelve 200.
- [ ] Al renombrar un artefacto obligatorio → el proceso termina y el log nombra artefacto y ruta.
- [ ] `git status` no muestra cambios en `data/processed/chroma/` después de arrancar la API.

No se hace ningún commit sin aprobación explícita.

## Siguiente paso

Aprobar la Parte 1. Al terminar la Parte 4, la Fase 6 de [`plan-docker.md`](plan-docker.md) ya puede definir los volúmenes con la regla correcta para Chroma.
