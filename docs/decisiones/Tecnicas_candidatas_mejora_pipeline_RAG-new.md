# Técnicas candidatas para la mejora del pipeline RAG normativo

## 1. Etapas a mejorar: 

1. **Etapa 2 — Comprensión de la consulta.**
2. **Etapa 3 — Recuperación de la información.**
3. **Etapa 4 — Incorporación del contexto empresarial.**
4. **Etapa 5 — Validación y control de la respuesta.**


---

# 2. Pipeline RAG base

La implementación actual sigue, de forma simplificada, el siguiente flujo:

![Texto alternativo](/../proyecto_rag/data/images/base_rag_graph.png "Grafo del pipeline RAG base")

Por tanto, el pipeline diferencia entre **cero documentos** y **uno o más documentos**, pero todavía no comprueba si esos documentos son relevantes ni si contienen evidencia suficiente para responder la pregunta.

> **Retrieval actual:** la implementación utiliza únicamente **búsqueda vectorial densa (Dense Retrieval)** sobre una colección persistente de Chroma. La consulta se compara con los embeddings almacenados y se recuperan los `top-k` vecinos más cercanos. Por tanto, **Dense Retrieval constituye el baseline de la Fase 4**. Chroma documenta `query()` como una operación de búsqueda de vecinos cercanos sobre embeddings densos.
>


Referencia: [Chroma — Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)

## 2.1. Implicaciones del `formatting.py` actual

El módulo de formateo permite precisar varios aspectos del baseline que afectan directamente las técnicas candidatas.

### 2.1.1. La normalización descarta la señal de similitud de Chroma

Actualmente `recovered_documents()` solo conserva:

```python
RetrievedDocument(
    document=str(document),
    metadata=metadata_at(metadatas, index),
)
```

Aunque un resultado de `collection.query()` puede incluir campos como `ids`, `documents`, `metadatas` y `distances`, el normalizador actual solo consume `documents` y `metadatas`. Por tanto, después de `normalize_documents` el grafo ya no dispone de la distancia de similitud asociada a cada resultado.

Esto tiene tres consecuencias:

1. no puede registrarse la distribución de distancias para analizar la calidad del retrieval;
2. no puede experimentarse con un filtro o umbral calibrado de similitud sin modificar `RetrievedDocument`;
3. un reranker o evidence grader posterior no puede utilizar esa señal como feature auxiliar.

Una evolución razonable del modelo sería conservar, al menos de forma opcional:

```python
class RetrievedDocument:
    document: str
    metadata: dict[str, Any]
    id: str | None
    distance: float | None
```

La distancia **no debe interpretarse automáticamente como evidencia suficiente** ni sustituir el relevance grader. Su significado y un eventual umbral dependen de la función de distancia, el modelo de embeddings y la distribución observada en el dataset, por lo que cualquier threshold debe calibrarse experimentalmente.

Referencia: [Chroma — Query collection](https://docs.trychroma.com/reference/chroma-api/record/query-collection)

### 2.1.2. La metadata actual contextualiza la generación, pero no filtra el retrieval

`metadata_context()` inserta en el contexto entregado al LLM información como:

```text
Tipo normativo
Año
Capítulo
Artículo
Parágrafo
Numeral
Literal
ID padre
Inicio
Fin
```

Esto mejora trazabilidad y facilita generar referencias, pero ocurre **después de recuperar los documentos**. En el pipeline actual no hay evidencia de que estos campos intervengan en la selección inicial de candidatos.

Por ello debe diferenciarse:

```text
Metadata en el prompt
    ≠
Metadata-Aware Retrieval
```

La técnica **Metadata-Aware Retrieval** de la Etapa 4 sigue siendo una mejora independiente: utilizaría metadata durante `collection.query(..., where=...)` para restringir o condicionar los candidatos antes de construir el contexto.

Chroma permite aplicar filtros de metadata mediante `where` durante `query`.

Referencia: [Chroma — Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)

### 2.1.3. Parte de la metadata técnica puede convertirse en ruido para el generador

El contexto actual expone también campos puramente técnicos:

```text
ID padre
Inicio
Fin
table_key
linked_placeholder
oversized_row
```

Estos campos pueden ser útiles para trazabilidad interna, depuración o recuperación padre-hijo, pero no necesariamente aportan información semántica al LLM que redacta la respuesta normativa.

Conviene separar conceptualmente:

```text
metadata_retrieval
metadata_trace
metadata_generation
```

Por ejemplo:

- `parent_id` puede ser necesario para **Parent-Document Retrieval**;
- `article`, `paragraph`, `source_stem` son útiles para **generación y citación**;
- `start_char` y `end_char` pueden conservarse para **trazabilidad técnica**, sin necesidad de enviarlos siempre al LLM.

Esto no obliga a introducir Contextual Compression. Primero debe reducirse de manera determinística la metadata que no tiene utilidad para generación.

### 2.1.4. Las referencias deduplicadas no constituyen verificación de citas

`build_references()` evita repetir una misma referencia:

```python
if reference not in references:
    references.append(reference)
```

Esto es correcto como mecanismo de presentación, pero no verifica que una afirmación generada esté respaldada por dicha referencia. Por tanto, **Claim-Level Citation Verification sigue siendo una técnica nueva y no una funcionalidad ya cubierta por `build_references()`**.

### 2.1.5. El fallback vacío depende de una invariancia del grafo

El manejo de contexto vacío fue retirado de `build_context()`:

```python
# if not documents:
#     return "No se recuperó contexto."
```

En el grafo actual esto no causa un problema porque `assess_evidence` enruta hacia `fallback_answer` antes de llamar a `format_context` cuando `documents == []`.

Sin embargo, al incorporar ciclos como:

```text
retrieve → grade → rewrite → retrieve
```

debe mantenerse explícitamente esa invariancia: **`format_context` solo debe ejecutarse con un conjunto de documentos válido**. La condición no debería quedar implícita entre funciones desacopladas.

---

# 3. Ubicación de las técnicas dentro del pipeline

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

# 4. Etapa 2 — Mejora en la comprensión de la consulta

## 4.1. Query Rewriting

### Definición

**Query Rewriting** transforma la consulta original en una formulación más adecuada para el sistema de recuperación. La reformulación puede eliminar ruido, corregir ambigüedad, incorporar terminología del dominio o convertir una consulta conversacional en una consulta autosuficiente.

El trabajo *Query Rewriting for Retrieval-Augmented Large Language Models* propone explícitamente una arquitectura **Rewrite-Retrieve-Read**, añadiendo una etapa de reescritura antes de recuperar información.

### Ejemplo

Consulta original:

```text
¿Qué tiene que hacer una empresa pequeña con seguridad laboral?
```

Consulta para retrieval:

```text
Obligaciones y estándares mínimos del SG-SST aplicables a una microempresa colombiana.
```

### Ubicación en el pipeline

**Antes de `retrieve`.**

Pipeline:

```text
question
   ↓
rewrite_query
   ↓
retrieve
```

En `RagGraphState` convendría mantener ambas versiones:

```python
original_question: str
retrieval_query: str
```

La pregunta original debe conservarse para generación y trazabilidad; la reescrita se utiliza principalmente para retrieval.

### Ventajas

- Reduce discrepancias entre lenguaje del usuario y vocabulario del corpus.
- Puede normalizar consultas informales.
- Tiene una integración relativamente simple con LangGraph.
- No requiere modificar el corpus ni los embeddings existentes.

### Riesgos

- El LLM puede modificar la intención original.
- Puede agregar restricciones no expresadas por el usuario.
- Introduce una llamada adicional al modelo.
- Una mala reescritura puede degradar el retrieval.

### Referencia principal

Ma, X., Gong, Y., He, P., Zhao, H., & Duan, N. (2023). *Query Rewriting for Retrieval-Augmented Large Language Models*.  
https://arxiv.org/abs/2305.14283

---

## 4.2. RAG-Fusion / Multi-Query Retrieval + Reciprocal Rank Fusion

### Definición

La técnica genera varias reformulaciones de una misma consulta, ejecuta retrieval para cada una y fusiona posteriormente los rankings obtenidos.

**RAG-Fusion** combina múltiples consultas con **Reciprocal Rank Fusion (RRF)** para consolidar candidatos recuperados desde diferentes perspectivas de la pregunta.

### Ejemplo

Pregunta:

```text
¿Qué obligaciones tiene una microempresa respecto al SG-SST?
```

Consultas generadas:

```text
Q0: obligaciones SG-SST para microempresas
Q1: estándares mínimos SG-SST empresas pequeñas
Q2: requisitos de seguridad y salud en el trabajo para microempresas
Q3: responsabilidades del empleador en SG-SST para empresas pequeñas
```

Cada consulta recupera resultados y RRF combina sus posiciones.

### Ubicación en el pipeline

**Antes y durante `retrieve`, con una fase de fusión posterior a las búsquedas.**

```text
question
   ↓
generate_queries
   ↓
q1 ─→ retrieve ─┐
q2 ─→ retrieve ─┼→ RRF → normalize_documents
q3 ─→ retrieve ─┤
q4 ─→ retrieve ─┘
```

Probablemente exigiría dividir el nodo actual `retrieve` en:

```text
generate_queries
retrieve_queries
fuse_results
```

### Ventajas

- Aumenta la cobertura cuando existen varias formas válidas de expresar una misma necesidad.
- Puede mejorar recall ante vocabulario heterogéneo.
- RRF no exige que los scores de diferentes búsquedas estén en la misma escala.

### Riesgos

- Multiplica el número de operaciones de retrieval.
- Puede aumentar la latencia.
- Consultas generadas incorrectamente pueden introducir documentos fuera de tema.
- La mejora en recall no garantiza una mejora final después de reranking y límites de contexto.

### Referencias principales

Rackauckas, Z. (2024). *RAG-Fusion: a New Take on Retrieval-Augmented Generation*.  
https://arxiv.org/abs/2402.03367

Medrano, L., Verma, A., & Chhabra, M. (2026). *Scaling Retrieval Augmented Generation with RAG Fusion: Lessons from an Industry Deployment*.  
https://arxiv.org/abs/2603.02153

---

## 4.3. Query Decomposition

### Definición

**Query Decomposition** divide una consulta compleja en varias subpreguntas más simples. Cada subpregunta puede recuperar evidencia independiente y los resultados se agregan antes de generar la respuesta final.

Es especialmente útil cuando una consulta contiene varias obligaciones, condiciones o pasos que pueden encontrarse en fragmentos normativos diferentes.

### Ejemplo

Pregunta:

```text
¿Qué debe hacer una empresa de ocho trabajadores para implementar el SG-SST y qué debe documentar cuando ocurre un accidente?
```

Subconsultas:

```text
1. ¿Qué requisitos del SG-SST aplican a una empresa de ocho trabajadores?
2. ¿Qué obligaciones existen frente a accidentes de trabajo?
3. ¿Qué documentación debe conservarse sobre la investigación del accidente?
```

### Ubicación en el pipeline

**Antes de retrieval.**

```text
question
   ↓
decompose_query
   ↓
subquery_1 ─→ retrieve ─┐
subquery_2 ─→ retrieve ─┼→ merge → rerank
subquery_3 ─→ retrieve ─┘
```

### Ventajas

- Mejora la cobertura de consultas compuestas o multi-hop.
- Permite recuperar evidencia diferente para cada componente.
- Facilita detectar qué parte de una pregunta sí tiene evidencia y cuál no.

### Riesgos

- Preguntas simples pueden descomponerse innecesariamente.
- Una mala descomposición puede perder relaciones entre condiciones.
- Aumenta retrieval, tokens y complejidad de orquestación.
- Conviene disponer de un clasificador o criterio que determine cuándo descomponer.

### Referencias principales

Ammann, P. J. L. (2025). *Question Decomposition for Retrieval-Augmented Generation*. ACL Student Research Workshop.  
https://aclanthology.org/2025.acl-srw.32/

Petcu, R. et al. (2026). *Query Decomposition for RAG: Balancing Exploration and Exploitation*. EACL 2026.  
https://aclanthology.org/2026.eacl-long.322/

---

# 5. Etapa 3 — Mejora en la recuperación de la información

## 5.1. Hybrid Retrieval + Reciprocal Rank Fusion

### Definición

**Esta técnica representa una extensión directa del baseline actual.** El sistema ya dispone de **Dense Retrieval vectorial en Chroma**; el experimento consiste en conservar esa rama y añadir recuperación sparse/léxica para posteriormente fusionar ambos rankings.

**Hybrid Retrieval** combina señales de recuperación de distinta naturaleza:

- **Dense Retrieval:** similitud semántica mediante embeddings. **Ya implementado en el baseline.**
- **Sparse Retrieval:** coincidencia léxica mediante métodos como BM25 o representaciones sparse aprendidas. **Componente nuevo.**
- **Fusion:** combinación de rankings, por ejemplo mediante RRF. **Componente nuevo.**

En normativa, la combinación resulta relevante porque una consulta puede requerir simultáneamente comprensión semántica y coincidencia exacta de términos como números de resolución, artículos, siglas o conceptos jurídicos.

### Ejemplo

Consulta:

```text
¿Qué exige el artículo 3 de la Resolución 0312 sobre estándares mínimos?
```

La búsqueda sparse puede favorecer:

```text
"Artículo 3"
"Resolución 0312"
"estándares mínimos"
```

La búsqueda dense puede recuperar fragmentos semánticamente relacionados aunque la formulación no coincida exactamente.

### Ubicación en el pipeline

**Dentro de la etapa `retrieve`.**

```text
                  ┌→ dense retrieval ─┐
retrieval_query ──┤                   ├→ RRF → candidates
                  └→ sparse retrieval ─┘
```

El nodo `retrieve` actual debería convertirse en un componente capaz de ejecutar más de un retriever y fusionar resultados.

### Ventajas

- Complementa coincidencia semántica y coincidencia textual exacta.
- Adecuado para dominios con terminología, referencias y códigos específicos.
- Puede aumentar robustez frente a variaciones de redacción.

### Riesgos

- Requiere mantener o implementar dos mecanismos de recuperación.
- Necesita una estrategia de fusión.
- El incremento de candidatos puede aumentar el costo posterior de reranking.
- Debe evaluarse con métricas de retrieval; no basta con evaluar únicamente la respuesta final.

### Referencias principales

Meng, S. et al. (2026). *Sifei at SemEval-2026 Task 8: Hybrid Retrieval and Query Rewriting for Multi-Turn RAG*.  
https://aclanthology.org/2026.semeval-1.32/

Raya-Rios, V. et al. (2026). *IIMAS-RAG at SemEval-2026 Task 8*.  
https://aclanthology.org/2026.semeval-1.345/

---

## 5.2. Retrieve-Many + Cross-Encoder Reranking

### Definición

En lugar de recuperar directamente el pequeño conjunto que se enviará al LLM, el retriever recupera un conjunto mayor de candidatos. Posteriormente, un **reranker** evalúa con mayor precisión la relación entre pregunta y documento y conserva únicamente los mejores fragmentos.

```text
retrieve top-N
      ↓
cross-encoder reranker
      ↓
select top-K
```

La recuperación inicial prioriza **recall**; el reranker busca mejorar la **precision** del conjunto final.

### Ejemplo

```text
Retriever: top 30 candidatos
Reranker: reevalúa los 30
Contexto final: top 5
```

### Ubicación en el pipeline

**Después de `normalize_documents` y antes de evaluar evidencia.**

```text
retrieve
   ↓
normalize_documents
   ↓
rerank_documents
   ↓
assess_evidence
```

Para que el experimento sea auditable, `normalize_documents` debería conservar también el identificador del resultado y, cuando Chroma lo retorne, su `distance`. El reranker producirá su propio score de relevancia, por lo que deben mantenerse separadas ambas señales:

```text
dense_distance     = señal del retriever vectorial
reranker_score     = señal de la segunda etapa
```

No deben mezclarse como si estuvieran en la misma escala.

### Ventajas

- Reduce documentos semánticamente cercanos pero poco útiles.
- Permite utilizar un retrieval inicial más amplio.
- Separa claramente recall y precision.
- Puede mejorar la calidad del contexto sin aumentar el número final de fragmentos enviados al generador.

### Riesgos

- Añade latencia computacional.
- El reranker debe estar alineado con el idioma y dominio.
- Rerankear demasiados candidatos puede ser costoso.
- Un reranker deficiente puede eliminar evidencia válida recuperada en primera etapa.

### Referencias principales

Nogueira, R., & Cho, K. (2019). *Passage Re-ranking with BERT*.  
https://arxiv.org/abs/1901.04085

Meng, S. et al. (2026). *Sifei at SemEval-2026 Task 8: Hybrid Retrieval and Query Rewriting for Multi-Turn RAG*.  
https://aclanthology.org/2026.semeval-1.32/

---

## 5.3. Parent-Document / Small-to-Big Retrieval

### Definición

La técnica separa la unidad utilizada para **buscar** de la unidad utilizada como **contexto del LLM**.

Los fragmentos pequeños o *children* se indexan porque permiten una comparación semántica precisa. Cuando uno de ellos coincide con la consulta, el sistema recupera su fragmento padre, que contiene un contexto más amplio.

### Aplicación al corpus normativo

```text
Artículo completo = parent

Numeral / inciso / fragmento semántico = child
```

Pipeline:

```text
query
  ↓
search child chunks
  ↓
child relevante
  ↓
parent_id
  ↓
recuperar artículo completo
```

### Ubicación en el pipeline

**Dentro del retrieval, después de identificar el child y antes de construir el conjunto final de documentos.**

```text
retrieve_child
    ↓
resolve_parent
    ↓
normalize_documents
```

### Ventajas

- Permite precisión durante búsqueda sin perder contexto jurídico.
- Reduce el riesgo de entregar un numeral aislado de su artículo.
- Aprovecha la jerarquía natural de normas: título, capítulo, artículo, parágrafo, numeral, tabla.

### Riesgos

- Requiere mantener relaciones `child_id → parent_id`.
- Un padre demasiado grande puede introducir ruido.
- Debe decidirse qué nivel constituye un padre: artículo, sección o capítulo.
- Duplicados de children pertenecientes al mismo padre deben deduplicarse.

### Referencia principal

LangChain. *Docugami integration — small-to-big retrieval / parent chunks*.  
https://docs.langchain.com/oss/python/integrations/document_loaders/docugami

---

# 6. Etapa 4 — Incorporación del contexto empresarial

## 6.1. Metadata-Aware Retrieval / Metadata Filtering

### Definición

El perfil empresarial se convierte en restricciones estructuradas que afectan directamente qué documentos o fragmentos pueden ser recuperados.

Ejemplo de estado:

```python
company_profile = {
    "employee_count": 8,
    "risk_level": "I",
    "company_size": "micro"
}
```

Estas propiedades pueden utilizarse para construir filtros compatibles con la metadata almacenada en el vector store.

### Ubicación en el pipeline

**Antes y dentro de `retrieve`.**

```text
company_profile
      ↓
build_filters
      ↓
retrieval_query + filters
      ↓
retrieve
```

### Ventajas

- Evita recuperar contenido conocido de antemano como no aplicable.
- Reduce ruido antes de llegar al LLM.
- No exige una llamada adicional al LLM cuando el perfil ya es estructurado.
- Chroma soporta filtrado mediante `where`.

### Riesgos

- La metadata del corpus debe representar correctamente la aplicabilidad normativa.
- Un filtro demasiado restrictivo puede eliminar evidencia relevante.
- Algunas condiciones jurídicas no pueden representarse con filtros simples.
- No se deben inferir automáticamente atributos empresariales ausentes.

### Referencias principales

Chroma. *Metadata Filtering*.  
https://docs.trychroma.com/docs/querying-collections/metadata-filtering

Chroma. *Query Collection*.  
https://docs.trychroma.com/reference/chroma-api/record/query-collection

---

## 6.2. Self-Query Retrieval

### Definición

**Self-Query Retrieval** utiliza un LLM para interpretar una consulta en lenguaje natural y separar:

1. la parte semántica que debe buscarse;
2. las restricciones estructuradas que pueden expresarse como filtros de metadata.

### Ejemplo

Pregunta:

```text
Soy una empresa de ocho trabajadores de riesgo I. ¿Qué estándares debo cumplir?
```

Salida conceptual:

```text
semantic_query:
"estándares mínimos SG-SST aplicables"

filters:
employee_count <= 10
risk_level == "I"
```

### Ubicación en el pipeline

**Antes de `retrieve`.**

```text
question
   ↓
self_query
   ├→ semantic_query
   └→ metadata_filters
           ↓
        retrieve
```

### Ventajas

- Convierte restricciones expresadas informalmente en filtros estructurados.
- Puede mejorar precisión cuando el corpus dispone de buena metadata.
- Evita depender exclusivamente de embeddings para atributos categóricos.

### Riesgos

- El LLM puede construir filtros incorrectos.
- Debe restringirse a un esquema de metadata conocido.
- No debe utilizarse para volver a inferir datos que ya existen estructurados en el perfil empresarial.
- Restricciones no representables en metadata pueden perderse.

### Referencias principales

Požarnik Vavken, M., Ogrinc, M., Eftimov, T., & Koroušić Seljak, B. (2026). *Evaluation of LLMs in retrieving food and nutritional context for RAG systems*.  
https://arxiv.org/abs/2603.09704

Chroma. *Metadata Filtering*.  
https://docs.trychroma.com/docs/querying-collections/metadata-filtering

---

## 6.3. Context-Aware Query Rewriting

### Definición

Es una variante de Query Rewriting en la que la reescritura no depende únicamente de la pregunta actual. El sistema utiliza contexto adicional —por ejemplo, perfil empresarial o historial conversacional— para producir una consulta autosuficiente para retrieval.

### Ejemplo

Pregunta:

```text
¿Y qué documentos debo tener?
```

Perfil / contexto:

```text
Microempresa
8 trabajadores
Riesgo I
```

Consulta para retrieval:

```text
Documentación del SG-SST exigible a una microempresa colombiana
con ocho trabajadores clasificada en riesgo I.
```

### Ubicación en el pipeline

**Antes de `retrieve` y después de disponer del contexto empresarial o conversacional.**

```text
question + company_profile + relevant_history
                     ↓
            contextual_rewrite
                     ↓
             retrieval_query
                     ↓
                 retrieve
```

### Ventajas

- Resuelve preguntas elípticas o dependientes de contexto.
- Permite integrar el perfil empresarial en la búsqueda y no únicamente en el prompt de generación.
- Es útil si posteriormente el sistema pasa de consultas aisladas a conversaciones multi-turn.

### Riesgos

- Introducir demasiado historial puede contaminar la consulta.
- El sistema debe seleccionar únicamente información contextual relevante.
- Una reescritura incorrecta puede cambiar el alcance de la pregunta.
- Si el perfil ya genera filtros estructurados, esta técnica debe complementar y no duplicar Metadata-Aware Retrieval.

### Referencias principales

Wigger, F. et al. (2026). *Contextual Query Rewriting and Dense Retrieval for Multi-Turn RAG*.  
https://aclanthology.org/2026.semeval-1.227/

Zhou, K. et al. (2026). *UTRAG at SemEval-2026 Task 8: History-Aware Query Rewriting*.  
https://aclanthology.org/2026.semeval-1.237/

---

# 7. Etapa 5 — Validación y control de la respuesta

## 7.1. Retrieval Relevance Grading / CRAG-style Evidence Grader

### Definición

Un **relevance grader** evalúa si los documentos recuperados son realmente relevantes para la consulta antes de permitir que el sistema genere una respuesta.

Esto reemplaza el criterio débil:

```python
bool(documents)
```

por una evaluación de calidad de evidencia.

CRAG propone explícitamente un evaluador de retrieval capaz de estimar la calidad del conjunto recuperado y activar acciones correctivas.

### Ubicación en el pipeline

**Sustituye o amplía `assess_evidence`.**

```text
retrieve
   ↓
normalize
   ↓
rerank
   ↓
grade_relevance
   ├→ relevant → answerability
   └→ irrelevant → rewrite / retry / fallback
```

En LangGraph es un punto natural para utilizar `add_conditional_edges`.

### Ventajas

- Evita interpretar cualquier resultado de Chroma como evidencia válida.
- Permite ciclos correctivos.
- Separa claramente disponibilidad de documentos de relevancia de documentos.
- Está alineado con arquitecturas correctivas de RAG.

### Riesgos

- El grader también puede cometer errores.
- Una evaluación LLM por cada consulta aumenta costo.
- Debe limitarse el número de reintentos para evitar ciclos.
- Conviene utilizar salida estructurada, no texto libre.

### Referencias principales

Yan, S.-Q., Gu, J.-C., Zhu, Y., & Ling, Z.-H. (2024). *Corrective Retrieval Augmented Generation*.  
https://arxiv.org/abs/2401.15884

LangChain. *Build a custom RAG agent with LangGraph*.  
https://docs.langchain.com/oss/python/langgraph/agentic-rag

---

## 7.2. Answerability Gate / Sufficient-Context Gate

### Definición

Un documento puede ser relevante y aun así ser insuficiente para responder completamente una pregunta.

El **Answerability Gate** evalúa si el conjunto de contexto recuperado contiene la información necesaria para responder. Por tanto, responde una pregunta distinta al relevance grader:

```text
Relevance:
¿Los documentos tienen relación con la consulta?

Answerability:
¿Los documentos contienen evidencia suficiente para contestarla?
```

### Ejemplo

Pregunta:

```text
¿Qué obligación tiene el empleador y en qué plazo debe cumplirla?
```

El contexto contiene la obligación pero no el plazo.

Resultado esperado:

```text
Relevant: sí
Answerable completamente: no
```

El sistema puede intentar recuperar evidencia adicional o responder únicamente la parte soportada.

### Ubicación en el pipeline

**Después del retrieval/reranking y antes de `build_messages` / `generate_answer`.**

```text
documents
   ↓
relevance_grading
   ↓
format_context
   ↓
answerability_gate
   ├→ sufficient → build_messages → generate
   └→ insufficient → retry / partial answer / fallback
```

### Ventajas

- Reduce respuestas fabricadas a partir de evidencia parcial.
- Permite abstención explícita.
- Es especialmente importante en dominios normativos.
- Diferencia fallas de retrieval de fallas de generación.

### Riesgos

- Requiere definir qué se entiende por evidencia “suficiente”.
- Puede provocar falsos negativos y abstenciones innecesarias.
- Las preguntas parcialmente respondibles requieren un estado adicional.
- Debe evaluarse con ejemplos answerable, partially answerable y unanswerable.

### Referencias principales

Joren, H. et al. (2024). *Sufficient Context: A New Lens on Retrieval Augmented Generation Systems*.  
https://arxiv.org/abs/2411.06037

Raya-Rios, V. et al. (2026). *IIMAS-RAG at SemEval-2026 Task 8*.  
https://aclanthology.org/2026.semeval-1.345/

---

## 7.3. Claim-Level Citation Verification

### Definición

La presencia de citas en la respuesta no garantiza que cada cita respalde realmente la afirmación asociada.

**Claim-Level Citation Verification** descompone la respuesta en afirmaciones verificables y compara cada afirmación contra la evidencia citada.

Pipeline conceptual:

```text
answer
   ↓
extract_atomic_claims
   ↓
claim 1 + evidence → supported / unsupported / contradicted
claim 2 + evidence → supported / unsupported / contradicted
claim 3 + evidence → supported / unsupported / contradicted
   ↓
accept / remove / regenerate
```

### Ubicación en el pipeline

**Después de `generate_answer` y antes de `format_result`.**

```text
generate_answer
      ↓
verify_citations
      ↓
 ┌────┴────┐
pass      fail
 │          │
 ↓          └→ refine / regenerate / fallback
format_result
```

### Ventajas

- Comprueba grounding a nivel de afirmación.
- Permite detectar citas decorativas o incorrectas.
- Mejora trazabilidad y auditabilidad.
- Resulta especialmente adecuada para respuestas normativas donde una obligación debe estar vinculada con una fuente concreta.

### Riesgos

- Puede exigir una o varias llamadas adicionales.
- La segmentación en claims debe ser consistente.
- La verificación mediante otro LLM no constituye verdad absoluta.
- Debe diferenciar soporte, contradicción y ausencia de evidencia.

### Referencias principales

Qian, H. et al. (2025). *VeriCite: Towards Reliable Citations in Retrieval-Augmented Generation via Rigorous Verification*.  
https://arxiv.org/abs/2510.11394

Ji, Y. et al. (2026). *MedRAGChecker: Claim-Level Verification for Biomedical Retrieval-Augmented Generation*.  
https://arxiv.org/abs/2601.06519

---

# 8. Tabla consolidada de técnicas candidatas

| **Etapa / dimensión** | **Técnica 1** | **Técnica 2** | **Técnica 3** |
|---|---|---|---|
| **Comprensión de consultas** | **Query Rewriting:** reformula la consulta para acercarla al vocabulario y estructura adecuados para retrieval, conservando la pregunta original para generación y trazabilidad. | **RAG-Fusion / Multi-Query + RRF:** genera varias formulaciones de la pregunta, realiza múltiples búsquedas y fusiona los rankings para aumentar cobertura. | **Query Decomposition:** divide preguntas compuestas en subconsultas independientes, recupera evidencia para cada una y posteriormente combina los candidatos. |
| **Recuperación** | **Hybrid Retrieval + RRF:** combina recuperación dense y sparse para aprovechar simultáneamente similitud semántica y coincidencia léxica exacta. | **Retrieve-Many + Reranking:** recupera un conjunto amplio de candidatos y utiliza un reranker más preciso para seleccionar los fragmentos finales. | **Parent-Document / Small-to-Big:** busca sobre fragmentos pequeños y, tras encontrar coincidencias, recupera una unidad padre más amplia para preservar el contexto normativo. |
| **Contexto empresarial** | **Metadata-Aware Retrieval:** convierte atributos empresariales estructurados en filtros aplicados directamente durante retrieval. | **Self-Query Retrieval:** transforma restricciones expresadas en lenguaje natural en una consulta semántica más filtros de metadata. | **Context-Aware Query Rewriting:** reformula la consulta utilizando perfil empresarial o historial relevante para producir una búsqueda autosuficiente y contextualizada. |
| **Validación y control** | **Retrieval Relevance Grading / CRAG:** evalúa si los documentos recuperados son realmente relevantes y permite decidir entre continuar, reintentar o aplicar fallback. | **Answerability / Sufficient-Context Gate:** comprueba si el contexto relevante contiene evidencia suficiente para responder total o parcialmente antes de invocar al generador. | **Claim-Level Citation Verification:** verifica después de la generación que cada afirmación esté efectivamente respaldada por los fragmentos o referencias citados. |

---

# 9. Resumen de ubicación dentro del LangGraph actual

| **Técnica** | **Ubicación** | **Cambio sobre el grafo actual** |
|---|---|---|
| **Dense Retrieval (baseline)** | `retrieve` actual | Ya implementado mediante búsqueda vectorial en Chroma; no constituye una técnica nueva de mejora |
| Query Rewriting | Antes de `retrieve` | Agregar `rewrite_query` |
| RAG-Fusion / Multi-Query + RRF | Antes y durante `retrieve` | Agregar `generate_queries`, búsquedas múltiples y `fuse_results` |
| Query Decomposition | Antes de `retrieve` | Agregar `decompose_query`, retrieval por subconsulta y fusión |
| Hybrid Retrieval + RRF | Dentro de `retrieve` | Mantener la rama dense actual, agregar rama sparse y fusionar rankings |
| Retrieve-Many + Reranking | Después de `normalize_documents` | Recuperar más candidatos, preservar señales del retrieval y agregar `rerank_documents` |
| Parent-Document Retrieval | Dentro/después del retrieval inicial | Resolver `child → parent` antes del contexto final |
| Metadata-Aware Retrieval | Antes/dentro de `retrieve` | Construir y pasar filtros al retriever |
| Self-Query Retrieval | Antes de `retrieve` | Agregar extracción estructurada `query + filters` |
| Context-Aware Query Rewriting | Antes de `retrieve` | Incorporar perfil/historial al nodo de reescritura |
| Relevance Grading / CRAG | En `assess_evidence` | Sustituir `bool(documents)` por evaluación de relevancia |
| Answerability Gate | Antes de `build_messages` / `generate_answer` | Agregar decisión sobre suficiencia de contexto |
| Claim-Level Citation Verification | Después de `generate_answer` | Agregar verificación antes de `format_result` |

---

# 10. Técnicas documentadas previamente que quedan como alternativas

Las siguientes técnicas son válidas y pueden conservarse en la revisión bibliográfica, pero no forman parte de las tres candidatas principales propuestas para cada etapa.

## HyDE — Hypothetical Document Embeddings

Genera un documento hipotético a partir de la consulta y utiliza su embedding para recuperar documentos reales. Es una técnica válida de enriquecimiento de consulta, pero en un dominio normativo debe evaluarse cuidadosamente porque el documento hipotético puede contener información inventada que modifique la dirección del retrieval.

Referencia:

Gao, L. et al. (2023). *Precise Zero-Shot Dense Retrieval without Relevance Labels*.  
https://aclanthology.org/2023.acl-long.99/

**Ubicación:** antes de `retrieve`.

---

## Query Expansion

Agrega términos relacionados, sinónimos o vocabulario especializado a la consulta para ampliar la recuperación.

**Ubicación:** antes de `retrieve`.

Puede ser útil si existe un vocabulario controlado del SG-SST, pero una expansión no controlada mediante LLM puede aumentar el ruido.

---

## Conversational Query Rewriting

Convierte una pregunta dependiente del historial conversacional en una consulta autónoma, resolviendo pronombres, elipsis y referencias a turnos anteriores.

**Ubicación:** antes de `retrieve`.

Para una interfaz estrictamente single-turn tiene poco valor inmediato; cobra importancia cuando el agente conserva historial conversacional.

Referencia:

Elgohary, A., Peskov, D., & Boyd-Graber, J. (2019). *Can You Unpack That? Learning to Rewrite Questions-in-Context*.  
https://aclanthology.org/D19-1605/

---

## Contextual Compression

Reduce o extrae únicamente las partes de los documentos recuperados que resultan relevantes para la pregunta antes de construir el prompt.

**Ubicación:** después de retrieval/reranking y antes de `format_context`.

Es útil para controlar tokens, pero puede eliminar condiciones, excepciones o contexto jurídico si la compresión es demasiado agresiva.

---

## Query Classification / Intent Classification

Clasifica la consulta para seleccionar un flujo, retriever, filtro o estrategia diferente.

Ejemplos:

```text
consulta normativa
consulta de aplicabilidad
pregunta sobre definición
pregunta multi-parte
```

**Ubicación:** al inicio del pipeline, antes de cualquier técnica de query transformation.

Tiene mayor valor cuando existen rutas realmente diferentes. Agregar un clasificador sin rutas diferenciadas solo incrementaría complejidad.

---

# 11. Orden recomendado para experimentación

No deberían implementarse las doce técnicas al mismo tiempo. Hacerlo impediría atribuir correctamente las mejoras observadas.

Una secuencia experimental razonable es:

```text
Baseline actual: Dense Retrieval vectorial en Chroma
     ↓
0. Instrumentar retrieval: conservar IDs/distances y medir Recall@k
     ↓
1. Relevance Grading
     ↓
2. Query Rewriting
     ↓
3. Hybrid Retrieval
     ↓
4. Reranking
     ↓
5. Parent-Document Retrieval
     ↓
6. RAG-Fusion / Query Decomposition
     ↓
7. Contexto empresarial
     ↓
8. Answerability + Citation Verification
```

Cada experimento debería mantener constantes, en la medida de lo posible:

- corpus;
- dataset de evaluación;
- modelo generador;
- temperatura;
- prompt;
- número final de documentos entregados al LLM;
- métricas;
- criterios de evaluación.

Esto permite aplicar estudios de ablación y determinar qué componente produce realmente una mejora.

---

# 12. Referencias

- Ammann, P. J. L. (2025). *Question Decomposition for Retrieval-Augmented Generation*. ACL Student Research Workshop. https://aclanthology.org/2025.acl-srw.32/
- Chroma. *Metadata Filtering*. https://docs.trychroma.com/docs/querying-collections/metadata-filtering
- Chroma. *Query and Get*. https://docs.trychroma.com/docs/querying-collections/query-and-get
- Chroma. *Query Collection*. https://docs.trychroma.com/reference/chroma-api/record/query-collection
- Elgohary, A., Peskov, D., & Boyd-Graber, J. (2019). *Can You Unpack That? Learning to Rewrite Questions-in-Context*. https://aclanthology.org/D19-1605/
- Gao, L. et al. (2023). *Precise Zero-Shot Dense Retrieval without Relevance Labels*. https://aclanthology.org/2023.acl-long.99/
- Ji, Y. et al. (2026). *MedRAGChecker: Claim-Level Verification for Biomedical Retrieval-Augmented Generation*. https://arxiv.org/abs/2601.06519
- Joren, H. et al. (2024). *Sufficient Context: A New Lens on Retrieval Augmented Generation Systems*. https://arxiv.org/abs/2411.06037
- LangChain. *Build a custom RAG agent with LangGraph*. https://docs.langchain.com/oss/python/langgraph/agentic-rag
- LangChain. *Docugami integration — small-to-big retrieval*. https://docs.langchain.com/oss/python/integrations/document_loaders/docugami
- Ma, X., Gong, Y., He, P., Zhao, H., & Duan, N. (2023). *Query Rewriting for Retrieval-Augmented Large Language Models*. https://arxiv.org/abs/2305.14283
- Medrano, L., Verma, A., & Chhabra, M. (2026). *Scaling Retrieval Augmented Generation with RAG Fusion: Lessons from an Industry Deployment*. https://arxiv.org/abs/2603.02153
- Meng, S. et al. (2026). *Sifei at SemEval-2026 Task 8: Hybrid Retrieval and Query Rewriting for Multi-Turn RAG*. https://aclanthology.org/2026.semeval-1.32/
- Nogueira, R., & Cho, K. (2019). *Passage Re-ranking with BERT*. https://arxiv.org/abs/1901.04085
- Petcu, R. et al. (2026). *Query Decomposition for RAG: Balancing Exploration and Exploitation*. https://aclanthology.org/2026.eacl-long.322/
- Požarnik Vavken, M., Ogrinc, M., Eftimov, T., & Koroušić Seljak, B. (2026). *Evaluation of LLMs in retrieving food and nutritional context for RAG systems*. https://arxiv.org/abs/2603.09704
- Qian, H. et al. (2025). *VeriCite: Towards Reliable Citations in Retrieval-Augmented Generation via Rigorous Verification*. https://arxiv.org/abs/2510.11394
- Rackauckas, Z. (2024). *RAG-Fusion: a New Take on Retrieval-Augmented Generation*. https://arxiv.org/abs/2402.03367
- Raya-Rios, V. et al. (2026). *IIMAS-RAG at SemEval-2026 Task 8*. https://aclanthology.org/2026.semeval-1.345/
- Wigger, F. et al. (2026). *Contextual Query Rewriting and Dense Retrieval for Multi-Turn RAG*. https://aclanthology.org/2026.semeval-1.227/
- Yan, S.-Q., Gu, J.-C., Zhu, Y., & Ling, Z.-H. (2024). *Corrective Retrieval Augmented Generation*. https://arxiv.org/abs/2401.15884
- Zhou, K. et al. (2026). *UTRAG at SemEval-2026 Task 8: History-Aware Query Rewriting*. https://aclanthology.org/2026.semeval-1.237/
