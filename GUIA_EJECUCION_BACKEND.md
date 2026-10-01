# Guía de ejecución del backend

Esta guía describe cómo preparar y levantar localmente los dos servicios backend del proyecto SG-SST:

- **Agente 1 — Consulta normativa**
- **Agente 2 — Diagnóstico de cumplimiento**

Los dos servicios se ejecutan desde el mismo repositorio y comparten el mismo entorno virtual de Python.

---

## 1. Requisitos previos

Antes de iniciar, se requiere:

- Git.
- Python **3.12**.
- `pip`.
- Conexión a Internet, al menos durante la primera ejecución.
- Una clave válida de DeepSeek en la variable de entorno `DEEPSEEK_API_KEY`.

Verificar Python:

```bash
python3 --version
```

La versión utilizada durante el desarrollo es Python 3.12.

---

## 2. Preparar el entorno por primera vez

Ubicarse en la raíz del repositorio:

```bash
cd sg-sst-agentic-rag
```

Crear el entorno virtual:

```bash
python3 -m venv .venv-rag
```

Activarlo:

```bash
source .venv-rag/bin/activate
```

Actualizar `pip`:

```bash
python -m pip install --upgrade pip
```

Instalar las dependencias declaradas por el proyecto:

```bash
pip install -r requirements.txt
```

> El entorno virtual solo debe crearse una vez. En ejecuciones posteriores basta con activarlo.

### Dependencias de ejecución que deben estar declaradas

El backend utiliza, entre otras, FastAPI, Uvicorn, ChromaDB, Sentence Transformers, LangChain/LangGraph y ReportLab. La instalación reproducible debe realizarse mediante `requirements.txt`; no se recomienda mantener instalaciones manuales fuera de este archivo.

Si aparece un `ModuleNotFoundError` durante una instalación limpia, se debe corregir `requirements.txt` para incluir la dependencia faltante.

---

## 3. Configurar DeepSeek

El sistema utiliza DeepSeek para las operaciones que requieren un LLM. Antes de levantar los servicios, exportar la clave en la terminal correspondiente:

```bash
export DEEPSEEK_API_KEY="TU_CLAVE"
```

Comprobar que la variable existe sin imprimir su contenido:

```bash
test -n "$DEEPSEEK_API_KEY" && echo "DEEPSEEK_API_KEY configurada"
```

No se deben subir claves privadas al repositorio.

> Si los agentes se levantan desde dos terminales independientes, cada terminal debe disponer de la variable `DEEPSEEK_API_KEY`.

---

## 4. Datos y modelos requeridos por el Agente 1

El Agente 1 utiliza los artefactos de recuperación almacenados en el repositorio, principalmente:

```text
data/processed/chroma/
data/processed/bm25/
data/processed/chunks/parents.jsonl
```

Estos archivos deben existir antes de levantar el servicio.

Durante la primera ejecución también pueden descargarse modelos desde Hugging Face, entre ellos los modelos usados para embeddings y reranking. Esta descarga puede tardar y requiere conexión a Internet.

Actualmente se utilizan modelos como:

```text
Qwen/Qwen3-Embedding-0.6B
BAAI/bge-reranker-v2-m3
```

Las siguientes ejecuciones normalmente reutilizan la caché local de Hugging Face.

---

## 5. Levantar el Agente 1 — Consulta normativa

Abrir una terminal en la raíz del repositorio.

Activar el entorno:

```bash
source .venv-rag/bin/activate
```

Configurar la clave si no está disponible en esa terminal:

```bash
export DEEPSEEK_API_KEY="TU_CLAVE"
```

Levantar la API:

```bash
uvicorn agents.consulta_normativa.api.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

El servicio queda disponible en:

```text
http://127.0.0.1:8000
```

Comprobar salud:

```bash
curl http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

La consulta normativa se expone mediante:

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

> La primera inicialización del Agente 1 puede tardar mientras carga ChromaDB, BM25, embeddings y reranker.

---

## 6. Levantar el Agente 2 — Diagnóstico de cumplimiento

Mantener el Agente 1 ejecutándose y abrir una **segunda terminal**.

Desde la raíz del mismo repositorio:

```bash
source .venv-rag/bin/activate
```

Configurar la clave si no está disponible en esa terminal:

```bash
export DEEPSEEK_API_KEY="TU_CLAVE"
```

Levantar la API del diagnóstico en otro puerto:

```bash
uvicorn agents.diagnostico_cumplimiento.api.main:app \
  --host 127.0.0.1 \
  --port 8001 \
  --reload
```

El servicio queda disponible en:

```text
http://127.0.0.1:8001
```

Comprobar salud:

```bash
curl http://127.0.0.1:8001/api/v1/diagnostics/health
```

Para comprobar la creación de un diagnóstico:

```bash
curl -X POST \
  http://127.0.0.1:8001/api/v1/diagnostics \
  -H 'Content-Type: application/json' \
  -d '{"worker_count":5}'
```

Para una empresa con 5 trabajadores y riesgo I, la respuesta debe iniciar un diagnóstico con el catálogo aplicable de 1 a 10 trabajadores.

---

## 7. Estado esperado de los servicios

Para ejecutar el prototipo completo deben permanecer activos simultáneamente:

| Servicio | Dirección |
|---|---|
| Agente 1 — Consulta normativa | `http://127.0.0.1:8000` |
| Agente 2 — Diagnóstico | `http://127.0.0.1:8001` |
| Frontend | `http://localhost:3000` |

Se recomienda utilizar una terminal independiente para cada proceso.

---

## 8. Ejecuciones posteriores

Después de la instalación inicial no es necesario reinstalar las dependencias en cada ejecución.

Para levantar nuevamente el backend:

**Terminal 1 — Agente 1**

```bash
cd sg-sst-agentic-rag
source .venv-rag/bin/activate
export DEEPSEEK_API_KEY="TU_CLAVE"

uvicorn agents.consulta_normativa.api.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

**Terminal 2 — Agente 2**

```bash
cd sg-sst-agentic-rag
source .venv-rag/bin/activate
export DEEPSEEK_API_KEY="TU_CLAVE"

uvicorn agents.diagnostico_cumplimiento.api.main:app \
  --host 127.0.0.1 \
  --port 8001 \
  --reload
```

---

## 9. Problemas frecuentes

### `DEEPSEEK_API_KEY is not configured`

La clave no está disponible en la terminal actual.

```bash
export DEEPSEEK_API_KEY="TU_CLAVE"
```

### `Address already in use`

El puerto ya está ocupado. Consultar el proceso correspondiente:

```bash
ss -ltnp | grep ':8000'
```

o:

```bash
ss -ltnp | grep ':8001'
```

### Error al abrir ChromaDB

Verificar que exista:

```bash
ls data/processed/chroma
```

### Descarga lenta en la primera ejecución

Es normal que la primera inicialización tarde más debido a la descarga y carga de modelos de Hugging Face.

### El frontend no puede comunicarse con un agente

Comprobar que los tres procesos estén activos en sus puertos esperados:

```text
Frontend  → 3000
Agente 1  → 8000
Agente 2  → 8001
```

---

## 10. Detener los servicios

En cada terminal donde se está ejecutando Uvicorn:

```text
Ctrl + C
```

Esto detiene el servidor correspondiente.
