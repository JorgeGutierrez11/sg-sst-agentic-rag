# agents/ — online

Código que corre en tiempo de respuesta, importado por app/backend/.

shared/                     cliente LLM, retriever, prompts base — usado por ambos agentes
consulta_normativa/         Bloque A. Progresión de las 5 etapas vía git tags
                             (etapa-1-rag-base, etapa-2-comprension, ...),
                             NO vía carpetas etapa_1..5 duplicadas.
diagnostico_cumplimiento/   Bloque B.
