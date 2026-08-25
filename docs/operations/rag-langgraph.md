# Runbook operativo: RAG LangChain/LangGraph

Esta guía cubre la ejecución de la implementación RAG actual en `agents/consulta_normativa/langchain_rag/`.

## Propósito

Operar la consulta normativa SG-SST actual: abre una colección ChromaDB existente, abre un índice BM25 existente, ejecuta recuperación híbrida en LangGraph y genera respuestas fundamentadas con Groq.

## Prerrequisitos

| Requisito | Detalle |
|---|---|
| Vector store | Debe existir `data/processed/chroma` con la colección `sg_sst_base_rag`. |
| Índice BM25 | Debe existir `data/processed/bm25`. |
| API key | `GROQ_API_KEY` debe estar en el entorno. |
| Dependencias | Instalar `requirements.txt`, incluyendo Chroma, LangChain, LangGraph y `langchain_groq`. |
| Modelo | `langchain_rag/config.py` usa `openai/gpt-oss-120b` con temperatura `0`. |

La consulta abre la colección existente con `open_existing_collection(...)` y el índice BM25 existente con `open_existing_index(...)`; no debe crear índices vacíos durante la operación. El top-k final sale de `RETRIEVAL_TOP_K`, mientras `HYBRID_CANDIDATE_TOP_K` controla el pool candidato por motor antes de la fusión.

## Ruta rápida

```bash
export GROQ_API_KEY="tu_api_key"
python -m agents.consulta_normativa.langchain_rag.main
```

También se puede responder una sola pregunta y salir:

```bash
python -m agents.consulta_normativa.langchain_rag.main "¿Qué debe incluir el plan anual de trabajo del SG-SST?"
```

## Comportamiento esperado

La CLI interactiva imprime literales en inglés porque son las cadenas exactas del código actual:

| Momento | Literal de consola |
|---|---|
| Inicio | `Experimental LangChain RAG ready. Type 'exit' or 'quit' to leave.` |
| Prompt | `Question> ` |
| Respuesta | `Answer:` |
| Fuentes | `References:` solo si existen referencias |

La sesión termina con `exit`, `quit`, EOF o `Ctrl+C`. Los errores operacionales controlados se imprimen en stderr como `Error during <stage>:` y devuelven código `2`.

## Efectos secundarios actuales

Durante la construcción del runtime, el código intenta escribir el diagrama del grafo en:

```text
data/images/base_rag_graph.png
```

Si la carpeta no existe o no hay permisos de escritura, la inicialización puede fallar antes de entrar a la CLI.

## Fallos frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| `GROQ_API_KEY is not configured` | Falta la variable de entorno. | Exportar `GROQ_API_KEY` antes de iniciar. |
| Error al abrir Chroma | Falta `data/processed/chroma` o la colección `sg_sst_base_rag`. | Ejecutar primero [`vectorization.md`](vectorization.md). |
| Error al abrir BM25 | Falta `data/processed/bm25`. | Ejecutar primero [`bm25-sparse-retrieval.md`](bm25-sparse-retrieval.md). |
| Error al guardar `base_rag_graph.png` | Falta `data/images/` o no hay permisos. | Crear/verificar la carpeta antes de ejecutar. |
| Respuesta de evidencia insuficiente | La recuperación híbrida no devolvió documentos. | Revisar corpus, vectorización, índice BM25 y formulación de la pregunta. |

## Documentos relacionados

- Arquitectura de esta implementación: [`../architecture/retrieval-langgraph.md`](../architecture/retrieval-langgraph.md).
- Línea base manual congelada: [`rag-manual.md`](rag-manual.md).
- Vectorización previa: [`vectorization.md`](vectorization.md).
- Índice BM25 previo: [`bm25-sparse-retrieval.md`](bm25-sparse-retrieval.md).
