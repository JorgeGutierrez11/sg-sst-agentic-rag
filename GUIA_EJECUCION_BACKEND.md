# Guía de ejecución del backend

Esta guía explica cómo preparar y ejecutar localmente la API unificada de los agentes de consulta normativa y diagnóstico de cumplimiento del SG-SST.

## 1. Requisitos previos

- Git.
- Python 3.14.
- `pip`.
- Los artefactos locales de recuperación del agente de consulta.
- Conexión a Internet durante la descarga inicial de modelos.
- Una clave válida de DeepSeek en `DEEPSEEK_API_KEY`.

Los principales artefactos requeridos son:

```text
data/processed/chroma/
data/processed/bm25/
data/processed/chunks/parents.jsonl
```

## 2. Preparar el entorno

Desde la raíz del repositorio:

```bash
python3.14 -m venv .venv-rag
source .venv-rag/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

El entorno virtual solo debe crearse una vez. En ejecuciones posteriores basta con activarlo.

El backend usa FastAPI, Uvicorn, ChromaDB, Sentence Transformers, LangChain/LangGraph y ReportLab. Las dependencias de ejecución deben estar declaradas en `requirements.txt`; si una instalación limpia produce `ModuleNotFoundError`, se debe corregir ese manifiesto.

## 3. Configurar DeepSeek

```bash
export DEEPSEEK_API_KEY="TU_CLAVE"
test -n "$DEEPSEEK_API_KEY" && echo "DEEPSEEK_API_KEY configurada"
```

No imprima ni suba claves privadas al repositorio.

## 4. Levantar la API unificada

Active el entorno, configure la clave y ejecute un único proceso Uvicorn:

```bash
source .venv-rag/bin/activate
export DEEPSEEK_API_KEY="TU_CLAVE"

uvicorn agents.api.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

La única URL base del backend es:

```text
http://127.0.0.1:8000
```

La inicialización puede tardar mientras carga ChromaDB, BM25, embeddings y el reranker. La primera ejecución también puede descargar modelos como `Qwen/Qwen3-Embedding-0.6B` y `BAAI/bge-reranker-v2-m3`.

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

## 6. Consulta normativa

La consulta normativa conserva el endpoint:

```text
POST /api/v1/query
```

Ejemplo:

```bash
curl -X POST \
  http://127.0.0.1:8000/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"¿Qué es el SG-SST?"}'
```

Para continuar una conversación, reutilice el `conversation_id` retornado por la primera respuesta.

## 7. Diagnóstico de cumplimiento

Todos los endpoints de diagnóstico usan la misma URL base:

```text
POST /api/v1/diagnostics
POST /api/v1/diagnostics/{diagnosis_id}/answers
POST /api/v1/diagnostics/{diagnosis_id}/complete
GET  /api/v1/diagnostics/{diagnosis_id}/report
```

Crear un diagnóstico para una empresa de riesgo I con cinco trabajadores:

```bash
curl -X POST \
  http://127.0.0.1:8000/api/v1/diagnostics \
  -H 'Content-Type: application/json' \
  -d '{"worker_count":5}'
```

Use el `diagnosis_id` y la siguiente pregunta de la respuesta para enviar respuestas, completar el diagnóstico y descargar el informe PDF.

## 8. Limitación de sesiones de diagnóstico

Las sesiones de diagnóstico se guardan únicamente en la memoria del proceso:

- Ejecute Uvicorn con **un solo worker**.
- Reiniciar el backend elimina todos los diagnósticos en curso.
- `--reload` reinicia el proceso al detectar cambios y también elimina esas sesiones.
- Dos workers no comparten sesiones; una solicitud dirigida a otro worker no encontrará el diagnóstico.
- Las sesiones no son persistentes ni recuperables después de un reinicio.

No use `--workers` mientras el almacenamiento de diagnósticos siga siendo local al proceso.

## 9. Problemas frecuentes

### `DEEPSEEK_API_KEY is not configured`

```bash
export DEEPSEEK_API_KEY="TU_CLAVE"
```

### `Address already in use`

Compruebe el único puerto del backend:

```bash
ss -ltnp | grep ':8000'
```

### Error al abrir ChromaDB

Verifique que existan los artefactos requeridos en `data/processed/` y que `chromadb` esté instalado en el entorno activo.

### El frontend no puede comunicarse con el backend

Compruebe que el frontend use `http://127.0.0.1:8000` como única URL base. La configuración CORS permite el origen de desarrollo `http://localhost:3000`.

## 10. Detener el backend

En la terminal donde se ejecuta Uvicorn:

```text
Ctrl + C
```

Esto detiene ambos agentes porque forman parte de la misma aplicación y elimina las sesiones de diagnóstico en memoria.
