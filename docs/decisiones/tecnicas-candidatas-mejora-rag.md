# Técnicas candidatas para mejorar el RAG normativo

Este documento consolida las técnicas candidatas para mejorar el pipeline RAG normativo basado en LangGraph. La decisión no es implementar todas las técnicas a la vez, sino evaluarlas incrementalmente sobre el baseline actual y seleccionar solo aquellas que demuestren mejora medible para consultas SG-SST.

## Diagrama de flujo general

                     ┌───────────────────────┐
                     │ Pregunta del usuario  │
                     └───────────┬───────────┘
                                 │
                    ETAPA 4      │ contexto empresarial
                                 ↓
                     ┌───────────────────────┐
                     │ Perfil / restricciones│
                     └───────────┬───────────┘
                                 │
                    ETAPA 2      ↓
               ┌─────────────────────────────┐
               │ Comprensión de la consulta  │
               │ - Query Rewriting           │
               │ - RAG-Fusion / Multi-Query  │
               │ - LLM-Based Query Expansion │
               └──────────────┬──────────────┘
                              │
                    ETAPA 3   ↓
               ┌─────────────────────────────┐
               │ Retrieval                   │
               │ - Hybrid Retrieval          │
               │ - Parent/Child Retrieval    │
               └──────────────┬──────────────┘
                              ↓
               ┌─────────────────────────────┐
               │ Reranking                   │
               └──────────────┬──────────────┘
                              │
                    ETAPA 5   ↓
               ┌─────────────────────────────┐
               │ Relevance Grading           │
               └──────────────┬──────────────┘
                         ┌────┴─────┐
                         │          │
                    relevante   irrelevante
                         │          │
                         ↓          └──→ rewrite/retry/fallback
               ┌─────────────────────────────┐
               │ Answerability Gate          │
               └──────────────┬──────────────┘
                         ┌────┴─────┐
                         │          │
                    suficiente  insuficiente
                         │          │
                         ↓          └──→ retry/fallback
                     generación
                         ↓
               ┌─────────────────────────────┐
               │ Citation Verification       │
               └──────────────┬──────────────┘
                              ↓
                           respuesta

## Decisión

Las mejoras se evaluarán como experimentos controlados por dimensión:

1. comprensión de la consulta;
2. calidad de recuperación;
3. incorporación del contexto empresarial;
4. validación y control de la respuesta.

Cada experimento debe mantener constantes, cuando sea posible, el corpus, dataset de evaluación, modelo generador, temperatura, prompt y `top-k` final entregado al LLM. Cambiar varios componentes al mismo tiempo dificultaría atribuir mejoras o regresiones.

## Baseline actual y brechas

El baseline actual del agente de consulta normativa usa **dense vector retrieval sobre Chroma** dentro del grafo LangGraph. Recupera documentos por similitud de embeddings y luego construye contexto y referencias para la respuesta.

Brechas relevantes antes de experimentar:

| Aspecto | Estado actual | Implicación |
|---|---|---|
| Recuperación | Búsqueda vectorial densa sobre Chroma. | Es el baseline; hybrid retrieval, reranking o filtros son mejoras separadas. |
| Evidencia | El criterio operativo es `bool(documents)`. | Recuperar al menos un documento no prueba relevancia ni suficiencia. |
| Señales de Chroma | `RetrievedDocument` conserva texto y metadata, pero no preserva `ids` ni `distances`. | No se puede auditar calidad de retrieval, calibrar umbrales ni comparar rankings sin instrumentación previa. |
| Contexto y referencias | Existe formateo de contexto y deduplicación de referencias. | `build_references()` solo evita referencias repetidas; no verifica que las citas respalden afirmaciones. |
| Metadata | La metadata se usa para construir contexto y referencias. | Metadata en el prompt no equivale a metadata-aware retrieval; todavía no filtra candidatos durante la búsqueda. |

Por esto, el primer paso no debe ser agregar una técnica avanzada, sino **instrumentar el retrieval**: conservar identificadores, distancias/scores disponibles, posición en ranking, consulta usada, documentos finales y resultado de evaluación.

## Técnicas candidatas por dimensión

### Comparación compacta

| Dimensión | Técnica candidata | Qué hace | Ubicación en LangGraph | Riesgo / nota de evaluación |
|---|---|---|---|---|
| Comprensión de consulta | Query Rewriting | Reformula la pregunta para acercarla al vocabulario normativo sin perder la intención original. | Antes de `retrieve`; conservar `original_question` y `retrieval_query`. | Puede cambiar el alcance de la consulta; evaluar con pares donde la intención original sea clara. |
| Comprensión de consulta | RAG-Fusion / Multi-Query + RRF | Genera varias reformulaciones, recupera con cada una y fusiona rankings. | Antes y dentro de `retrieve`: `generate_queries` → búsquedas múltiples → `fuse_results`. | Aumenta latencia y puede introducir ruido; medir recall y precisión del contexto final. |
| Comprensión de consulta | LLM-Based Query Expansion | Amplía la consulta original agregando términos, conceptos o expresiones semánticamente relacionadas para reducir el vocabulary mismatch y aumentar la probabilidad de recuperar documentos relevantes. | Antes del nodo de recuperación (retrieve), transformando la consulta original en una consulta enriquecida que será enviada al retriever. | Puede introducir topic drift o términos no pertinentes si el LLM expande demasiado la consulta. Debe evaluarse manteniendo constante el mismo retriever, corpus y top-k, comparando métricas como Recall@k, MRR o nDCG. |
| Calidad de recuperación | Hybrid Retrieval + RRF | Combina recuperación densa con búsqueda léxica/sparse para capturar semántica y coincidencias exactas. | Dentro de `retrieve`, agregando una rama sparse a la rama dense actual. | Requiere índice/mecanismo adicional; medir si mejora referencias exactas como resolución, artículo, numeral o sigla. |
| Calidad de recuperación | Retrieve-Many + Reranking | Recupera más candidatos y reordena con un reranker antes de seleccionar el `top-k` final. | Después de retrieval/normalización y antes de `assess_evidence`. | Añade costo; mantener separadas las señales de distancia Chroma y score del reranker. |
| Calidad de recuperación | Parent-Document / Small-to-Big Retrieval | Busca en fragmentos pequeños y recupera una unidad normativa mayor asociada. | Durante retrieval: `child` recuperado → resolver `parent_id` → contexto final. | Un padre demasiado amplio mete ruido; evaluar nivel óptimo: artículo, parágrafo, sección o tabla. |
| Contexto empresarial | Metadata-Aware Retrieval | Convierte atributos estructurados de empresa en filtros aplicados durante retrieval. | Antes/dentro de `retrieve`, construyendo filtros `where` para Chroma cuando aplique. | Filtros incompletos o demasiado estrictos pueden excluir evidencia; no inferir atributos ausentes. |
| Contexto empresarial | Self-Query Retrieval | Usa un LLM para separar consulta semántica y filtros de metadata desde lenguaje natural. | Antes de `retrieve`: `self_query` → `semantic_query` + `metadata_filters`. | Solo útil si el esquema de metadata soporta esos filtros; validar salida estructurada contra un esquema cerrado. |
| Contexto empresarial | Context-Aware Query Rewriting | Reformula la consulta usando perfil empresarial o historial relevante. | Antes de `retrieve`, después de disponer del perfil/contexto. | Puede contaminar la consulta con contexto irrelevante; comparar contra filtros estructurados simples. |
| Validación y control | Retrieval Relevance Grading / CRAG | Evalúa si los documentos recuperados son relevantes antes de generar respuesta. | Sustituye o amplía `assess_evidence` con rutas condicionales. | Un grader también falla; exigir salida estructurada y límite de reintentos. |
| Validación y control | Answerability / Sufficient-Context Gate | Determina si el contexto contiene evidencia suficiente para responder completa o parcialmente. | Después de recuperación/reranking y antes de generación. | Puede generar abstenciones excesivas; evaluar casos respondibles, parcialmente respondibles y no respondibles. |
| Validación y control | Self-Refine | Genera feedback sobre la respuesta inicial y la refina para producir una salida potencialmente mejor. | Después de `generate_answer` | Aumenta costo y el modelo puede producir feedback incorrecto.|

### Relevancia para SG-SST

- **Comprensión de consulta:** los usuarios pueden preguntar con lenguaje informal, incompleto o mezclando obligaciones, plazos y documentos.
- **Calidad de recuperación:** el dominio normativo requiere tanto similitud semántica como coincidencias exactas de artículos, resoluciones, numerales y conceptos jurídicos.
- **Contexto empresarial:** la aplicabilidad puede depender de tamaño de empresa, número de trabajadores, nivel de riesgo y condiciones específicas.
- **Validación y control:** una respuesta normativa debe abstenerse o señalar insuficiencia cuando la evidencia no respalda la afirmación.

## Orden recomendado de experimentación

0. **Instrumentación del retrieval.** Preservar `ids`, `distances`/scores disponibles, ranking, consulta usada, filtros aplicados y documentos finales. Sin esto no hay línea base auditable.
1. **Relevance Grading.** Reemplazar el criterio `bool(documents)` por una evaluación explícita de relevancia.
2. **Query Rewriting.** Medir si reduce la brecha entre lenguaje del usuario y vocabulario normativo.
3. **Hybrid Retrieval.** Evaluar mejora en consultas con referencias exactas: normas, artículos, numerales, siglas.
4. **Retrieve-Many + Reranking.** Separar recall inicial de precisión final del contexto.
5. **Parent-Document Retrieval.** Evaluar si mejora trazabilidad y suficiencia sin introducir demasiado ruido.
6. **RAG-Fusion o LLM-Based Query Expansion.** Probar solo si el dataset muestra fallos por consultas ambiguas, multi-formulación o compuestas.
7. **Contexto empresarial.** Empezar por filtros determinísticos con metadata estructurada; evaluar Self-Query solo si el usuario expresa restricciones en lenguaje natural no capturadas en perfil.
8. **Answerability y Citation Verification.** Añadir controles finales cuando ya exista retrieval suficientemente estable.

## Criterios de evaluación

* **Evaluación con ARES:** todas las técnicas y configuraciones experimentales se evaluarán utilizando el framework **ARES**, manteniendo el mismo conjunto de evaluación y las mismas condiciones experimentales.
* **Context Relevance:** mide qué tan relevante es el contexto recuperado respecto a la consulta planteada.
* **Answer Faithfulness:** evalúa si la respuesta generada está respaldada por la información contenida en el contexto recuperado.
* **Answer Relevance:** determina qué tan pertinente es la respuesta generada respecto a la pregunta del usuario.
* **Comparación experimental:** cada técnica se evaluará individualmente respecto al **baseline** de la etapa correspondiente. Posteriormente podrán evaluarse combinaciones entre las técnicas que hayan mostrado mejoras.
* **Ablación:** los cambios deben introducirse de forma controlada para poder atribuir las variaciones en las métricas de ARES a una técnica específica y evitar evaluar múltiples modificaciones simultáneamente sin conocer su contribución individual.

## Técnicas no prioritarias

Estas técnicas pueden aparecer en revisión bibliográfica o exploración futura, pero no son prioridad inicial:

- **HyDE:** puede mejorar recuperación densa generando un documento hipotético, pero en normativa puede inventar premisas y sesgar el retrieval.
- **Query Expansion:** útil con vocabulario controlado SG-SST; expansión libre por LLM puede aumentar ruido.
- **Contextual Compression:** ayuda a reducir tokens, pero puede eliminar excepciones, condiciones o plazos jurídicamente importantes.
- **Query Classification:** solo aporta valor si existen rutas realmente distintas; sin rutas diferenciadas añade complejidad accidental.
- **Conversational Query Rewriting:** relevante para conversaciones multi-turn; menos prioritario si la evaluación inicial es single-turn.

## Referencias mínimas

- Chroma. *Query and Get*. https://docs.trychroma.com/docs/querying-collections/query-and-get
- Chroma. *Metadata Filtering*. https://docs.trychroma.com/docs/querying-collections/metadata-filtering
- LangChain. *Build a custom RAG agent with LangGraph*. https://docs.langchain.com/oss/python/langgraph/agentic-rag
- Ma, X., Gong, Y., He, P., Zhao, H., & Duan, N. (2023). *Query Rewriting for Retrieval-Augmented Large Language Models*. https://arxiv.org/abs/2305.14283
- Gao, L. et al. (2023). *Precise Zero-Shot Dense Retrieval without Relevance Labels*. https://aclanthology.org/2023.acl-long.99/
- Nogueira, R., & Cho, K. (2019). *Passage Re-ranking with BERT*. https://arxiv.org/abs/1901.04085
- Yan, S.-Q., Gu, J.-C., Zhu, Y., & Ling, Z.-H. (2024). *Corrective Retrieval Augmented Generation*. https://arxiv.org/abs/2401.15884
- Joren, H. et al. (2024). *Sufficient Context: A New Lens on Retrieval Augmented Generation Systems*. https://arxiv.org/abs/2411.06037





sef-refine

Dhuliawala, S., et al. (2024). Chain-of-Verification Reduces Hallucination in Large Language Models. Findings of ACL 2024, pp. 3563–3578. DOI: 10.18653/v1/2024.findings-acl.212.
https://aclanthology.org/2024.findings-acl.212/