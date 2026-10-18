# RAG LangChain/LangGraph de consulta normativa

> **Status:** `Current`
> **Audience:** maintainer, contributor
> **Verified against:** `agents/consulta_normativa/langchain_rag/graph.py`, `main.py`, `config.py`, `core/routes.py`, `retrieval/`
> **Last verified:** 2026-10-18
> **Replacement:** N/A

Esta es la implementación actual de consulta normativa. Vive en `agents/consulta_normativa/langchain_rag/` y ejecuta un `StateGraph` que incorpora el contexto empresarial, expande la consulta, recupera evidencia híbrida, la reordena, la valida y genera una respuesta fundamentada.

## Artefactos requeridos

| Artefacto | Ruta | Construcción |
|---|---|---|
| ChromaDB `sg_sst_base_rag` | `data/processed/chroma` | [Vectorización](../operations/vectorization.md) |
| Índice BM25S | `data/processed/bm25` | [BM25](../operations/bm25-sparse-retrieval.md) |
| Parent chunks | `data/processed/chunks/parents.jsonl` | [Construcción del corpus](../operations/corpus-build.md) |
| Documentos de tabla | `data/processed/table_documents.jsonl` | [Procesamiento de tablas](../operations/table-processing.md) |

El runtime abre los índices existentes y nunca crea índices vacíos. `build_runtime` (`main.py`) además carga el reranker, el lookup de padres, la primera parte de cada tabla, un checkpointer `InMemorySaver` y un `InMemoryStore` con embeddings `Qwen/Qwen3-Embedding-0.6B` (1024 dimensiones) para la memoria de largo plazo. La memoria vive solo en el proceso: se pierde al reiniciar.

## Archivos principales

| Ruta (bajo `langchain_rag/`) | Responsabilidad |
|---|---|
| `config.py` | Rutas de Chroma, modelos (DeepSeek, Groq, reranker), temperatura, `top_k` y constantes RRF/híbridas; carga `.env` con `load_project_environment`. |
| `main.py` | `build_runtime` (dependencias y grafo) y CLI. |
| `graph.py` | Construcción y ejecución del `StateGraph`. |
| `core/` | Estado del grafo, invocación del LLM, rutas condicionales e instrumentación de trazas. |
| `retrieval/` | Chroma, BM25 (`DEFAULT_BM25_PATH`), fusión híbrida RRF, reranking, expansión a padres y complemento de tablas. |
| `query_understanding/` | Expansión de consulta (cableada); reescritura y Multi-Query (no cableadas). |
| `business_context/` | Perfil empresarial, historial y técnicas de memoria. |
| `validation/` | Relevance grading (cableado); sufficient context gate y self-refine (no cableados). |
| `formatting.py`, `models.py`, `prompts.py` | Contexto, referencias, modelos de resultado y prompts. |

## Grafo de ejecución

```text
business_profile
  -> retrieval_long_term_memory
  -> expand_query
  -> retrieve                      # híbrido Chroma + BM25 con RRF sobre retrieval_query
  -> normalize_documents
  -> rerank                        # cross-encoder: pool 16 -> top 8
  -> expand_parent_documents
  -> record_retrieval_trace
  -> retrieval_relevance_grading   # filtra documentos no relevantes
  -> complement_linked_tables      # agrega la primera parte de tablas enlazadas
  -> evidence_route
       with_evidence:    format_context -> build_messages -> generate_answer
       without_evidence: fallback_answer
  -> save_conversation_turn
  -> store_long_term_memory
  -> format_result
```

`evidence_route` (`core/routes.py`) devuelve `with_evidence` si quedan documentos después del grading. Por lo tanto, "sin evidencia" incluye el caso en que el grader rechaza todos los documentos recuperados.

`sufficient_context_route` existe en `core/routes.py` pero no está conectado al grafo.

## Generación

Con evidencia, el grafo construye un `SystemMessage` con las instrucciones base y un `HumanMessage` con la pregunta, el contexto normativo y el contexto empresarial vigente, e invoca el LLM mediante `invoke_llm_text` (`core/llm.py`). El modelo es DeepSeek `deepseek-chat` en `https://api.deepseek.com` con temperatura `0`.

Sin evidencia, `fallback_answer` también invoca el LLM con `FALLBACK_PROMPT` y un mensaje de diagnóstico (traza del grading, error de expansión y contexto empresarial). Solo si esa llamada falla devuelve el texto determinístico de evidencia insuficiente.

El resultado público es `LangChainRagResult(answer, references, context, prompt, chunks)`.

## Contratos operativos

| Aspecto | Contrato |
|---|---|
| Pool por motor | `HYBRID_SOURCE_CANDIDATE_TOP_K = 60` candidatos de Chroma y de BM25. |
| Salida híbrida | `HYBRID_RRF_OUTPUT_TOP_K = 16`, con `RRF_K = 60`. |
| Reranker | `SINAI/ALIA-MrBERT-es-legal-administrative-reranker`, CPU, `max_length=512`, lotes de 12. |
| Top-k final | `RERANKER_FINAL_TOP_K = DEFAULT_TOP_K = 8`, antes de la expansión a padres. |
| Trazabilidad híbrida | Metadata `_retrieval_sources`: `['chroma']`, `['bm25']` o `['chroma', 'bm25']`. |
| Variable requerida | `DEEPSEEK_API_KEY`. |
| Imagen del grafo | Solo la CLI escribe `data/images/base_rag_graph.png`; la API usa `build_runtime(write_graph_image=False)`. |

## Ejecución

- CLI: [runbook RAG LangGraph](../operations/rag-langgraph.md).
- API HTTP: [referencia de la API](../reference/api.md).
- Técnicas individuales: [`docs/techniques/`](../techniques/retrieval/hybrid-retrieval.md).
