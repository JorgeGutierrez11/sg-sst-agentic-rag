# Tecnicas Elegidas

La comparación usa el `accuracy del juez LLM` de las tres etiquetas de cada técnica y calcula un único valor por técnica con el promedio simple de:

- `Context_Relevance_Label`
- `Answer_Faithfulness_Label`
- `Answer_Relevance_Label`

# Query Understanding

| Técnica | Archivo | Context | Faithfulness | Relevance | Promedio |
|---|---|---:|---:|---:|---:|
| `query_expansion` | [query_expansion.md](query_understanding/query_expansion.md) | 0.900 | 0.975 | 0.988 | 0.954 |
| `multi_query` | [multi_query.md](query_understanding/multi_query.md) | 0.812 | 0.975 | 0.963 | 0.917 |
| `rewrite_query` | [rewrite_query.md](query_understanding/rewrite_query.md) | 0.787 | 0.963 | 0.887 | 0.879 |

### Mejor técnica del directorio

| Directorio | Técnica ganadora | Promedio |
|---|---|---:|
| `query_understanding` | `query_expansion` | 0.954 |

# Retrieval

| Técnica | Archivo | Context | Faithfulness | Relevance | Promedio |
|---|---|---:|---:|---:|---:|
| `r1_hybrid_retrieval` | [r1_hybrid_retrieval.md](retrieval/r1_hybrid_retrieval.md) | 0.938 | 0.950 | 1.000 | 0.963 |
| `r2_hybrid_reranking` | [r2_hybrid_reranking.md](retrieval/r2_hybrid_reranking.md) | 0.925 | 0.975 | 0.988 | 0.963 |
| `r3_hybrid_reranking_parent` | [r3_hybrid_reranking_parent.md](retrieval/r3_hybrid_reranking_parent.md) | 0.975 | 0.988 | 1.000 | 0.988 |

### Mejor técnica del directorio

| Directorio | Técnica ganadora | Promedio |
|---|---|---:|
| `retrieval` | `r3_hybrid_reranking_parent` | 0.988 |

# Business Context

| Técnica | Archivo | Context | Faithfulness | Relevance | Promedio |
|---|---|---:|---:|---:|---:|
| `full_conversation_memory` | [full_conversation_memory.md](business_context/full_conversation_memory.md) | 0.912 | 0.925 | 0.975 | 0.937 |
| `retrieval_long_term_memory` | [retrieval_long_term_memory.md](business_context/retrieval_long_term_memory.md) | 0.938 | 0.938 | 0.975 | 0.950 |
| `summarization_memory` | [summarization_memory.md](business_context/summarization_memory.md) | 0.838 | 0.963 | 1.000 | 0.934 |

### Mejor técnica del directorio

| Directorio | Técnica ganadora | Promedio |
|---|---|---:|
| `business_context` | `retrieval_long_term_memory` | 0.950 |

# Validation

| Técnica | Archivo | Context | Faithfulness | Relevance | Promedio |
|---|---|---:|---:|---:|---:|
| `retrieval_relevance_grading` | [retrieval_relevance_grading.md](validation/retrieval_relevance_grading.md) | 0.825 | 0.963 | 0.950 | 0.913 |
| `self_refine` | [self_refine.md](validation/self_refine.md) | 0.800 | 0.950 | 0.963 | 0.904 |
| `sufficient_context_gate` | [sufficient_context_gate.md](validation/sufficient_context_gate.md) | 0.863 | 0.975 | 0.887 | 0.908 |

### Mejor técnica del directorio

| Directorio | Técnica ganadora | Promedio |
|---|---|---:|
| `validation` | `retrieval_relevance_grading` | 0.913 |



