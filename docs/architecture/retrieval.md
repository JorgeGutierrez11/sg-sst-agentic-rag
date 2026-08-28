# Arquitectura de recuperación normativa

La consulta normativa tiene dos implementaciones RAG separadas. Esta página solo sirve como índice para evitar mezclar responsabilidades entre la línea base manual congelada y la implementación actual con LangChain/LangGraph.

## Implementaciones

| Implementación | Estado | Ruta | Cuándo usarla |
|---|---|---|---|
| Manual | Línea base congelada de referencia | `agents/consulta_normativa/manual_implementation/` | Comparar comportamiento, revisar el flujo mínimo o conservar una referencia antes de experimentos. |
| LangChain/LangGraph | Implementación actual de consulta normativa | `agents/consulta_normativa/langchain_rag/` | Ejecutar y documentar el RAG actual basado en grafo, mensajes LangChain y DeepSeek. |

## Documentos específicos

- [Implementación manual congelada](retrieval-manual.md)
- [Implementación LangChain/LangGraph actual](retrieval-langgraph.md)

La vectorización de ChromaDB se documenta aparte en [Arquitectura de vectorización](vectorization.md) y en la guía operativa [vectorization.md](../operations/vectorization.md). Para ejecutar consultas, usa los runbooks [rag-langgraph.md](../operations/rag-langgraph.md) o [rag-manual.md](../operations/rag-manual.md).
