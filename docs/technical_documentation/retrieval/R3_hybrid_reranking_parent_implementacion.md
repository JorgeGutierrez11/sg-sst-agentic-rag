# R3 — Hybrid Retrieval + Cross-Encoder Reranking + Parent-Document Retrieval

## Propósito

Este documento registra cómo quedó implementada la configuración **R3 — Hybrid Retrieval + Cross-Encoder Reranking + Parent-Document Retrieval** para poder reconstruirla exactamente en el futuro si resulta ganadora en la evaluación con ARES.

R3 parte de R2 y agrega una etapa final de expansión **child → parent** después del reranking:

```text
Pregunta
  ├── Chroma / Dense ──┐
  │                    ├── Reciprocal Rank Fusion (RRF)
  └── BM25 / Sparse ───┘
                           ↓
                      40 candidatos
                           ↓
                Cross-Encoder Reranking
                           ↓
                    8 child chunks
                           ↓
                   Parent Expansion
                           ↓
                    Deduplicación
                           ↓
                       Contexto
                           ↓
                     Generación
```

Durante esta evaluación permanecen desactivadas:

```text
Query Expansion
Business Context
```

---

# Objetivo experimental

R3 busca medir si, después de seleccionar los mejores fragmentos mediante Hybrid Retrieval + Cross-Encoder Reranking, **expandir los child chunks hacia sus parent chunks** mejora la calidad del contexto entregado al generador.

La comparación acumulativa queda:

```text
R1
Dense + BM25 + RRF
        ↓
R2
Dense + BM25 + RRF + Cross-Encoder
        ↓
R3
Dense + BM25 + RRF + Cross-Encoder + Parent-Document
```

La diferencia principal entre R2 y R3 es la expansión **small-to-big** posterior al reranking.

---

# Principio de diseño

R3 separa:

```text
Unidad óptima para buscar
≠
Unidad óptima para generar
```

Los **child chunks** se usan para recuperar y rerankear con mayor precisión.

Después, solo los mejores child chunks seleccionados por el Cross-Encoder se expanden hacia sus **parent chunks**, proporcionando al LLM una unidad normativa más amplia y contextualizada.

El orden correcto es:

```text
Hybrid Retrieval
    ↓
Cross-Encoder Reranking
    ↓
Parent Expansion
```

No se expande a parents antes del Cross-Encoder.

---

# Parámetros utilizados

Archivo:

```text
agents/consulta_normativa/langchain_rag/config.py
```

Configuración relevante:

```python
RETRIEVAL_TOP_K = 8
DEFAULT_TOP_K = RETRIEVAL_TOP_K

RRF_K = 60

HYBRID_CANDIDATE_TOP_K = 40
HYBRID_RRF_K = RRF_K

RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
RERANKER_MAX_LENGTH = 512
RERANKER_FINAL_TOP_K = DEFAULT_TOP_K
RERANKER_CANDIDATE_POOL_SIZE = 40
```

También se utiliza:

```python
DEFAULT_PARENT_CHUNKS_PATH
```

proveniente de la configuración de chunking.

Interpretación:

```text
Chroma / Dense candidatos       = 40
BM25 / Sparse candidatos        = 40
RRF k                           = 60
Candidatos al reranker          = 40
Cross-Encoder                   = BAAI/bge-reranker-v2-m3
Longitud máxima reranker        = 512
Child chunks seleccionados      = 8
Parent expansion                = posterior al reranking
Documentos finales              = <= 8 por deduplicación
```

---

# Archivos involucrados

## 1. `config.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/config.py
```

Configuración utilizada:

```python
HYBRID_CANDIDATE_TOP_K = 40
HYBRID_RRF_K = RRF_K

RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
RERANKER_MAX_LENGTH = 512
RERANKER_FINAL_TOP_K = DEFAULT_TOP_K
RERANKER_CANDIDATE_POOL_SIZE = 40
```

Con:

```python
RRF_K = 60
DEFAULT_TOP_K = 8
```

Para Parent-Document se usa:

```python
DEFAULT_PARENT_CHUNKS_PATH
```

---

# 2. `main.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/main.py
```

## Imports de configuración

Para R3 se utilizan:

```python
DEFAULT_CHROMA_PATH
DEFAULT_COLLECTION_NAME
HYBRID_CANDIDATE_TOP_K
HYBRID_RRF_K
RERANKER_MODEL_NAME
RERANKER_MAX_LENGTH
RERANKER_CANDIDATE_POOL_SIZE
RERANKER_FINAL_TOP_K
DEFAULT_PARENT_CHUNKS_PATH
```

---

## `RuntimeDependencies`

R3 requiere:

```python
open_existing_collection: Callable[[Any, str], Any]
open_existing_bm25_index: Callable[..., Any]
hybrid_retriever: Callable[..., Retriever]
get_reranker: Callable[..., Any]
load_parent_documents: Callable[..., Any]
```

---

## Carga de dependencias

En `load_dependencies()` se utilizan:

```python
from agents.consulta_normativa.langchain_rag.retrieval.chroma_retrieval import (
    open_existing_collection,
)

from agents.consulta_normativa.langchain_rag.retrieval.bm25_retrieval import (
    open_existing_index as open_existing_bm25_index,
)

from agents.consulta_normativa.langchain_rag.retrieval.hybrid_retrieval import (
    hybrid_retriever,
)

from agents.consulta_normativa.langchain_rag.retrieval.reranking import (
    get_reranker,
)

from agents.consulta_normativa.langchain_rag.retrieval.parent_document_retrieval import (
    load_parent_documents,
)
```

Y se registran en:

```python
return RuntimeDependencies(
    build_deepseek_llm=build_deepseek_llm,
    build_langgraph_rag=build_langgraph_rag,
    answer_with_langgraph=answer_with_langgraph,
    open_existing_collection=open_existing_collection,
    open_existing_bm25_index=open_existing_bm25_index,
    hybrid_retriever=hybrid_retriever,
    get_reranker=get_reranker,
    load_parent_documents=load_parent_documents,
)
```

---

# Construcción de R3 en `build_runtime()`

## Abrir Chroma

```python
collection = dependencies.open_existing_collection(
    DEFAULT_CHROMA_PATH,
    DEFAULT_COLLECTION_NAME,
)
```

## Abrir BM25

```python
bm25_index = dependencies.open_existing_bm25_index()
```

## Construir Hybrid Retrieval

```python
retriever = dependencies.hybrid_retriever(
    collection,
    bm25_index,
    candidate_top_k=HYBRID_CANDIDATE_TOP_K,
    rrf_k=HYBRID_RRF_K,
)
```

## Cargar Cross-Encoder

```python
reranker = dependencies.get_reranker(
    RERANKER_MODEL_NAME,
    RERANKER_MAX_LENGTH,
)
```

## Cargar parent chunks

```python
parent_lookup = dependencies.load_parent_documents(
    DEFAULT_PARENT_CHUNKS_PATH
)
```

`parent_lookup` es un diccionario indexado por `parent_id`.

---

## Construir el grafo

```python
graph = dependencies.build_langgraph_rag(
    llm,
    retriever,
    RERANKER_CANDIDATE_POOL_SIZE,
    checkpointer=checkpointer,
    store=memory_store,
    reranker=reranker,
    reranker_candidate_pool_size=RERANKER_CANDIDATE_POOL_SIZE,
    reranker_final_top_k=RERANKER_FINAL_TOP_K,
    parent_lookup=parent_lookup,
)
```

El tercer argumento continúa siendo:

```python
RERANKER_CANDIDATE_POOL_SIZE
```

con valor:

```text
40
```

por lo que el nodo de retrieval entrega 40 documentos híbridos antes del reranking.

---

# 3. `graph.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/graph.py
```

## Imports agregados

R2 ya utilizaba:

```python
from agents.consulta_normativa.langchain_rag.retrieval.reranking import (
    rerank_node,
)
```

Para R3 se agregó:

```python
from agents.consulta_normativa.langchain_rag.retrieval.parent_document_retrieval import (
    expand_parent_documents,
)
```

---

## Firma de `build_langgraph_rag`

La función quedó:

```python
def build_langgraph_rag(
    llm: Any,
    retriever: Retriever,
    top_k: int = DEFAULT_TOP_K,
    checkpointer: Any | None = None,
    store: Any | None = None,
    reranker: Any | None = None,
    reranker_candidate_pool_size: int = 40,
    reranker_final_top_k: int = DEFAULT_TOP_K,
    parent_lookup: dict[str, Any] | None = None,
) -> Any:
```

---

## Nodo de reranking

Se mantiene:

```python
workflow.add_node(
    "rerank",
    rerank_node(
        reranker,
        reranker_candidate_pool_size,
        reranker_final_top_k,
    ),
)
```

---

## Nodo de Parent Expansion

Se agregó:

```python
workflow.add_node(
    "expand_parent_documents",
    expand_parent_documents_node(parent_lookup or {}),
)
```

Wrapper utilizado:

```python
def expand_parent_documents_node(
    parent_lookup: dict[str, Any],
) -> Callable[[RagGraphState], RagGraphState]:
    # Expande los child chunks rerankeados hacia sus parent documents.
    def run(state: RagGraphState) -> RagGraphState:
        documents = state.get("documents", [])

        return {
            "documents": expand_parent_documents(
                documents,
                parent_lookup,
            )
        }

    return run
```

---

# Orden de nodos

Antes de R3, R2 tenía:

```text
retrieve
   ↓
normalize_documents
   ↓
rerank
   ↓
record_retrieval_trace
```

R3 queda:

```text
retrieve
   ↓
normalize_documents
   ↓
rerank
   ↓
expand_parent_documents
   ↓
record_retrieval_trace
```

Código:

```python
workflow.add_edge("retrieve", "normalize_documents")
workflow.add_edge("normalize_documents", "rerank")
workflow.add_edge("rerank", "expand_parent_documents")
workflow.add_edge(
    "expand_parent_documents",
    "record_retrieval_trace",
)
```

---

# Flujo completo del grafo R3

```text
START
  ↓
retrieve
  ↓
Hybrid Retrieval
  ↓
normalize_documents
  ↓
rerank
  ↓
expand_parent_documents
  ↓
record_retrieval_trace
  ↓
evidence_route
  ├── without_evidence → fallback_answer
  └── with_evidence → format_context
                         ↓
                     build_messages
                         ↓
                    generate_answer
                         ↓
                     format_result
                         ↓
                        END
```

---

# 4. `parent_document_retrieval.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py
```

## Carga de parents

La función:

```python
load_parent_documents(
    parents_path
)
```

carga los parent chunks y construye:

```text
parent_id → RetrievedDocument(parent)
```

---

## Función principal de expansión

R3 utiliza:

```python
expand_parent_documents(
    documents,
    parent_lookup,
)
```

Su comportamiento es:

```text
1. Recorrer los documentos seleccionados por el reranker.
2. Detectar documentos con document_type == "child_chunk".
3. Leer su parent_id.
4. Buscar el parent correspondiente en parent_lookup.
5. Sustituir el child por el parent.
6. Mantener el orden de ranking.
7. Deduplicar parents repetidos.
8. Registrar los child IDs que llevaron al mismo parent.
9. Si un parent no existe, conservar el child como fallback.
```

---

## Metadata de trazabilidad

Cuando ocurre una expansión válida se agregan campos como:

```python
parent_expansion_applied
expanded_parent_id
expanded_from_child_id
expanded_from_child_ids
expanded_from_document_type
```

También se conserva:

```python
_retrieval_sources
```

cuando está disponible.

---

## Deduplicación

Si varios child chunks seleccionados pertenecen al mismo parent, solo se conserva una copia del parent.

Ejemplo conceptual:

```text
child A ─┐
         ├── parent X
child B ─┘
```

Resultado:

```text
parent X
expanded_from_child_ids = [child A, child B]
```

Por esta razón el número final de documentos puede ser menor que 8.

---

## Fallback por parent faltante

Si un child contiene `parent_id` pero el parent no existe en el lookup, se conserva el child original y se marca:

```python
parent_expansion_fallback = "missing_parent"
```

---

# Verificación manual realizada

Comando:

```bash
python -m agents.consulta_normativa.langchain_rag.main
```

Pregunta:

```text
Que es el SG-SST?
```

Resultado observado:

```text
-------------------------- R3 HYBRID + RERANKING + PARENT ---------------------------------------

Candidatos recibidos por reranker: 40
Documentos seleccionados por reranker: 8
Fallback reranker: False
Documentos finales después de Parent Expansion: 7
Parents expandidos: 7
Child chunks deduplicados por compartir parent: 1
Fallback por parent faltante: 0
```

Esto confirmó:

```text
Hybrid Retrieval activo                = sí
Chroma activo                          = sí
BM25 activo                            = sí
RRF activo                             = sí
Candidatos antes del reranking         = 40
Cross-Encoder ejecutado                = sí
Child chunks seleccionados             = 8
Parent Expansion ejecutada             = sí
Parents finales                        = 7
Deduplicación realizada                = sí
Child chunks deduplicados              = 1
Fallback del reranker                  = no
Fallback por parent faltante           = no
```

---

# Evidencia de deduplicación

En la prueba, el primer parent fue activado por dos child chunks:

```text
Child IDs que llevaron a este parent:

[
  'child-parent-decreto-1072-de-2015-libro-2-parte-2-titulo-4-capitulo-6-0c24a5ba-0003-33b39d843d-0000-6d00309739',
  'child-parent-decreto-1072-de-2015-libro-2-parte-2-titulo-4-capitulo-6-0c24a5ba-0003-33b39d843d-0001-c4f559f697'
]
```

Ambos fueron sustituidos por un único:

```text
parent_chunk
```

Por eso:

```text
8 child chunks
→
7 parent chunks
```

---

# Evidencia de Parent Expansion

Los documentos finales de la prueba mostraron:

```text
Tipo: parent_chunk
Parent expansion aplicada: True
```

Esto confirmó que los documentos entregados al generador ya correspondían a parents y no a los child chunks recuperados originalmente.

---

# Rendimiento observado

El Cross-Encoder continuó ejecutándose en CPU:

```text
No device provided, using cpu
```

Modelo:

```text
BAAI/bge-reranker-v2-m3
```

La prueba manual mostró aproximadamente 39–40 segundos para la etapa de reranking de los 40 candidatos.

La Parent Expansion es una operación local de lookup y deduplicación; el principal costo computacional observado sigue estando en el Cross-Encoder.

---

# Dataset utilizado

Conjunto:

```text
evaluation/datasets/conjunto_b_optim/conjunto_b1.json
```

Características:

```text
Número de preguntas = 80
IDs                 = B001 ... B080
Tipo                = preguntas independientes
```

---

# Runner utilizado

Archivo:

```text
evaluation/experiments/run_conjunto_b1.py
```

El runner importa:

```python
from agents.consulta_normativa.langchain_rag.main import build_runtime
```

Por tanto, ejecuta la configuración R3 activa.

Cada pregunta utiliza un `thread_id` independiente.

---

# Comando utilizado para generar el TSV

```bash
python evaluation/experiments/run_conjunto_b1.py   --dataset evaluation/datasets/conjunto_b_optim/conjunto_b1.json   --output evaluation/results/ares_runs/r3_hybrid_reranking_parent.tsv   --reset
```

---

# TSV generado

Ruta:

```text
evaluation/results/ares_runs/r3_hybrid_reranking_parent.tsv
```

Formato:

```text
Query
Document
Answer
```

Validación realizada:

```text
Registros                = 80
Filas mal formadas       = 0
Queries vacías           = 0
Documents vacíos         = 0
Answers vacías           = 0
Queries duplicadas       = 0
```

El TSV quedó listo para evaluación con ARES.

---

# Estado final de R3

```text
Query Expansion                     = OFF
Dense Retrieval / Chroma            = ON
Sparse Retrieval / BM25             = ON
Reciprocal Rank Fusion              = ON
Cross-Encoder Reranking             = ON
Parent-Document Retrieval           = ON
Business Context                    = OFF

HYBRID_CANDIDATE_TOP_K              = 40
HYBRID_RRF_K                        = 60
RERANKER_CANDIDATE_POOL_SIZE        = 40
RERANKER_MODEL_NAME                 = BAAI/bge-reranker-v2-m3
RERANKER_MAX_LENGTH                 = 512
RERANKER_FINAL_TOP_K                = 8
```

---

# Cómo restaurar R3 en el futuro

Si R3 resulta ganadora:

1. Mantener Hybrid Retrieval con Chroma + BM25 + RRF.
2. Configurar `HYBRID_CANDIDATE_TOP_K = 40`.
3. Configurar `HYBRID_RRF_K = 60`.
4. Hacer que Hybrid Retrieval entregue 40 candidatos al grafo.
5. Cargar `BAAI/bge-reranker-v2-m3`.
6. Insertar `rerank_node` después de `normalize_documents`.
7. Configurar `candidate_pool_size = 40`.
8. Configurar `final_top_k = 8`.
9. Cargar `parent_lookup` mediante `load_parent_documents(DEFAULT_PARENT_CHUNKS_PATH)`.
10. Pasar `parent_lookup` a `build_langgraph_rag`.
11. Insertar `expand_parent_documents` después de `rerank`.
12. Ejecutar `record_retrieval_trace` después de Parent Expansion.
13. Mantener Query Expansion y Business Context desactivados si se desea reproducir exactamente la evaluación R3.

---

# Identificador experimental

```text
R3 — Hybrid Retrieval + Cross-Encoder Reranking + Parent-Document Retrieval
```

Resultado ARES:

```text
Pendiente de evaluación.
```
