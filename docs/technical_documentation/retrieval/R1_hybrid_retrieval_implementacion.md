# R1 — Hybrid Retrieval: Chroma + BM25 + RRF

## Propósito

Este documento registra cómo quedó implementada la configuración **R1 — Hybrid Retrieval** para poder reconstruirla exactamente en el futuro si resulta ganadora en la evaluación con ARES.

R1 combina:

```text
Pregunta
  ├── Chroma / Dense ──┐
  │                    ├── Reciprocal Rank Fusion (RRF)
  └── BM25 / Sparse ───┘
                           ↓
                         Top-8
                           ↓
                       Generación
```

La técnica de Query Expansion permanece desactivada durante esta evaluación.  
Parent-Document Retrieval y Cross-Encoder Reranking también permanecen desactivados.

---

## Parámetros utilizados

Archivo:

```text
agents/consulta_normativa/langchain_rag/config.py
```

Configuración utilizada:

```python
RETRIEVAL_TOP_K = 8
DEFAULT_TOP_K = RETRIEVAL_TOP_K

RRF_K = 60

HYBRID_CANDIDATE_TOP_K = 40
HYBRID_RRF_K = RRF_K
```

Interpretación:

```text
Chroma / Dense candidatos = 40
BM25 / Sparse candidatos  = 40
RRF k                     = 60
Documentos finales        = 8
```

El corte final a 8 documentos ocurre después de la fusión RRF.

---

## Archivos involucrados

### 1. `config.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/config.py
```

Cambios relevantes:

```python
RETRIEVAL_TOP_K = 8
DEFAULT_TOP_K = RETRIEVAL_TOP_K

HYBRID_CANDIDATE_TOP_K = 40
HYBRID_RRF_K = RRF_K
```

Con:

```python
RRF_K = 60
```

---

### 2. `main.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/main.py
```

#### Imports de configuración

Se agregaron:

```python
HYBRID_CANDIDATE_TOP_K
HYBRID_RRF_K
```

Ejemplo:

```python
from agents.consulta_normativa.langchain_rag.config import (
    DEFAULT_CHROMA_PATH,
    DEFAULT_COLLECTION_NAME,
    DEFAULT_TOP_K,
    HYBRID_CANDIDATE_TOP_K,
    HYBRID_RRF_K,
)
```

#### `RuntimeDependencies`

La configuración activa para R1 requiere:

```python
open_existing_collection: Callable[[Any, str], Any]
open_existing_bm25_index: Callable[..., Any]
hybrid_retriever: Callable[..., Retriever]
```

No se utiliza el wrapper standalone:

```python
chroma_retriever
```

Esto **no elimina Chroma**. La colección Chroma continúa siendo usada directamente por `hybrid_retriever`.

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
)
```

---

## Construcción del retriever híbrido

Dentro de `build_runtime()` se mantiene la carga de Chroma:

```python
collection = dependencies.open_existing_collection(
    DEFAULT_CHROMA_PATH,
    DEFAULT_COLLECTION_NAME,
)
```

Después se carga el índice BM25:

```python
bm25_index = dependencies.open_existing_bm25_index()
```

Finalmente se construye R1:

```python
retriever = dependencies.hybrid_retriever(
    collection,
    bm25_index,
    candidate_top_k=HYBRID_CANDIDATE_TOP_K,
    rrf_k=HYBRID_RRF_K,
)
```

Ese `retriever` se entrega al grafo:

```python
graph = dependencies.build_langgraph_rag(
    llm,
    retriever,
    DEFAULT_TOP_K,
    checkpointer=checkpointer,
    store=memory_store,
)
```

---

## `graph.py`

Ruta:

```text
agents/consulta_normativa/langchain_rag/graph.py
```

**No fue necesario modificar el grafo para implementar R1.**

El nodo de retrieval continúa siendo genérico:

```python
def retrieve_node(
    retriever: Retriever,
    top_k: int,
) -> Callable[[RagGraphState], RagGraphState]:

    def run(state: RagGraphState) -> RagGraphState:
        retrieval_query = state.get("retrieval_query") or state["question"]
        return {"raw_results": retriever(retrieval_query, top_k)}

    return run
```

Como Query Expansion está desactivada, `retrieval_query` no es escrito por ningún nodo y el flujo utiliza:

```python
state["question"]
```

La arquitectura del grafo permanece:

```text
START
  ↓
retrieve
  ↓
normalize_documents
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
```

---

## Funcionamiento interno esperado de R1

`hybrid_retriever` recibe:

```text
dense_collection = colección Chroma
sparse_index     = índice BM25
candidate_top_k  = 40
rrf_k            = 60
```

La secuencia es:

```text
1. Consultar Chroma con top-40.
2. Consultar BM25 con top-40.
3. Normalizar ambos rankings.
4. Fusionar los rankings con Reciprocal Rank Fusion.
5. Entregar al grafo los documentos mejor posicionados.
6. El grafo conserva los primeros DEFAULT_TOP_K = 8.
```

---

## Verificación manual realizada

Comando:

```bash
python -m agents.consulta_normativa.langchain_rag.main
```

Pregunta utilizada:

```text
que es el SG-SST?
```

Resultado de depuración:

```text
-------------------------- R1 HYBRID RETRIEVAL ---------------------------------------
Documentos finales: 8

Documento 1
Fuentes retrieval: ['chroma', 'bm25']

Documento 2
Fuentes retrieval: ['chroma', 'bm25']

Documento 3
Fuentes retrieval: ['chroma', 'bm25']

Documento 4
Fuentes retrieval: ['chroma', 'bm25']

Documento 5
Fuentes retrieval: ['chroma', 'bm25']

Documento 6
Fuentes retrieval: ['chroma', 'bm25']

Documento 7
Fuentes retrieval: ['chroma', 'bm25']

Documento 8
Fuentes retrieval: ['chroma', 'bm25']
```

La prueba confirmó:

```text
Chroma activo          = sí
BM25 activo            = sí
RRF activo             = sí
Documentos finales     = 8
Errores de ejecución   = ninguno
```

---

## Dataset utilizado para evaluación

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

Cada pregunta utiliza un `thread_id` diferente en el runner B1 para evitar contaminación de contexto conversacional.

---

## Runner utilizado

Archivo:

```text
evaluation/experiments/run_conjunto_b1.py
```

El runner importa directamente:

```python
from agents.consulta_normativa.langchain_rag.main import build_runtime
```

Por tanto, utiliza la configuración R1 activa en `main.py`.

El TSV generado contiene exactamente:

```text
Query
Document
Answer
```

---

## Comando utilizado para generar el TSV

```bash
python evaluation/experiments/run_conjunto_b1.py \
  --dataset evaluation/datasets/conjunto_b_optim/conjunto_b1.json \
  --output evaluation/results/ares_runs/r1_hybrid_retrieval.tsv \
  --reset
```

---

## TSV generado

Ruta:

```text
evaluation/results/ares_runs/r1_hybrid_retrieval.tsv
```

Validación realizada:

```text
Registros de evaluación = 80
Columnas                 = Query, Document, Answer
Filas mal formadas       = 0
Campos vacíos            = 0
Queries duplicadas       = 0
```

Este archivo queda listo para evaluación con ARES.

---

## Estado final de R1

```text
Query Expansion               = OFF
Dense Retrieval / Chroma      = ON
Sparse Retrieval / BM25       = ON
Reciprocal Rank Fusion        = ON
Cross-Encoder Reranking       = OFF
Parent-Document Retrieval     = OFF
Business Context              = OFF
final_top_k                   = 8
```

---

## Cómo restaurar R1 en el futuro

Si R1 resulta ganadora, para reconstruirla se debe:

1. Configurar `DEFAULT_TOP_K = 8`.
2. Configurar `HYBRID_CANDIDATE_TOP_K = 40`.
3. Configurar `HYBRID_RRF_K = 60`.
4. Abrir la colección Chroma.
5. Abrir el índice BM25.
6. Construir `hybrid_retriever(collection, bm25_index, candidate_top_k=40, rrf_k=60)`.
7. Entregar ese retriever a `build_langgraph_rag`.
8. Mantener Query Expansion, Reranking y Parent-Document desactivados si se desea reproducir exactamente la evaluación R1.

---

## Identificador experimental

```text
R1 — Hybrid Retrieval: Dense + BM25 + RRF
```

Resultado ARES:

```text
Pendiente de evaluación.
```
