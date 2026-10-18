# agents/ — online

Código que corre en tiempo de respuesta. Se expone por HTTP desde `api/` (`uvicorn agents.api.main:app`).

api/                        Composición FastAPI única: CORS, ciclo de vida y sondas /health.
consulta_normativa/         Bloque A. api/ (router /api/v1/query), langchain_rag/ (runtime actual,
                             incluye retrieval/), manual_implementation/ (línea base congelada).
                             Progresión de las 5 etapas vía git tags, NO vía carpetas etapa_1..5.
diagnostico_cumplimiento/   Bloque B. Catálogo, cuestionario, evaluación e informe PDF.

Documentación: ../docs/reference/api.md y ../docs/architecture/retrieval-langgraph.md.
