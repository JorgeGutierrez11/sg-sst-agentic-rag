# RAG manual de consulta normativa

Esta implementación es una línea base congelada para comparación. Vive en `agents/consulta_normativa/manual_implementation/` y no debe presentarse como el flujo actual por defecto.

## Responsabilidad

El RAG manual muestra el flujo mínimo de recuperación y respuesta sobre una colección ChromaDB existente. Su valor principal es servir como referencia simple frente a implementaciones más experimentales.

## Archivos principales

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Constantes de ejecución: ruta Chroma, colección, modelo Groq, temperatura y `top_k`. |
| `main.py` | CLI de la línea base manual. |
| `prompts.py` | Construcción del prompt base con reglas de grounding. |
| `rag_base.py` | Orquestación manual de recuperación, contexto, referencias, prompt, generación y fallback. |

## Flujo interno

`rag_base.py` ejecuta la secuencia:

```text
answer_question
  -> retriever
  -> recovered_documents
  -> build_context
  -> build_references
  -> build_base_prompt
  -> generator o fallback
  -> RagAnswer
```

El resultado público es `RagAnswer(answer, references, context, prompt)`.

## Recuperación y contexto

- El retriever se crea con `chroma_retriever(collection)`.
- La consulta usa `query_top_k(...)` sobre Chroma.
- Los documentos recuperados se normalizan como `RecoveredDocument(document, metadata)`.
- El contexto usa índices visibles (`[1]`, `[2]`, etc.) y referencias compactas desde la metadata plana.
- Las referencias se deduplican en orden de aparición.

## Fallback

Si no se recupera contexto, no se debe inventar una respuesta. El fallback determinístico es:

```text
La evidencia recuperada es insuficiente para responder la pregunta.
```

## Límite de uso

Esta carpeta conserva una referencia funcional mínima. Las decisiones de arquitectura y ejecución del RAG actual deben documentarse en [retrieval-langgraph.md](retrieval-langgraph.md).

Para operación puntual de esta línea base, consulta [`../operations/rag-manual.md`](../operations/rag-manual.md).
