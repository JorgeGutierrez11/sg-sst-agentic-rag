# syntax=docker/dockerfile:1

# 1. CONFIGURACIÓN BASE
ARG PYTHON_IMAGE=python:3.14-slim


# 2. DEPENDENCIAS
FROM ${PYTHON_IMAGE} AS deps

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ARG TORCH_VERSION=2.14.1

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH=/opt/venv/bin:$PATH

RUN python -m venv /opt/venv

# Instalar PyTorch para CPU
RUN pip install \
    --index-url "${TORCH_INDEX_URL}" \
    "torch==${TORCH_VERSION}"

# Instalar dependencias del backend
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt


# 3. DESCARGA DE MODELOS
FROM deps AS models

ENV HF_HOME=/opt/hf-cache

WORKDIR /build

# Archivos de configuración de modelos
COPY pipeline/chunking/config.py pipeline/chunking/config.py
COPY agents/consulta_normativa/langchain_rag/config.py agents/consulta_normativa/langchain_rag/config.py

# Script de descarga
COPY docker/download_models.py docker/download_models.py

RUN python docker/download_models.py

# huggingface_hub writes trees/*.json as 0600; the non-root runtime user needs read access.
RUN find /opt/hf-cache -type f ! -perm -o=r -exec chmod a+r {} +


# 4. IMAGEN DE PRODUCCIÓN
FROM ${PYTHON_IMAGE} AS runtime

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/hf-cache \
    HF_HUB_OFFLINE=1

# Crear usuario sin privilegios
RUN groupadd --system --gid 10001 app \
    && useradd --system \
       --uid 10001 \
       --gid app \
       --create-home \
       --shell /usr/sbin/nologin app

# Copiar dependencias y modelos
COPY --from=deps /opt/venv /opt/venv
COPY --from=models /opt/hf-cache /opt/hf-cache

# Copiar código de la aplicación
WORKDIR /app

COPY agents/ agents/
COPY pipeline/ pipeline/

# Ejecutar sin root
USER 10001:10001

EXPOSE 8000


# 5. HEALTHCHECK
HEALTHCHECK --interval=30s \
    --timeout=5s \
    --start-period=120s \
    --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4)"]


# 6. INICIO DE FASTAPI
CMD ["uvicorn", "agents.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
