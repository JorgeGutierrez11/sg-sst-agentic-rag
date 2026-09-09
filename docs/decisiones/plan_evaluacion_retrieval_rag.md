# Plan de evaluación de Retrieval para el RAG SG-SST

## Objetivo

Comparar configuraciones de recuperación ya disponibles en el sistema y seleccionar la mejor bajo las métricas de ARES:

- Context Relevance.
- Answer Faithfulness.
- Answer Relevance.

La comparación debe mantener fijo el corpus, las preguntas, el chunking, los embeddings, el LLM, el prompt, la temperatura y el `final_top_k`.

---

## R1 — Hybrid Retrieval: Dense + BM25 + RRF

```text
Query
  ├── Chroma / Dense ──┐
  │                    ├── RRF
  └── BM25 / Sparse ───┘
                         ↓
                      Top-k
                         ↓
                    Generación
```

### Hipótesis

Combinar recuperación semántica y léxica permitirá recuperar mejor evidencia normativa que Dense Retrieval por sí solo.

### Justificación

Dense Retrieval captura similitud semántica, mientras que BM25 es especialmente útil para coincidencias exactas frecuentes en normativa, por ejemplo:

- nombres de normas;
- números de resolución o decreto;
- artículos;
- códigos CIIU;
- términos como COPASST o SG-SST.

RRF permite fusionar ambos rankings sin comparar directamente escalas incompatibles como la similitud de Chroma y el score de BM25.

### Decisión

```python
HYBRID_CANDIDATE_TOP_K = 40
HYBRID_RRF_K = 60
```

R1 recupera 40 candidatos por cada retriever, fusiona los rankings con RRF y entrega 8 documentos finales al generador.

---

## R2 — Hybrid Retrieval + Cross-Encoder Reranking

```text
Query
  ├── Chroma / Dense ──┐
  │                    ├── RRF
  └── BM25 / Sparse ───┘
                         ↓
                  Candidate pool
                         ↓
                  Cross-Encoder
                         ↓
                      Top-k
                         ↓
                    Generación
```

### Hipótesis

El retrieval híbrido aumenta cobertura y el Cross-Encoder mejora la selección de los documentos que finalmente llegan al generador.

### Justificación

El retriever debe priorizar cobertura. El Cross-Encoder puede evaluar con mayor precisión cada par:

```text
(query, documento)
```

Este enfoque evita pasar demasiados documentos al LLM y reduce ruido en el contexto final.

### Decisión

```python
HYBRID_CANDIDATE_TOP_K = 40
HYBRID_RRF_K = 60
RERANKER_CANDIDATE_POOL_SIZE = 40
RERANKER_FINAL_TOP_K = 8
```

R2 conserva 40 candidatos después de RRF, aplica Cross-Encoder sobre esos 40 y reduce a 8 documentos finales.

El corte a 8 debe ocurrir después del Cross-Encoder, no antes.

---

## R3 — Hybrid Retrieval + Cross-Encoder + Parent-Child

```text
Query
  ├── Chroma / Dense ──┐
  │                    ├── RRF
  └── BM25 / Sparse ───┘
                         ↓
                  Candidate pool
                         ↓
                  Cross-Encoder
                         ↓
                mejores child chunks
                         ↓
                 Parent expansion
                         ↓
                  deduplicación
                         ↓
                     contexto
                         ↓
                   Generación
```

### Hipótesis

Después de seleccionar los child chunks más relevantes, expandirlos hacia su unidad padre entregará al generador contexto normativo más completo.

### Justificación

En documentos jurídicos, un fragmento recuperado puede depender de encabezados, artículos, numerales, parágrafos, excepciones o tablas.

Parent-Child permite separar:

```text
unidad óptima para buscar
≠
unidad óptima para generar
```

### Decisión

```python
HYBRID_CANDIDATE_TOP_K = 40
HYBRID_RRF_K = 60
RERANKER_CANDIDATE_POOL_SIZE = 40
RERANKER_FINAL_TOP_K = 8
```

R3 usa el mismo flujo de R2 hasta el Cross-Encoder. Luego expande los 8 mejores child chunks hacia sus parents y deduplica el contexto.

No se debe expandir a parents antes del Cross-Encoder.

---

## Configuraciones a evaluar

| ID | Configuración | Qué mide |
|---|---|---|
| R1 | Dense + BM25 + RRF | Aporte de Hybrid Retrieval |
| R2 | Dense + BM25 + RRF + Cross-Encoder | Aporte del reranking |
| R3 | Dense + BM25 + RRF + Cross-Encoder + Parent-Child | Aporte de Small-to-Big Retrieval |

---


## Fuentes

1. Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). **Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods**. SIGIR 2009.  
   https://doi.org/10.1145/1571941.1572114

2. Elasticsearch. **Reciprocal rank fusion API**.  
   https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion

3. Sentence Transformers. **Retrieve & Re-Rank — Cross-Encoder**.  
   https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html

4. Pinecone. **Rerankers and Two-Stage Retrieval**.  
   https://www.pinecone.io/learn/series/rag/rerankers/
