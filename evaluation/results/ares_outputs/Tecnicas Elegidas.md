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
| `hybrid_reranking` | [hybrid_reranking.md](retrieval/hybrid_reranking.md) | 0.875 | 0.963 | 0.988 | 0.942 |
| `parent_document_retrieval` | [parent_document_retrieval.md](retrieval/parent_document_retrieval.md) | 0.900 | 0.963 | 0.975 | 0.946 |
| `hybrid_retrieval` | [hybrid_retrieval.md](retrieval/hybrid_retrieval.md) | 0.863 | 0.975 | 0.912 | 0.917 |

### Mejor técnica del directorio

| Directorio | Técnica ganadora | Promedio |
|---|---|---:|
| `retrieval` | `parent_document_retrieval` | 0.946 |


