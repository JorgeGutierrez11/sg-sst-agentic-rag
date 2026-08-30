# RAG LangChain/LangGraph de consulta normativa

Esta es la implementación actual de consulta normativa. Vive en `agents/consulta_normativa/langchain_rag/` y ejecuta un grafo explícito para recuperar evidencia, decidir si hay contexto suficiente y generar una respuesta fundamentada.

## Operación

Antes de consultar deben existir dos índices locales:

| Índice | Ruta | Construcción |
|---|---|---|
| ChromaDB `sg_sst_base_rag` | `data/processed/chroma` | [Guía operativa de vectorización](../operations/vectorization.md) |
| BM25S | `data/processed/bm25` | [Guía operativa de BM25](../operations/bm25-sparse-retrieval.md) |

El runtime abre ambos índices existentes, construye un recuperador híbrido con `agents/shared/hybrid_retrieval.py` y lo pasa a `build_langgraph_rag(..., top_k=RETRIEVAL_TOP_K)`.

Los pasos de ejecución viven en el runbook [`../operations/rag-langgraph.md`](../operations/rag-langgraph.md).

## Archivos principales

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Constantes de Chroma, BM25, DeepSeek, temperatura y `top_k`. |
| `formatting.py` | Normalización de documentos, construcción de contexto y referencias. |
| `graph.py` | Construcción y ejecución del `StateGraph`. |
| `main.py` | Entrypoint CLI actual: inicializa dependencias, abre Chroma y BM25 existentes, crea el recuperador híbrido y ejecuta el grafo. |
| `models.py` | Modelos `RetrievedDocument` y `LangChainRagResult`. |
| `prompts.py` | Instrucciones del sistema y prompt humano. |
| `agents/shared/hybrid_retrieval.py` | Fusiona resultados Chroma y BM25 con RRF y conserva trazabilidad de fuentes. |

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

Luego invoca el modelo con `llm.invoke(messages)`. El runtime usa DeepSeek con el modelo `deepseek-chat`, base URL `https://api.deepseek.com` y temperatura `0`.

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
| Recuperación runtime | Híbrida: Chroma + BM25 con fusión RRF. |
| Colección Chroma | Abre una colección existente; no debe crear una colección vacía durante consulta. |
| Colección esperada | `sg_sst_base_rag`. |
| Índice BM25 | Abre un índice existente; no debe crear un índice vacío durante consulta. |
| Persistencia esperada | `data/processed/chroma` y `data/processed/bm25`. |
| Top-k final | `RETRIEVAL_TOP_K`; `DEFAULT_TOP_K` queda solo como alias de compatibilidad. |
| Pool candidato híbrido | `HYBRID_CANDIDATE_TOP_K` por motor antes de fusionar. |
| Trazabilidad híbrida | Metadata `_retrieval_sources`, por ejemplo `['chroma']`, `['bm25']` o `['chroma', 'bm25']`. |
| Variable requerida | `DEEPSEEK_API_KEY`. |
| Evidencia suficiente | Existe al menos un documento recuperado. |
| Sin evidencia | Respuesta determinística sin invocar el LLM. |
