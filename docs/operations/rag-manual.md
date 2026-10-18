# Runbook operativo: RAG manual congelado

> **Status:** `Baseline`
> **Audience:** operator, academic-reviewer
> **Verified against:** `agents/consulta_normativa/manual_implementation/main.py`, `rag_base.py`
> **Last verified:** 2026-10-18
> **Replacement:** [rag-langgraph.md](rag-langgraph.md)

Esta guía cubre la operación de la línea base manual en `agents/consulta_normativa/manual_implementation/`. Úsala como referencia o comparación; no es la implementación RAG actual por defecto.

## Propósito

Ejecutar, revisar o diagnosticar el flujo manual mínimo de consulta normativa SG-SST sobre una colección ChromaDB existente.

## Prerrequisitos

| Requisito | Detalle |
|---|---|
| Vector store | Debe existir `data/processed/chroma` con la colección `sg_sst_base_rag`. |
| API key | `GROQ_API_KEY` debe existir si se usa la ruta generativa de la CLI. |
| Dependencias | Instalar `requirements.txt`, incluyendo Chroma y `langchain_groq`. |
| Estado | Implementación congelada/de referencia, no flujo vigente. |

## Ruta rápida

```bash
export GROQ_API_KEY="tu_api_key"
python -m agents.consulta_normativa.manual_implementation.main
```

> Los imports del módulo apuntan a `agents.consulta_normativa.manual_implementation.{config,rag_base,prompts}` y reutilizan `agents.consulta_normativa.langchain_rag.retrieval.chroma_retrieval` para abrir la colección. Ya no quedan imports legacy.

## Comportamiento esperado

Según el código de `manual_implementation/main.py`, la CLI interactiva muestra estos literales exactos:

| Momento | Literal de consola |
|---|---|
| Inicio | `RAG normativo listo. Escribe 'exit' o 'quit' para salir.` |
| Prompt | `Pregunta> ` |
| Contexto | `Contexto recuperado:` |
| Respuesta | `Respuesta:` |
| Fuentes | `Referencias:` |

La sesión termina con `exit`, `quit`, EOF o `Ctrl+C`. Los errores controlados se imprimen en stderr como `Error during <stage>:` y devuelven código `2` cuando ocurren durante la inicialización.

## Fallos frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| `GROQ_API_KEY is not configured` | Falta la variable de entorno. | Exportar `GROQ_API_KEY` antes de iniciar la CLI. |
| Error al abrir Chroma | Falta `data/processed/chroma` o la colección `sg_sst_base_rag`. | Ejecutar primero [`vectorization.md`](vectorization.md). |
| No hay evidencia | No se recuperaron documentos para la pregunta. | Revisar consulta, corpus vectorizado y cobertura de chunks/tablas. |

## Documentos relacionados

- Arquitectura de la línea base manual: [`../architecture/retrieval-manual.md`](../architecture/retrieval-manual.md).
- Implementación actual: [`rag-langgraph.md`](rag-langgraph.md).
- Vectorización previa: [`vectorization.md`](vectorization.md).
