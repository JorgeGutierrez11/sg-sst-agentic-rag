# Resultados comparativos de las técnicas evaluadas con ARES

**Configuración indicada en los archivos:** 80 consultas por técnica; juez `deepseek-v4-flash`; conjunto de referencia de 200 ejemplos.

**Criterio de comparación:** promedio aritmético de las tres estimaciones `ARES Prediction` consignadas en los archivos. No se utiliza la precisión del juez para clasificar las técnicas.

## Comprensión de consultas

| Técnica | Relevancia del contexto | Fidelidad de la respuesta | Relevancia de la respuesta | Promedio |
|---|---:|---:|---:|---:|
| **Query Expansion (seleccionada)** | 0.9500 | 1.0000 | 0.9925 | **0.9808** |
| Multi-Query Retrieval | 0.8475 | 1.0000 | 0.9625 | 0.9367 |
| Query Rewriting | 0.8025 | 1.0000 | 0.8925 | 0.8983 |

## Recuperación de información

| Técnica | Relevancia del contexto | Fidelidad de la respuesta | Relevancia de la respuesta | Promedio |
|---|---:|---:|---:|---:|
| **R3 — Hybrid + Reranking + Parent-Document (seleccionada)** | 0.9550 | 1.0000 | 1.0000 | **0.9850** |
| R2 — Hybrid + Reranking | 0.9400 | 1.0000 | 0.9875 | 0.9758 |
| R1 — Hybrid Retrieval | 0.9300 | 0.9800 | 0.9400 | 0.9500 |

## Contexto empresarial

| Técnica | Relevancia del contexto | Fidelidad de la respuesta | Relevancia de la respuesta | Promedio |
|---|---:|---:|---:|---:|
| **Retrieval-Based Long-Term Memory (seleccionada)** | 0.9575 | 1.0000 | 0.9750 | **0.9775** |
| Full Conversation Memory | 0.9475 | 1.0000 | 0.9800 | 0.9758 |
| Summarization-Based Memory | 0.8525 | 1.0000 | 0.9900 | 0.9475 |

## Validación de respuestas

| Técnica | Relevancia del contexto | Fidelidad de la respuesta | Relevancia de la respuesta | Promedio |
|---|---:|---:|---:|---:|
| **Retrieval Relevance Grading (seleccionada)** | 0.8550 | 1.0000 | 0.9450 | **0.9333** |
| Sufficient-Context Gate | 0.8825 | 1.0000 | 0.8875 | 0.9233 |
| Self-Refine | 0.8100 | 0.8220 | 0.9675 | 0.8665 |

## Técnicas seleccionadas

| Dimensión | Técnica seleccionada | Promedio |
|---|---|---:|
| Comprensión de consultas | **Query Expansion** | 0.9808 |
| Recuperación de información | **R3 — Hybrid + Reranking + Parent-Document** | 0.9850 |
| Contexto empresarial | **Retrieval-Based Long-Term Memory** | 0.9775 |
| Validación de respuestas | **Retrieval Relevance Grading** | 0.9333 |

