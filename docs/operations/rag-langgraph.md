# Runbook operativo: RAG LangChain/LangGraph

> **Status:** `Current`
> **Audience:** operator
> **Verified against:** `agents/consulta_normativa/langchain_rag/main.py`, `config.py`, `agents/api/main.py`
> **Last verified:** 2026-10-18
> **Replacement:** N/A

Esta guía cubre la ejecución por CLI de la implementación RAG actual en `agents/consulta_normativa/langchain_rag/`. Para usarla por HTTP, consulta [getting-started.md](../getting-started.md).

## Propósito

Operar la consulta normativa SG-SST actual: abre la colección ChromaDB y el índice BM25 existentes, ejecuta el grafo LangGraph (contexto empresarial, expansión de consulta, recuperación híbrida, reranking, expansión a padres, grading y complemento de tablas) y genera respuestas con DeepSeek. La arquitectura está en [retrieval-langgraph.md](../architecture/retrieval-langgraph.md).

## Prerrequisitos

| Requisito | Detalle |
|---|---|
| Vector store | `data/processed/chroma` con la colección `sg_sst_base_rag`. |
| Índice BM25 | `data/processed/bm25`. |
| Parent chunks | `data/processed/chunks/parents.jsonl`; si falta, el arranque falla con `FileNotFoundError`. |
| Documentos de tabla | `data/processed/table_documents.jsonl`. |
| Carpeta de imágenes | `data/images/` con permisos de escritura (solo CLI). |
| API key | `DEEPSEEK_API_KEY` en el entorno o en `.env`. |
| Modelos | La primera ejecución descarga `Qwen/Qwen3-Embedding-0.6B` y `SINAI/ALIA-MrBERT-es-legal-administrative-reranker` desde Hugging Face. |
| Dependencias | `pip install -r requirements.txt`. |

## Ruta rápida

```bash
python -m agents.consulta_normativa.langchain_rag.main
```

Responder una sola pregunta y salir:

```bash
python -m agents.consulta_normativa.langchain_rag.main "¿Qué debe incluir el plan anual de trabajo del SG-SST?"
```

## Comportamiento esperado

Los literales están en inglés porque son las cadenas exactas del código:

| Momento | Literal de consola |
|---|---|
| Inicio | `Experimental LangChain RAG ready. Type 'exit' or 'quit' to leave.` |
| Prompt | `Question> ` |
| Respuesta | `Answer:` |
| Fuentes | `References:` solo si existen referencias |

Antes de la respuesta, la CLI imprime bloques de depuración: `QUERY EXPANSION`, la traza híbrida con reranking y padres, `RETRIEVAL RELEVANCE GRADING` y `CURRENT BUSINESS CONTEXT`.

La sesión termina con `exit`, `quit`, EOF o `Ctrl+C`. Los errores se imprimen en stderr como `Error during initialization:` o `Error during RAG execution:`. En modo de una sola pregunta devuelven código `2`; en modo interactivo el error de ejecución se imprime y el bucle continúa.

## Efectos secundarios

Al construir el runtime, la CLI escribe `data/images/base_rag_graph.png` e imprime `Grafo guardado exitosamente como 'base_rag_graph.png'`. La API no escribe esta imagen.

La memoria conversacional y de largo plazo es en memoria del proceso: se pierde al salir.

## Fallos frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| `DEEPSEEK_API_KEY is not configured` | Falta la variable. | Definirla en `.env` o exportarla. |
| Error al abrir Chroma | Falta `data/processed/chroma` o la colección. | Ejecutar [vectorization.md](vectorization.md). |
| Error al abrir BM25 | Falta `data/processed/bm25`. | Ejecutar [bm25-sparse-retrieval.md](bm25-sparse-retrieval.md). |
| `FileNotFoundError` de `parents.jsonl` | Falta la salida de chunking. | Ejecutar [corpus-build.md](corpus-build.md). |
| Error al guardar `base_rag_graph.png` | Falta `data/images/` o no hay permisos. | Crear la carpeta. |
| Respuesta de evidencia insuficiente | La recuperación no devolvió documentos o el grader los rechazó todos. | Revisar el bloque `RETRIEVAL RELEVANCE GRADING`, los índices y la pregunta. |

## Documentos relacionados

- Línea base manual congelada: [rag-manual.md](rag-manual.md).
- Pruebas: [testing.md](../testing.md).
