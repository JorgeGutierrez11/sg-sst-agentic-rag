# Plan por fases para preparar el entorno de despliegue

> **Status:** `Current`
> **Audience:** maintainer
> **Verified against:** `requirements.txt`, `.python-version`, `agents/api/main.py`
> **Last verified:** 2026-10-18
> **Replacement:** N/A

Proyecto: SG-SST Agentic RAG Componente: Backend — FastAPI / Python Versión de Python: 3.14 Objetivo general: preparar un entorno reproducible, seguro y listo para su contenedorización, integración continua y posterior despliegue en producción.

## Fase 1 — Baseline local reproducible

Objetivo: garantizar que cualquier desarrollador pueda instalar y ejecutar el sistema bajo las mismas condiciones.

### Actividades

1. Definir Python `3.14` como versión oficial.
2. Crear un entorno virtual `.venv` utilizando esa versión.
3. Instalar las dependencias de `requirements.txt`.
4. Verificar las importaciones y ejecutar las pruebas focalizadas:
   ```
   python -m unittest agents.api.tests.test_main
   python -m compileall agents/api agents/consulta_normativa agents/diagnostico_cumplimiento
   ```
5. Confirmar que el archivo `.env` no esté rastreado por Git.

Criterio de aceptación: la API inicia correctamente desde un entorno limpio y todas las pruebas focalizadas pasan.

## Fase 2 — Dependencias reproducibles

Objetivo: eliminar diferencias entre instalaciones y garantizar versiones compatibles.

### Actividades

1. Resolver las dependencias utilizando Python `3.14`.
2. Verificar las versiones instaladas de:
   - FastAPI
   - Uvicorn
   - Pydantic
   - LangChain
   - LangGraph
   - langchain-openai
   - ChromaDB
   - BM25S
   - ReportLab
   - HTTPX
   - Pytest
3. Fijar versiones compatibles en `requirements.txt`.
4. Declarar explícitamente `chromadb` y `bm25s`.
5. Separar las dependencias de desarrollo y pruebas cuando sea necesario:
   ```
   requirements.txt
   requirements-dev.txt
   ```

Criterio de aceptación: una instalación limpia reproduce el mismo conjunto de dependencias y supera las pruebas de consulta normativa, diagnóstico y API.

## Fase 3 — Configuración y gestión de secretos

Objetivo: unificar la configuración entre desarrollo, CI y producción sin exponer información sensible.

### Actividades

1. Utilizar `.env` exclusivamente para el desarrollo local.
2. Crear `.env.example` sin valores secretos:
   ```
   DEEPSEEK_API_KEY=
   IP_ADDRESS=http://localhost:3000
   ```
3. Documentar las variables obligatorias y opcionales.
4. Configurar GitHub Actions:
   - `DEEPSEEK_API_KEY` como Secret.
   - Origen CORS como Variable.
5. Sustituir progresivamente `IP_ADDRESS` por `CORS_ALLOWED_ORIGINS`, con validación explícita de los orígenes permitidos.

Criterio de aceptación: ningún secreto aparece en el repositorio, Dockerfile, logs, pruebas ni artefactos generados por CI.

## Fase 4 — Salud y disponibilidad

Objetivo: permitir que Docker y la infraestructura distingan entre un proceso activo y una API preparada para atender solicitudes.

### Estado actual

Los siguientes endpoints ya están implementados:

| Endpoint            | Función   | Estado                                |
| ------------------- | --------- | ------------------------------------- |
| `GET /health`       | Liveness  | Implementado                          |
| `GET /health/ready` | Readiness | Implementado, pendiente de validación |

### Actividades pendientes

Ejecutar las pruebas:

```
python -m unittest agents.api.tests.test_main
```

### Criterios de aceptación

- `/health` responde rápidamente y no depende de servicios externos.
- `/health/ready` devuelve HTTP `200` únicamente cuando RAG y diagnóstico están inicializados.
- Ninguno de los endpoints de salud necesita llamar a DeepSeek.
- Un fallo durante la inicialización impide reportar readiness positiva.

## Fase 5 — Validación de artefactos locales

Objetivo: evitar que la API inicie con índices incompletos, ilegibles o inconsistentes.

### Artefactos que deben verificarse

```
data/processed/
├── chroma/
├── bm25/
├── chunks/
│   └── parents.jsonl
└── table_documents.jsonl
```

También deben validarse los catálogos requeridos por el agente de diagnóstico.

### Actividades

1. Definir las rutas obligatorias para el funcionamiento del runtime.
2. Establecer qué artefactos deben utilizarse en modo de solo lectura.
3. Implementar mensajes de error controlados cuando falten archivos.
4. Definir la política de descarga, almacenamiento y caché de los modelos:
   - Qwen — Embeddings.
   - ALIA — Reranking.
5. Verificar la compatibilidad entre los índices utilizados por el sistema.

Criterio de aceptación: los índices faltantes o ilegibles impiden la disponibilidad de la API, generan logs claros y no provocan la creación automática de índices vacíos.

## Fase 6 — Dockerización local

Objetivo: construir una imagen reproducible y segura del backend.

### Archivos por crear

```
Dockerfile
.dockerignore
compose.yaml
```

### Requisitos técnicos

- Utilizar Python `3.14`.
- Ejecutar la aplicación mediante un usuario no privilegiado.
- Configurar inicialmente un único worker.
- Deshabilitar `--reload` en producción.
- Excluir `.env` de la imagen.
- Montar los índices RAG como volúmenes de solo lectura. ChromaDB no puede abrirse en solo lectura: el runtime copia el índice al arrancar y consulta la copia, así que `RAG_CHROMA_WORKING_DIR` debe apuntar a un volumen o `tmpfs` con escritura (ver [`plan-fase-5-artefactos.md`](plan-fase-5-artefactos.md), Parte 4).
- Mantener la caché de modelos en un volumen independiente.
- Configurar el healthcheck utilizando `/health/ready`.
- Preparar el entorno para el uso posterior de GPU en el reranker.

Criterio de aceptación: mediante `docker compose up`, el backend inicia y permite utilizar los endpoints de salud, consulta normativa, diagnóstico y generación de PDF.

## Fase 7 — Separación del pipeline offline

Objetivo: independizar el procesamiento del corpus normativo de la ejecución de los agentes.

### Flujo de procesamiento

```
Documentos DOCX
      ↓
    Pandoc
      ↓
   Limpieza
      ↓
   Chunking
      ↓
Procesamiento de tablas
      ↓
  Vectorización
      ↓
  Chroma + BM25S
```

### Actividades

1. Crear un contenedor o job independiente para ejecutar el pipeline.
2. Incluir Pandoc y las dependencias específicas del procesamiento documental.
3. Permitir escritura únicamente en las ubicaciones destinadas a generar artefactos.
4. Configurar el backend para consumir los índices sin reconstruirlos.
5. Definir un procedimiento controlado de regeneración y publicación de índices.

Criterio de aceptación: la API opera exclusivamente en modo de consulta y el pipeline puede regenerar los índices de manera independiente, sin modificar los artefactos en uso.

## Fase 8 — Integración continua con GitHub Actions

Objetivo: detectar errores y regresiones antes de integrar cambios al repositorio principal.

### Pipeline propuesto

1. Preparar el entorno con Python `3.14`.
2. Instalar las dependencias.
3. Ejecutar las pruebas automatizadas:
   ```
   python -m unittest discover -s pipeline/tests
   python -m unittest discover -s agents/consulta_normativa/tests
   python -m unittest discover -s agents/diagnostico_cumplimiento/tests
   python -m compileall pipeline agents
   ```
4. Construir la imagen Docker.
5. Ejecutar pruebas de integración y smoke tests para:
   - `GET /health`
   - `GET /health/ready`
6. Verificar que la imagen Docker no incluya archivos `.env` ni secretos.

Consideración: las pruebas de readiness deberán ejecutarse con los modelos y artefactos necesarios. No se debe asumir que una imagen recién construida puede inicializar el RAG sin ellos.

Criterio de aceptación: ningún cambio puede integrarse si fallan las pruebas, las validaciones de código o la construcción de la imagen Docker.

## Fase 9 — Endurecimiento previo a producción

Objetivo: reducir los riesgos operativos y de seguridad antes de exponer públicamente el backend.

### Controles necesarios

- Implementar autenticación y autorización.
- Configurar límites de solicitudes (rate limiting).
- Establecer límites de tamaño de payload.
- Implementar logs estructurados sin registrar preguntas, respuestas ni información empresarial sensible.
- Escanear vulnerabilidades de dependencias e imágenes Docker.
- Definir políticas de retención y eliminación de diagnósticos.
- Implementar backups y versionado de índices RAG.
- Medir y dimensionar el consumo de CPU/RAM para Qwen y ALIA.
- Validar la persistencia de sesiones frente a reinicios.
- Establecer procedimientos de recuperación ante fallos.

Criterio de aceptación: el backend puede exponerse públicamente con controles verificables de acceso, disponibilidad, protección de datos y recuperación.

## Resumen de fases

| Fase                | Entregable principal                       |
| ------------------- | ------------------------------------------ |
| 1. Baseline local   | Entorno Python funcional                   |
| 2. Dependencias     | Instalación reproducible                   |
| 3. Configuración    | Variables y secretos controlados           |
| 4. Salud            | Liveness y readiness validados             |
| 5. Artefactos       | Índices y modelos verificados              |
| 6. Dockerización    | Backend ejecutable con Compose             |
| 7. Pipeline offline | Construcción de corpus independiente       |
| 8. CI               | Validaciones automáticas en GitHub Actions |
| 9. Seguridad        | Backend preparado para exposición pública  |

Observación arquitectónica: este plan prepara correctamente la contenedorización, pero no resuelve por sí solo la persistencia de las sesiones en memoria de los agentes ni el desacoplamiento del reranker para ejecutarlo mediante GPU serverless. Ambos aspectos deberán incorporarse al diseño del despliegue antes de considerar el backend preparado para producción.
