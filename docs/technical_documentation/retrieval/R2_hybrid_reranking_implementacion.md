# R2 — Hybrid Retrieval + Cross-Encoder Reranking

## Propósito

Este documento registra cómo quedó implementada la configuración **R2 — Hybrid Retrieval + Cross-Encoder Reranking** para poder reconstruirla exactamente en el futuro si resulta ganadora en la evaluación con ARES.

R2 parte de la recuperación híbrida de R1 y agrega una segunda etapa de selección mediante Cross-Encoder:

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
                         Top-8
                           ↓
                       Generación
```

Durante esta evaluación permanecen desactivadas:

```text
Query Expansion
Parent-Document Retrieval
Business Context
```

---

## Objetivo experimental

R2 busca medir si agregar un **Cross-Encoder Reranker** después del Hybrid Retrieval mejora la calidad del contexto que llega al generador.

La lógica experimental es:

```text
R1
Dense + BM25 + RRF
        ↓
R2
Dense + BM25 + RRF + Cross-Encoder
```

Por tanto, la diferencia principal entre R1 y R2 es la etapa de reranking.

---

## Parámetros utilizados

Archivo:

```text
agents/consulta_normativa/langchain_rag/config.py
```

Configuración:

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

Interpretación:

```text
Chroma / Dense candidatos       = 40
BM25 / Sparse candidatos        = 40
RRF k                           = 60
Candidatos entregados al rerank = 40
Cross-Encoder                   = BAAI/bge-reranker-v2-m3
Longitud máxima                 = 512
Documentos finales              = 8
```

---

## Orden correcto de ejecución

El corte a 8 documentos ocurre **después del Cross-Encoder**, no antes.

```text
Chroma top-40 ─┐
               ├── RRF
BM25 top-40 ───┘
                  ↓
             40 candidatos
                  ↓
           Cross-Encoder
                  ↓
                Top-8
```

Esto es importante porque el reranker debe recibir el candidate pool completo definido para R2.

---

# Archivos involucrados

## 1. `config.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/config.py
```

Configuración relevante:

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

---

## 2. `main.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/main.py
```

### Imports de configuración

Para R2 se utilizan:

```python
DEFAULT_CHROMA_PATH
DEFAULT_COLLECTION_NAME
HYBRID_CANDIDATE_TOP_K
HYBRID_RRF_K
RERANKER_MODEL_NAME
RERANKER_MAX_LENGTH
RERANKER_CANDIDATE_POOL_SIZE
RERANKER_FINAL_TOP_K
```

Ejemplo:

```python
from agents.consulta_normativa.langchain_rag.config import (
    DEFAULT_CHROMA_PATH,
    DEFAULT_COLLECTION_NAME,
    HYBRID_CANDIDATE_TOP_K,
    HYBRID_RRF_K,
    RERANKER_MODEL_NAME,
    RERANKER_MAX_LENGTH,
    RERANKER_CANDIDATE_POOL_SIZE,
    RERANKER_FINAL_TOP_K,
)
```

---

## `RuntimeDependencies`

Para R2 se utilizan:

```python
open_existing_collection: Callable[[Any, str], Any]
open_existing_bm25_index: Callable[..., Any]
hybrid_retriever: Callable[..., Retriever]
get_reranker: Callable[..., Any]
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
```

Y se registran en `RuntimeDependencies`:

```python
return RuntimeDependencies(
    build_deepseek_llm=build_deepseek_llm,
    build_langgraph_rag=build_langgraph_rag,
    answer_with_langgraph=answer_with_langgraph,
    open_existing_collection=open_existing_collection,
    open_existing_bm25_index=open_existing_bm25_index,
    hybrid_retriever=hybrid_retriever,
    get_reranker=get_reranker,
)
```

---

# Construcción de R2 en `build_runtime()`

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
)
```

El tercer argumento es:

```python
RERANKER_CANDIDATE_POOL_SIZE
```

y vale:

```text
40
```

Esto hace que el nodo `retrieve` solicite 40 documentos al Hybrid Retrieval antes de ejecutar el reranker.

---

# 3. `graph.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/graph.py
```

## Import agregado

```python
from agents.consulta_normativa.langchain_rag.retrieval.reranking import (
    rerank_node,
)
```

---

## Firma de `build_langgraph_rag`

La función quedó preparada para recibir el reranker y sus parámetros:

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
) -> Any:
```

---

## Nodo `rerank`

Se agregó:

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

## Cambio en las conexiones del grafo

Antes de R2:

```text
retrieve
   ↓
normalize_documents
   ↓
record_retrieval_trace
```

Con R2:

```text
retrieve
   ↓
normalize_documents
   ↓
rerank
   ↓
record_retrieval_trace
```

Código:

```python
workflow.add_edge("retrieve", "normalize_documents")
workflow.add_edge("normalize_documents", "rerank")
workflow.add_edge("rerank", "record_retrieval_trace")
```

El resto del flujo se mantiene sin cambios.

---

# Flujo completo del grafo R2

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

# 4. `reranking.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/retrieval/reranking.py
```

## Modelo

El reranker se carga mediante:

```python
@lru_cache(maxsize=4)
def get_reranker(
    model_name: str,
    max_length: int,
) -> Any:
    from sentence_transformers import CrossEncoder

    return CrossEncoder(
        model_name,
        max_length=max_length,
    )
```

Modelo usado:

```text
BAAI/bge-reranker-v2-m3
```

---

## Nodo de reranking

La función principal utilizada por el grafo es:

```python
rerank_node(
    reranker,
    candidate_pool_size,
    final_top_k,
)
```

El nodo:

```text
1. toma state["documents"]
2. conserva como máximo candidate_pool_size
3. usa state["question"] como query
4. puntúa cada par (query, documento)
5. ordena por score descendente
6. conserva final_top_k
7. vuelve a escribir state["documents"]
```

---

## Texto enviado al Cross-Encoder

Cada documento puede incluir metadata normativa compacta:

```text
Fuente
Tipo normativo
Año
Título
Capítulo
Artículo
Parágrafo
Numeral
Literal
Tipo de fragmento
Tabla
Tablas relacionadas
```

seguida del contenido:

```text
Metadata normativa:
...

Contenido:
...
```

---

## Trace del reranking

El nodo registra:

```python
"reranking_trace": {
    "fallback": False,
    "candidate_count": ...,
    "selected_count": ...,
}
```

Si ocurre una excepción, utiliza un fallback conservador:

```python
"fallback": True
```

y conserva los primeros `final_top_k` documentos del candidate pool.

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
-------------------------- R2 HYBRID + RERANKING ---------------------------------------

Candidatos recibidos por reranker: 40
Documentos seleccionados: 8
Fallback: False
Documentos finales en state: 8
```

Esto confirmó:

```text
Hybrid Retrieval activo             = sí
Chroma activo                       = sí
BM25 activo                         = sí
RRF activo                          = sí
Candidatos antes del reranking      = 40
Cross-Encoder ejecutado             = sí
Fallback del reranker               = no
Documentos finales                  = 8
```

También se verificó que los documentos mantenían metadata como:

```text
['_retrieval_sources']
```

con valores tales como:

```text
['chroma', 'bm25']
['chroma']
```

lo que confirma que los documentos provinieron de la etapa híbrida anterior.

---

# Rendimiento observado

Durante la prueba manual se observó:

```text
No device provided, using cpu
```

Por tanto, el modelo:

```text
BAAI/bge-reranker-v2-m3
```

se ejecutó en CPU.

La etapa de reranking de los 40 candidatos tardó aproximadamente 41 segundos en esa prueba.

Esto no modifica la configuración de calidad de R2, pero debe considerarse al comparar posteriormente costo computacional y latencia.

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

El runner utiliza:

```python
from agents.consulta_normativa.langchain_rag.main import build_runtime
```

por lo que ejecuta directamente la configuración R2 activa.

Cada pregunta utiliza un `thread_id` independiente.

---

# Comando utilizado para generar el TSV

```bash
python evaluation/experiments/run_conjunto_b1.py \
  --dataset evaluation/datasets/conjunto_b_optim/conjunto_b1.json \
  --output evaluation/results/ares_runs/r2_hybrid_reranking.tsv \
  --reset
```

---

# TSV generado

Ruta:

```text
evaluation/results/ares_runs/r2_hybrid_reranking.tsv
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

# Estado final de R2

```text
Query Expansion                     = OFF
Dense Retrieval / Chroma            = ON
Sparse Retrieval / BM25             = ON
Reciprocal Rank Fusion              = ON
Cross-Encoder Reranking             = ON
Parent-Document Retrieval           = OFF
Business Context                    = OFF

HYBRID_CANDIDATE_TOP_K              = 40
HYBRID_RRF_K                        = 60
RERANKER_CANDIDATE_POOL_SIZE        = 40
RERANKER_MODEL_NAME                 = BAAI/bge-reranker-v2-m3
RERANKER_MAX_LENGTH                 = 512
RERANKER_FINAL_TOP_K                = 8
```

---

# Cómo restaurar R2 en el futuro

Si R2 resulta ganadora:

1. Mantener Hybrid Retrieval con Chroma + BM25 + RRF.
2. Configurar 40 candidatos por retriever.
3. Configurar `RRF_K = 60`.
4. Hacer que el Hybrid Retrieval entregue 40 candidatos al grafo.
5. Cargar `BAAI/bge-reranker-v2-m3`.
6. Insertar `rerank_node` después de `normalize_documents`.
7. Configurar `candidate_pool_size = 40`.
8. Configurar `final_top_k = 8`.
9. Mantener Parent-Document Retrieval y Query Expansion desactivados para reproducir exactamente la evaluación R2.

---

# Identificador experimental

```text
R2 — Hybrid Retrieval + Cross-Encoder Reranking
```

Resultado ARES:

```text
Pendiente de evaluación.
```
