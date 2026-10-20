# proyecto_rag

> **Status:** `Current`
> **Audience:** user, operator, contributor, academic-reviewer, maintainer
> **Verified against:** `agents/api/main.py`, `requirements.txt`, `.python-version`, árbol `docs/`
> **Last verified:** 2026-10-18
> **Replacement:** N/A

Sistema RAG de tesis para **asistencia normativa y diagnóstico de cumplimiento del SG-SST** en MiPymes colombianas de riesgo I. Expone dos agentes detrás de una única API FastAPI:

- **Consulta normativa:** responde preguntas con evidencia del corpus (recuperación híbrida Chroma + BM25, reranking, expansión a documentos padre y generación con DeepSeek).
- **Diagnóstico de cumplimiento:** cuestionario guiado que evalúa requisitos normativos y genera un informe PDF.

**Límites.** El corpus se restringe al Decreto 1072/2015, las Resoluciones 0312/2019, 2346/2007, 1401/2007 y 2013/1986, las Leyes 1562/2012 y 1010/2006 y la clasificación de riesgo del Decreto 768/2022. Las respuestas no sustituyen la asesoría de un profesional SST. Aún no existe frontend (`app/` es un andamiaje vacío).

## Inicio rápido

Requiere Python 3.14, los índices ya construidos en `data/processed/` y un `.env` con `DEEPSEEK_API_KEY` y `CORS_ALLOWED_ORIGINS`.

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn agents.api.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health/ready   # {"status":"ready"} cuando ambos agentes cargaron
```

El paso a paso, las variables de entorno y la solución de problemas están en [docs/getting-started.md](docs/getting-started.md).

## Documentación por audiencia

| Si eres... | Empieza por | Luego |
|---|---|---|
| Usuario de la API | [Referencia de la API](docs/reference/api.md) | [Inicio rápido](docs/getting-started.md) |
| Operador local | [Inicio rápido](docs/getting-started.md) | Runbooks: [corpus](docs/operations/corpus-build.md), [tablas](docs/operations/table-processing.md), [vectorización](docs/operations/vectorization.md), [BM25](docs/operations/bm25-sparse-retrieval.md), [RAG](docs/operations/rag-langgraph.md) |
| Contribuidor | [Mapa de carpetas](docs/guia-carpetas.md) | [Pruebas](docs/testing.md), [arquitectura de recuperación](docs/architecture/retrieval.md) |
| Revisor académico | [Mapa fases ↔ repositorio](docs/mapa-fases-tesis.md) | [Metodología (PDF)](docs/EISI_2026-04-09_14-25-36_pg1409.pdf), [técnicas por etapa](docs/guia-carpetas.md#documentación), [experimentos](docs/experiments/chunking-strategy-comparison.md) |
| Mantenedor | [Arquitectura de recuperación](docs/architecture/retrieval.md) | [Plan de despliegue](docs/plans/plan-docker.md), [pipeline de chunking](docs/architecture/chunking.md) |

## Estados de los documentos

Cada documento abre con un bloque `Status`:

- `Current`: vigente y verificado contra el código.
- `Baseline`: implementación congelada para comparar; no es el flujo recomendado.
- `Experimental`: técnica candidata no conectada al runtime.
- `Historical`: plan ejecutado o snapshot conservado para trazabilidad.

Las instrucciones para agentes de desarrollo están en [AGENTS.md](AGENTS.md).
