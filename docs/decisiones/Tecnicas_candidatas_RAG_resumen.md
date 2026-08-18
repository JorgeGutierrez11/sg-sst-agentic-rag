# Técnicas candidatas para la mejora del pipeline RAG

## Ubicación de las técnicas dentro del pipeline

Una arquitectura ampliada podría adoptar la siguiente estructura conceptual:

```text
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
               │ - Query Decomposition       │
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
```

---


## Etapa 1. Implementación base del sistema RAG

Fase ya realizada.

El sistema actual utiliza **Dense Retrieval** mediante búsqueda vectorial sobre Chroma. Esta implementación se considera el **baseline** sobre el cual se evaluarán las mejoras posteriores.

---

## Etapa 2. Mejora en la comprensión de la consulta

El objetivo de esta etapa es mejorar la forma en que la consulta del usuario es interpretada antes de realizar la recuperación.

### 1. Query Rewriting

Reformula la consulta original para reducir ruido, corregir ambigüedades y aproximarla al vocabulario utilizado en el corpus normativo.

**¿Por qué evaluarla?**

Puede mejorar la recuperación cuando el usuario utiliza lenguaje informal, expresiones imprecisas o términos diferentes a los presentes en la normativa.

**Referencia:**  
Ma, X., Gong, Y., He, P., Zhao, H., & Duan, N. (2023). *Query Rewriting for Retrieval-Augmented Large Language Models*.  
https://arxiv.org/abs/2305.14283

---

### 2. RAG-Fusion / Multi-Query Retrieval

Genera varias formulaciones alternativas de una misma consulta, realiza una búsqueda para cada una y posteriormente combina los resultados obtenidos.

La combinación puede realizarse mediante **Reciprocal Rank Fusion (RRF)**.

**¿Por qué evaluarla?**

Puede aumentar la cobertura de recuperación cuando una misma necesidad de información puede expresarse de distintas formas.

**Referencia:**  
Rackauckas, Z. (2024). *RAG-Fusion: a New Take on Retrieval-Augmented Generation*.  
https://arxiv.org/abs/2402.03367

---

### 3. Query Decomposition

Divide una consulta compleja en varias subconsultas más simples que pueden resolverse de forma independiente.

Ejemplo:

```text
¿Qué debe hacer una empresa para implementar el SG-SST y qué debe hacer
cuando ocurre un accidente laboral?
```

Puede dividirse en:

```text
1. Requisitos para implementar el SG-SST.
2. Obligaciones frente a accidentes laborales.
```

**¿Por qué evaluarla?**

Puede mejorar el desempeño ante consultas que contienen varias preguntas, condiciones u obligaciones normativas al mismo tiempo.

**Referencia:**  
Ammann, P. J. L. (2025). *Question Decomposition for Retrieval-Augmented Generation*. ACL Student Research Workshop.  
https://aclanthology.org/2025.acl-srw.32/

---

## Etapa 3. Mejora en la recuperación de la información

El objetivo de esta etapa es mejorar la calidad de los fragmentos recuperados antes de entregarlos al modelo generador.

### 1. Hybrid Retrieval

Combina dos mecanismos de recuperación:

- **Dense Retrieval:** búsqueda semántica mediante embeddings.
- **Sparse Retrieval:** búsqueda léxica mediante coincidencia de términos.

Los rankings producidos pueden combinarse mediante técnicas como **Reciprocal Rank Fusion (RRF)**.

**¿Por qué evaluarla?**

El corpus normativo contiene tanto relaciones semánticas como términos que requieren coincidencia exacta, por ejemplo:

- números de artículos;
- nombres de resoluciones;
- términos jurídicos;
- siglas;
- conceptos específicos del SG-SST.

La combinación de señales semánticas y léxicas puede resultar más robusta que utilizar únicamente búsqueda vectorial.

**Referencias:**  
Meng, S. et al. (2026). *Sifei at SemEval-2026 Task 8: Hybrid Retrieval and Query Rewriting for Multi-Turn RAG*.  
https://aclanthology.org/2026.semeval-1.32/

Raya-Rios, V. et al. (2026). *IIMAS-RAG at SemEval-2026 Task 8*.  
https://aclanthology.org/2026.semeval-1.345/

---

### 2. Reranking

Recupera inicialmente un conjunto amplio de fragmentos y posteriormente utiliza un modelo adicional para volver a clasificarlos según su relevancia respecto a la consulta.

Flujo conceptual:

```text
Recuperación inicial
        ↓
Lista amplia de candidatos
        ↓
Reranker
        ↓
Fragmentos más relevantes
```

**¿Por qué evaluarla?**

La búsqueda vectorial puede recuperar documentos semánticamente cercanos pero poco útiles para responder la consulta. El reranking permite realizar una segunda evaluación más precisa antes de construir el contexto final.

**Referencia:**  
Nogueira, R., & Cho, K. (2019). *Passage Re-ranking with BERT*.  
https://arxiv.org/abs/1901.04085

---

### 3. Parent-Document Retrieval

Utiliza fragmentos pequeños para realizar la búsqueda, pero recupera posteriormente una unidad documental más amplia asociada al resultado encontrado.

En el corpus normativo puede utilizarse una estructura como:

```text
Artículo completo → Parent

Numeral / inciso / fragmento → Child
```

**¿Por qué evaluarla?**

Permite mantener precisión durante la búsqueda sin perder el contexto completo del artículo o disposición normativa.

**Referencia:**  
LangChain. *Small-to-big retrieval / Parent document retrieval*.  
https://docs.langchain.com/oss/python/integrations/document_loaders/docugami

---

## Etapa 4. Incorporación del contexto empresarial

El objetivo de esta etapa es utilizar información de la empresa para recuperar normativa más pertinente a su situación.

### 1. Metadata-Aware Retrieval

Utiliza características estructuradas de la empresa como filtros durante la recuperación.

Ejemplos:

```text
Número de trabajadores
Nivel de riesgo
Tamaño de empresa
Tipo de organización
```

**¿Por qué evaluarla?**

Permite reducir documentos que no son aplicables al perfil empresarial antes de que lleguen al modelo generador.

**Referencia:**  
Chroma. *Metadata Filtering*.  
https://docs.trychroma.com/docs/querying-collections/metadata-filtering

---

### 2. Self-Query Retrieval

Utiliza un modelo de lenguaje para identificar dentro de la consulta:

- la intención semántica;
- las restricciones que pueden convertirse en filtros de metadata.

Ejemplo:

```text
"Soy una empresa de 8 trabajadores de riesgo I.
¿Qué estándares debo cumplir?"
```

Puede interpretarse como:

```text
Consulta:
estándares mínimos SG-SST

Filtros:
trabajadores <= 10
riesgo = I
```

**¿Por qué evaluarla?**

Permite convertir información empresarial expresada en lenguaje natural en restricciones utilizables por el sistema de recuperación.

**Referencia:**  
Požarnik Vavken, M., Ogrinc, M., Eftimov, T., & Koroušić Seljak, B. (2026). *Evaluation of LLMs in retrieving food and nutritional context for RAG systems*.  
https://arxiv.org/abs/2603.09704

---

### 3. Context-Aware Query Rewriting

Reformula la consulta utilizando información adicional del usuario, como su perfil empresarial o el contexto de la conversación.

Ejemplo:

```text
Pregunta:
¿Qué documentos debo tener?

Perfil:
Microempresa
8 trabajadores
Riesgo I
```

Consulta reformulada:

```text
Documentación del SG-SST aplicable a una microempresa
de ocho trabajadores clasificada en riesgo I.
```

**¿Por qué evaluarla?**

Permite que el contexto empresarial afecte directamente la consulta utilizada para recuperar información y no únicamente la generación final.

**Referencia:**  
Wigger, F. et al. (2026). *Contextual Query Rewriting and Dense Retrieval for Multi-Turn RAG*.  
https://aclanthology.org/2026.semeval-1.227/

---

## Etapa 5. Validación y control de la respuesta

El objetivo de esta etapa es evitar que el sistema genere respuestas utilizando evidencia irrelevante, incompleta o incorrectamente citada.

### 1. Retrieval Relevance Grading

Evalúa si los documentos recuperados son realmente relevantes para la consulta antes de generar una respuesta.

La decisión deja de ser simplemente:

```text
¿Se recuperaron documentos?
```

y pasa a ser:

```text
¿Los documentos recuperados son relevantes para responder?
```

Si la evidencia no es relevante, el sistema puede reformular la consulta, repetir la búsqueda o aplicar un fallback.

**¿Por qué evaluarla?**

Evita considerar como evidencia válida cualquier documento devuelto por el sistema de recuperación.

**Referencias:**  
Yan, S.-Q., Gu, J.-C., Zhu, Y., & Ling, Z.-H. (2024). *Corrective Retrieval Augmented Generation*.  
https://arxiv.org/abs/2401.15884

LangChain. *Build a custom RAG agent with LangGraph*.  
https://docs.langchain.com/oss/python/langgraph/agentic-rag

---

### 2. Answerability / Sufficient Context

Evalúa si los documentos recuperados contienen información suficiente para responder la consulta.

Un documento puede ser relevante pero no contener toda la información necesaria.

Ejemplo:

```text
Pregunta:
¿Qué obligación debe cumplir el empleador y en qué plazo?

Contexto:
Contiene la obligación,
pero no contiene el plazo.
```

En este caso la información es relevante, pero insuficiente para responder completamente.

**¿Por qué evaluarla?**

Permite distinguir entre evidencia relacionada y evidencia realmente suficiente para generar una respuesta fundamentada.

**Referencia:**  
Joren, H. et al. (2024). *Sufficient Context: A New Lens on Retrieval Augmented Generation Systems*.  
https://arxiv.org/abs/2411.06037

---

### 3. Citation Verification

Verifica que las afirmaciones realizadas en la respuesta estén realmente respaldadas por los fragmentos normativos citados.

El proceso puede evaluar cada afirmación de forma independiente:

```text
Afirmación 1 → Fuente citada → ¿la respalda?
Afirmación 2 → Fuente citada → ¿la respalda?
Afirmación 3 → Fuente citada → ¿la respalda?
```

**¿Por qué evaluarla?**

La presencia de una referencia no garantiza que esa referencia respalde realmente la afirmación generada por el modelo.

**Referencia:**  
Qian, H. et al. (2025). *VeriCite: Towards Reliable Citations in Retrieval-Augmented Generation via Rigorous Verification*.  
https://arxiv.org/abs/2510.11394

---

# Tabla de técnicas candidatas

> Las tres técnicas de cada etapa son **alternativas candidatas para evaluación experimental**. No se plantea implementar necesariamente las tres en la arquitectura final. Los resultados obtenidos durante la Fase 4 permitirán seleccionar la técnica o combinación de técnicas que presente mejor desempeño para cada dimensión.

| **Dimensión** | **Técnica 1** | **Técnica 2** | **Técnica 3** |
|---|---|---|---|
| **Comprensión de consultas** | **Query Rewriting:** reformula la consulta para aproximarla al vocabulario y estructura del corpus normativo. | **RAG-Fusion / Multi-Query:** genera varias formulaciones de la consulta, realiza múltiples búsquedas y fusiona los resultados. | **Query Decomposition:** divide consultas complejas en subconsultas más simples para recuperar evidencia de cada componente. |
| **Recuperación** | **Hybrid Retrieval:** combina búsqueda vectorial densa con recuperación léxica para aprovechar señales semánticas y coincidencias exactas. | **Reranking:** reordena un conjunto inicial de candidatos mediante un modelo adicional de relevancia. | **Parent-Document Retrieval:** busca utilizando fragmentos pequeños y recupera posteriormente una unidad normativa más amplia para conservar contexto. |
| **Contexto empresarial** | **Metadata-Aware Retrieval:** utiliza características estructuradas de la empresa como filtros durante la recuperación. | **Self-Query Retrieval:** identifica automáticamente en la consulta restricciones que pueden convertirse en filtros de metadata. | **Context-Aware Query Rewriting:** reformula la consulta utilizando el perfil empresarial o contexto relevante del usuario. |
| **Validación y control** | **Retrieval Relevance Grading:** determina si los documentos recuperados son realmente relevantes antes de generar la respuesta. | **Answerability / Sufficient Context:** verifica si la evidencia disponible es suficiente para responder total o parcialmente la consulta. | **Citation Verification:** comprueba que las afirmaciones generadas estén respaldadas por los fragmentos normativos citados. |

---

# Técnicas adicionales documentadas

Estas técnicas pueden mantenerse dentro de la revisión bibliográfica, pero no forman parte de las tres candidatas principales seleccionadas para cada dimensión.

### HyDE

Genera un documento hipotético a partir de la consulta y utiliza su embedding para realizar retrieval.

**Referencia:**  
Gao, L. et al. (2023). *Precise Zero-Shot Dense Retrieval without Relevance Labels*.  
https://aclanthology.org/2023.acl-long.99/

### Query Expansion

Amplía la consulta con términos relacionados, sinónimos o vocabulario del dominio para aumentar la cobertura de recuperación.

### Conversational Query Rewriting

Reformula consultas dependientes de turnos anteriores de una conversación para convertirlas en preguntas autónomas.

**Referencia:**  
Elgohary, A., Peskov, D., & Boyd-Graber, J. (2019). *Can You Unpack That? Learning to Rewrite Questions-in-Context*.  
https://aclanthology.org/D19-1605/

### Contextual Compression

Reduce el contenido de los fragmentos recuperados conservando únicamente las partes consideradas relevantes para responder la consulta.

### Query Classification

Clasifica la consulta según su intención o características para decidir qué estrategia de recuperación o flujo utilizar.
