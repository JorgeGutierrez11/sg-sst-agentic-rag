# Guía de ejecución del backend

> **Status:** `Current`
> **Audience:** operator
> **Verified against:** `agents/api/main.py`, `agents/api/config.py`, `agents/consulta_normativa/langchain_rag/config.py`, `requirements.txt`
> **Last verified:** 2026-10-18
> **Replacement:** N/A (antes `GUIA_EJECUCION_BACKEND.md` en la raíz)

Esta guía explica cómo preparar y ejecutar localmente la API unificada de los agentes de consulta normativa y diagnóstico de cumplimiento del SG-SST.

## 1. Requisitos previos

- Git.
- Python 3.14.
- `pip`.
- Los artefactos locales de recuperación del agente de consulta.
- Conexión a Internet durante la descarga inicial de modelos.
- Un archivo `.env` local con las variables descritas en la sección 3.

Los principales artefactos requeridos son:

```text
data/processed/chroma/
data/processed/bm25/
data/processed/chunks/parents.jsonl
data/processed/table_documents.jsonl
```

Si faltan, constrúyalos con los runbooks de [`operations/`](operations/corpus-build.md).

Antes de abrir los índices o cargar modelos, el backend comprueba estos archivos: `chroma/chroma.sqlite3`, los seis archivos del índice `bm25/` (`params.index.json`, `vocab.index.json`, `data.csc.index.npy`, `indices.csc.index.npy`, `indptr.csc.index.npy`, `corpus.jsonl`), `parents.jsonl` y `table_documents.jsonl`. Todos deben existir y tener contenido, salvo `table_documents.jsonl`, que puede estar vacío si el corpus no tiene tablas. Si alguno falla, la API no arranca y el log nombra cada artefacto con su ruta absoluta (sección 8).

## 2. Preparar el entorno

Desde la raíz del repositorio:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

El entorno virtual solo debe crearse una vez. En ejecuciones posteriores basta con activarlo.

El backend usa FastAPI, Uvicorn, ChromaDB, Sentence Transformers, LangChain/LangGraph y ReportLab. Las dependencias de ejecución deben estar declaradas en `requirements.txt`; si una instalación limpia produce `ModuleNotFoundError`, se debe corregir ese manifiesto.

## 3. Configurar las variables de entorno

La configuración local vive en el archivo `.env` de la raíz del repositorio. Git lo ignora y **nunca debe subirse**. El backend lo carga automáticamente al iniciar (`load_project_environment` en `agents/consulta_normativa/langchain_rag/config.py`). Una variable exportada en la terminal tiene prioridad sobre el valor de `.env`.

| Variable | Obligatoria | Uso | Si falta o no es válida |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | Sí | Clave del LLM DeepSeek usado por la consulta normativa y el diagnóstico. | La consulta falla con `DEEPSEEK_API_KEY is not configured in the environment.` |
| `CORS_ALLOWED_ORIGINS` | Sí | Orígenes del navegador autorizados a llamar la API, separados por comas. Cada uno debe ser exactamente `http(s)://host[:puerto]`, sin ruta ni `/` final. Se rechaza `*` porque la API habilita credenciales CORS. | La API no arranca y muestra un `ValueError` que nombra `CORS_ALLOWED_ORIGINS`. |
| `HF_HOME` | No | Carpeta de la caché de Hugging Face donde se guardan los modelos Qwen (embeddings) y ALIA (reranking). Ambos se cargan con una revisión fija (hash de commit), así que todas las máquinas usan exactamente la misma versión. | Se usa `~/.cache/huggingface`. |
| `HF_HUB_OFFLINE` | No | Con `1`, el backend no se conecta a Hugging Face y carga los modelos solo desde `HF_HOME`. Es el modo recomendado una vez descargados los modelos, y el previsto para producción: allí se descargan durante la construcción de la imagen o en un paso previo. | Sin la variable, la primera ejecución descarga los modelos (necesita internet) y las siguientes usan la caché. Con `1` y sin los modelos en caché, la API no arranca (ver sección 8). |
| `RAG_CHROMA_WORKING_DIR` | No | Directorio padre donde el backend crea, al arrancar, una copia privada del índice ChromaDB. Chroma reescribe sus archivos incluso cuando solo consulta y falla si no puede escribir, así que el backend nunca abre `data/processed/chroma/` directamente. Cada arranque crea una subcarpeta `sg-sst-chroma-*` nueva y la borra al cerrar. Debe tener permisos de escritura y estar fuera de `data/processed/chroma/`. | Se usa el directorio temporal del sistema. Si apunta dentro del índice publicado, la API no arranca y el error nombra `RAG_CHROMA_WORKING_DIR`. |

Ejemplo de `.env`:

```bash
DEEPSEEK_API_KEY=TU_CLAVE
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

Varios orígenes: `CORS_ALLOWED_ORIGINS=http://localhost:3000,https://app.ejemplo.com`.

No imprima ni suba claves privadas al repositorio.

## 4. Levantar la API unificada

Active el entorno y ejecute un único proceso Uvicorn; las variables se toman de `.env`:

```bash
source .venv/bin/activate

uvicorn agents.api.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

La única URL base del backend es:

```text
http://127.0.0.1:8000
```

La inicialización puede tardar mientras carga ChromaDB, BM25, embeddings y el reranker. La primera ejecución también puede descargar modelos como `Qwen/Qwen3-Embedding-0.6B` y `SINAI/ALIA-MrBERT-es-legal-administrative-reranker`.

## 5. Comprobar salud y disponibilidad

La sonda de vida confirma únicamente que el proceso HTTP responde:

```bash
curl http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

`GET /health` no consulta servicios, índices ni proveedores externos. Por ello, una respuesta correcta no significa que los agentes ya estén disponibles.

La sonda de disponibilidad confirma que los servicios de consulta normativa y diagnóstico fueron inicializados correctamente:

```bash
curl http://127.0.0.1:8000/health/ready
```

Respuesta esperada después de completar la inicialización:

```json
{"status":"ready"}
```

Mientras la aplicación inicia o si falta alguno de los dos servicios, `GET /health/ready` responde `503` sin reconstruir runtimes, consultar ChromaDB o BM25, invocar servicios ni realizar solicitudes a DeepSeek. La disponibilidad **nunca debe depender de DeepSeek**: solo representa que ambos servicios locales fueron asignados durante el ciclo de vida de la aplicación.

En un despliegue futuro con contenedores, use `GET /health` como sonda de vida y `GET /health/ready` como sonda de disponibilidad. No existe `/health/live` ni un endpoint de salud separado bajo `/api/v1/diagnostics`.

## 6. Probar los agentes

Consulta normativa:

```bash
curl -X POST \
  http://127.0.0.1:8000/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"¿Qué es el SG-SST?"}'
```

Para continuar una conversación, reutilice el `conversation_id` retornado por la primera respuesta.

Diagnóstico de cumplimiento (la clase de riesgo es siempre I; solo se envía el número de trabajadores):

```bash
curl -X POST \
  http://127.0.0.1:8000/api/v1/diagnostics \
  -H 'Content-Type: application/json' \
  -d '{"worker_count":5}'
```

Los campos, códigos de error y el flujo completo (respuestas, cierre e informe PDF) están en la [referencia de la API](reference/api.md).


## 7. Limitación de sesiones de diagnóstico

Las sesiones de diagnóstico se guardan únicamente en la memoria del proceso:

- Ejecute Uvicorn con **un solo worker**.
- Reiniciar el backend elimina todos los diagnósticos en curso.
- `--reload` reinicia el proceso al detectar cambios y también elimina esas sesiones.
- Dos workers no comparten sesiones; una solicitud dirigida a otro worker no encontrará el diagnóstico.
- Las sesiones no son persistentes ni recuperables después de un reinicio.

No use `--workers` mientras el almacenamiento de diagnósticos siga siendo local al proceso.

## 8. Problemas frecuentes

### `DEEPSEEK_API_KEY is not configured`

Añada `DEEPSEEK_API_KEY` al archivo `.env` (sección 3) y reinicie Uvicorn.

### `CORS_ALLOWED_ORIGINS is not configured` o `contains an invalid origin`

Defina `CORS_ALLOWED_ORIGINS` en `.env` con orígenes `http(s)://host[:puerto]` separados por comas, sin ruta, sin `/` final y sin `*`.

### `Missing runtime artifact` o `Empty runtime artifact`

Uvicorn registra `API startup failed; the service will not report readiness.` seguido de un mensaje como:

```text
Missing runtime artifact: Chroma database (/ruta/al/repo/data/processed/chroma/chroma.sqlite3)
```

Si fallan varios artefactos, aparecen todos en el mismo mensaje, separados por `;`. Regenere cada artefacto indicado con los runbooks de [`operations/`](operations/corpus-build.md) y reinicie Uvicorn. La comprobación se ejecuta antes de abrir ChromaDB, así que un directorio `chroma/` vacío no se modifica.

### `Index record count mismatch`, `Index ID mismatch` o `Missing parent chunks`

Uvicorn registra `API startup failed; the service will not report readiness.` seguido de los problemas encontrados, separados por `;`, con los conteos y hasta 5 IDs de ejemplo. Indica que ChromaDB, BM25 y `parents.jsonl` se construyeron a partir de versiones distintas del corpus. La causa más común es volver a vectorizar sin borrar `data/processed/chroma/`: la vectorización añade y actualiza registros, pero no elimina los obsoletos. Reconstruya los índices desde cero con [`operations/rag-langgraph.md`](operations/rag-langgraph.md#fallos-frecuentes) y reinicie Uvicorn.

### `Catalog contains invalid JSON` o `Catalog does not match the expected schema`

El servicio de diagnóstico carga y valida al arrancar los tres catálogos que usa la API (`res0312_riesgo_i_1_10_general.json`, `res0312_riesgo_i_11_50.json` y `res0312_riesgo_i_51_plus.json`, en `agents/diagnostico_cumplimiento/catalog/data/`). Si alguno falla, Uvicorn registra `API startup failed; the service will not report readiness.` con la ruta del catálogo, y la API no arranca. Corrija el archivo indicado y reinicie Uvicorn.

Los catálogos se leen una sola vez: editar uno con la API en marcha no tiene efecto hasta reiniciarla. El catálogo agropecuario no se carga, porque la API no admite Unidades de Producción Agropecuaria.

### `OSError: We couldn't connect to 'https://huggingface.co' ... couldn't find them in the cached files`

Uvicorn registra `API startup failed; the service will not report readiness.` con ese mensaje. `HF_HUB_OFFLINE=1` está activo, pero falta en `HF_HOME` la revisión fija de Qwen o de ALIA. Descárguela una vez con conexión, sin `HF_HUB_OFFLINE`, y vuelva a arrancar en modo sin conexión:

```bash
HF_HUB_OFFLINE=0 uvicorn agents.api.main:app
```

Las revisiones están en `pipeline/chunking/config.py` (`DEFAULT_EMBEDDING_MODEL_REVISION`) y en `agents/consulta_normativa/langchain_rag/config.py` (`RERANKER_MODEL_REVISION`).

### `Address already in use`

Compruebe el único puerto del backend:

```bash
ss -ltnp | grep ':8000'
```

### Error al abrir ChromaDB

Verifique que existan los artefactos requeridos en `data/processed/` y que `chromadb` esté instalado en el entorno activo.

### El frontend no puede comunicarse con el backend

Compruebe que el frontend use `http://127.0.0.1:8000` como única URL base. El origen del frontend debe figurar en `CORS_ALLOWED_ORIGINS` (sección 3) con el mismo esquema, host y puerto.

## 9. Detener el backend

En la terminal donde se ejecuta Uvicorn:

```text
Ctrl + C
```

Esto detiene ambos agentes porque forman parte de la misma aplicación y elimina las sesiones de diagnóstico en memoria.
