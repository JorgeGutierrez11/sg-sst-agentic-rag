# RAG LangChain/LangGraph de consulta normativa

Esta es la implementación actual de consulta normativa. Vive en `agents/consulta_normativa/langchain_rag/` y ejecuta un grafo explícito para recuperar evidencia, decidir si hay contexto suficiente y generar una respuesta fundamentada.

## Operación

Antes de consultar debe existir la colección ChromaDB `sg_sst_base_rag`; su construcción se documenta en [la guía operativa de vectorización](../operations/vectorization.md).

Los pasos de ejecución viven en el runbook [`../operations/rag-langgraph.md`](../operations/rag-langgraph.md).

## Archivos principales

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Constantes de Chroma, Groq, temperatura y `top_k`. |
| `formatting.py` | Normalización de documentos, construcción de contexto y referencias. |
| `graph.py` | Construcción y ejecución del `StateGraph`. |
| `main.py` | Entrypoint CLI actual: inicializa dependencias, abre Chroma existente y ejecuta el grafo. |
| `models.py` | Modelos `RetrievedDocument` y `LangChainRagResult`. |
| `prompts.py` | Instrucciones del sistema y prompt humano. |

## Grafo de ejecución

`graph.py` construye un `StateGraph` con esta ruta:

```text
retrieve
  -> normalize_documents
  -> assess_evidence
  -> ruta condicional
```

La condición de evidencia es simple y explícita:

```text
has_evidence = bool(documents)
```

Ramas:

| Ruta | Nodos |
|---|---|
| Sin evidencia | `fallback_answer -> format_result` |
| Con evidencia | `format_context -> build_messages -> generate_answer -> format_result` |

## Generación

Cuando hay evidencia, el grafo construye mensajes LangChain:

```text
SystemMessage(BASE_SYSTEM_INSTRUCTIONS)
HumanMessage(build_human_prompt(...))
```

Luego invoca el modelo con `llm.invoke(messages)`. El runtime usa Groq con el modelo `openai/gpt-oss-120b` y temperatura `0`.

El resultado público es:

```text
LangChainRagResult(answer, references, context, prompt)
```

## CLI

La CLI actual se ejecuta con:

```bash
python -m agents.consulta_normativa.langchain_rag.main
```

Comportamiento visible. Los literales están en inglés porque son las cadenas exactas que imprime la CLI actual:

- prompt interactivo: `Question>`;
- salida principal: `Answer:`;
- salida de fuentes: `References:` solo cuando existen referencias;
- salida con `exit` o `quit`;
- errores operacionales controlados con código `2`.

## Contratos operativos

| Aspecto | Contrato |
|---|---|
| Colección Chroma | Abre una colección existente; no debe crear una colección vacía durante consulta. |
| Colección esperada | `sg_sst_base_rag`. |
| Persistencia esperada | `data/processed/chroma`. |
| Variable requerida | `GROQ_API_KEY`. |
| Evidencia suficiente | Existe al menos un documento recuperado. |
| Sin evidencia | Respuesta determinística sin invocar el LLM. |
