# Guía operativa: backend en Docker

> **Status:** `Current`
> **Audience:** operator
> **Verified against:** `Dockerfile`, `.dockerignore`, `compose.yaml`, `compose.dev.yaml`, `docker/download_models.py`
> **Last verified:** 2026-10-20
> **Replacement:** N/A

Esta guía construye y ejecuta la API unificada en un contenedor. La imagen contiene el código, las dependencias (PyTorch solo CPU) y los dos modelos de Hugging Face con su revisión fija; **no contiene el corpus**. El contenedor monta `data/processed/` del host en solo lectura, y el corpus se construye en el host con [`corpus-build.md`](corpus-build.md). Ejecuta todos los comandos desde la raíz del repositorio. Para la ejecución sin contenedor, consulta [`getting-started.md`](../getting-started.md).

## Ruta rápida

```bash
python -m pipeline.offline_corpus validate   # El corpus publicado debe existir y ser consistente
docker compose up -d --build
docker compose ps                            # Esperar STATUS "healthy"
curl http://127.0.0.1:8000/health/ready      # {"status":"ready"}
docker compose down
```

Swagger queda disponible en `http://127.0.0.1:8000/docs`.

## Prerrequisitos

| Requisito | Verificación práctica |
|---|---|
| Docker Engine y Docker Compose v2 | `docker compose version`. Verificado con Docker 29.7.2 y Compose 5.5.1. |
| Archivo `.env` | Copia [`.env.example`](../../.env.example) a `.env` y completa `DEEPSEEK_API_KEY` y `CORS_ALLOWED_ORIGINS` (ver [`getting-started.md`](../getting-started.md#3-configurar-las-variables-de-entorno)). Compose se niega a arrancar si falta. |
| Corpus publicado | `python -m pipeline.offline_corpus validate` termina sin errores. |
| Espacio en disco | La imagen ocupa unos 6 GB; el build necesita margen adicional para las capas intermedias. |
| Acceso a internet durante el build | El build descarga PyTorch, las dependencias y los modelos. El contenedor no necesita red para arrancar. |

## Qué contiene la imagen

El `Dockerfile` tiene tres etapas; solo la última forma la imagen final.

| Etapa | Contenido |
|---|---|
| `deps` | Entorno virtual en `/opt/venv` con `torch==2.14.1` del índice CPU de PyTorch y luego `requirements.txt`. |
| `models` | `docker/download_models.py` lee las revisiones fijas de `pipeline/chunking/config.py` y `agents/consulta_normativa/langchain_rag/config.py` y descarga ambos modelos en `/opt/hf-cache`. |
| `runtime` | Copia el entorno virtual, la caché de modelos, `agents/` y `pipeline/`. Corre como el usuario sin privilegios `10001`, con `HF_HUB_OFFLINE=1`, un único worker de Uvicorn y un `HEALTHCHECK` contra `/health/ready`. |

El `.dockerignore` funciona como lista blanca: solo entran `requirements.txt`, `agents/`, `pipeline/` y `docker/`, sin tests ni `__pycache__`. Por eso `.env`, `data/` y `evaluation/` nunca llegan a la imagen.

## Entorno de producción: `compose.yaml`

`docker compose up` usa solo este archivo.

| Configuración | Comportamiento |
|---|---|
| `env_file: .env` (`required: true`) | Inyecta los secretos al ejecutar, no al construir. |
| Bind `./data/processed` → `/app/data/processed` | Solo lectura y `create_host_path: false`: si falta la carpeta del host, el arranque falla en vez de crear una vacía. |
| `tmpfs` en `/tmp` (256 MiB, modo `1777`) | Aloja la copia desechable de Chroma (`RAG_CHROMA_WORKING_DIR=/tmp/chroma-work`), porque Chroma reescribe sus archivos incluso al consultar. |
| `ports: 127.0.0.1:8000:8000` | Publica la API solo en el loopback del host; no es accesible desde la red local. |
| `restart: on-failure:3` | Reintenta como máximo tres veces si el proceso termina con error, para que un corpus ausente no provoque un bucle infinito. |

```bash
docker compose up -d --build     # Construir (si cambió algo) y arrancar en segundo plano
docker compose logs -f backend   # Seguir los logs
docker compose ps                # Estado y salud del contenedor
docker compose down              # Detener y eliminar contenedor y red
```

Detener el contenedor elimina las sesiones de diagnóstico en memoria, igual que detener Uvicorn local.

## Entorno de desarrollo: `compose.dev.yaml`

El overlay de desarrollo se activa de forma explícita con `-f`:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Sobre la configuración de producción, el overlay monta `./agents` y `./pipeline` del host en solo lectura, ejecuta Uvicorn con `--reload` sobre ambas carpetas y desactiva los reinicios (`restart: "no"`). Un cambio en un `.py` recarga la API sin reconstruir la imagen. Los cambios en `requirements.txt`, `Dockerfile` o `docker/` sí requieren `--build`.

Se usa un archivo explícito en lugar de `compose.override.yaml` (que Compose carga automáticamente) para que olvidar el flag `-f` arranque producción, no desarrollo.

## Reconstruir el corpus

El pipeline offline se ejecuta en el host, nunca dentro del contenedor: la imagen no incluye `data/raw/` ni Pandoc, y el corpus está montado en solo lectura.

```bash
docker compose down
python -m pipeline.offline_corpus build
python -m pipeline.offline_corpus validate
docker compose up -d
```

Detén el contenedor antes de `build`, porque la publicación reemplaza los índices montados. No hace falta reconstruir la imagen, salvo que haya cambiado la revisión del modelo Qwen.

## Cuándo reconstruir la imagen

| Cambio | Acción |
|---|---|
| Código en `agents/` o `pipeline/` (producción) | `docker compose up -d --build` |
| `requirements.txt`, `Dockerfile` o `docker/` | `docker compose up -d --build` |
| Revisión del reranker en `langchain_rag/config.py` | `docker compose up -d --build` |
| Revisión de Qwen en `pipeline/chunking/config.py` | Reconstruir el corpus y luego la imagen: los índices dependen de esa revisión. |
| Solo el corpus o `.env` | `docker compose down && docker compose up -d`; no requiere build. |

## Verificación

```bash
# Imagen: PyTorch CPU, sin paquetes NVIDIA, usuario sin privilegios y sin datos privados
docker run --rm sg-sst-backend:local python -c "import torch; print(torch.__version__)"   # ...+cpu
docker run --rm sg-sst-backend:local sh -c 'pip list 2>/dev/null | grep -c nvidia-'       # 0
docker run --rm sg-sst-backend:local id -u                                                # 10001
docker run --rm sg-sst-backend:local sh -c 'test ! -e /app/.env && test ! -e /app/data && test ! -e /app/evaluation'

# Contenedor: disponibilidad y corpus en solo lectura
docker compose up -d
curl -i http://127.0.0.1:8000/health/ready                     # 200
docker compose exec backend touch /app/data/processed/x        # Read-only file system
docker compose down
```

## Troubleshooting

| Síntoma | Causa probable | Acción |
|---|---|---|
| `env file ... .env not found` | Falta `.env` en la raíz. | Crear `.env` a partir de `.env.example`. |
| `bind source path does not exist` | No existe `data/processed/` en el host. | Construir el corpus con `python -m pipeline.offline_corpus build`. |
| El contenedor termina con código `3` y el log muestra `Missing runtime artifact` | El corpus montado está incompleto. | Revisar con `validate` y reconstruir el corpus; luego `docker compose up -d`. |
| El contenedor se detiene tras tres reinicios | Fallo de arranque repetido (`restart: on-failure:3`). | Leer la causa en `docker compose logs backend`. |
| `No space left on device` durante el build | Disco del host lleno. | Revisar con `docker system df` y liberar espacio, por ejemplo con `docker builder prune`. |
| `Permission denied` al leer el corpus | El usuario `10001` no puede leer los archivos del host. | `chmod -R a+rX data/processed` |
| `port is already allocated` o `Address already in use` | Otro proceso usa el puerto 8000, por ejemplo un Uvicorn local. | Detener ese proceso o el otro contenedor. |
| `DEEPSEEK_API_KEY is not configured` | La variable falta o está vacía en `.env`. | Completar `.env` y reiniciar el contenedor. |
