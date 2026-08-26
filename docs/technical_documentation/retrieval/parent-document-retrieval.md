# Parent-Document Retrieval para recuperación normativa small-to-big

Parent-Document Retrieval es una técnica de recuperación small-to-big: recupera candidatos pequeños e indexables desde Chroma o Hybrid Retrieval, identifica los `child_chunk` recuperados y los reemplaza por su `parent_chunk` completo antes de construir el contexto enviado al LLM.

## Propósito

El objetivo no es recuperar más documentos ni regenerar chunks. El objetivo es conservar la precisión de búsqueda de los child chunks y entregar al modelo una unidad normativa más completa para responder con mejor contexto.

La técnica opera solo en tiempo de consulta: carga los parent chunks existentes desde JSONL, mantiene un lookup por `chunk_id` y expande únicamente los resultados cuyo `document_type` es `child_chunk` y tienen `parent_id`.

## Ubicación en el pipeline LangGraph

El grafo normaliza los resultados recuperados y luego aplica la expansión parent-document antes de registrar trazas, construir referencias y formar el contexto final.

```text
question -> retrieve -> normalize_documents -> expand_parent_documents
         -> record_retrieval_trace
         -> format_context/build_messages/generate_answer o fallback_answer
         -> format_result
```

La posición es importante: Parent-Document Retrieval no cambia el retriever inicial. El retriever sigue devolviendo candidatos pequeños; la expansión ocurre después, sobre `state["documents"]`, para que los nodos posteriores trabajen con el texto completo del parent cuando corresponde.

Archivos principales:

- `agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py`
- `agents/consulta_normativa/langchain_rag/graph.py`
- `agents/consulta_normativa/langchain_rag/main.py`
- `agents/consulta_normativa/langchain_rag/config.py`
- `pipeline/chunking/core/io_jsonl.py`
- `data/processed/chunks/parents.jsonl`

## Resumen de implementación

La técnica se divide en estas piezas:

| Pieza | Responsabilidad |
|---|---|
| `load_parent_documents(parents_path)` | Valida que exista el JSONL de parents y carga los parent chunks con `read_parent_chunks(...)`. |
| `build_parent_lookup(records, parents_path)` | Construye un diccionario `parent_id -> RetrievedDocument` usando el `chunk_id` del parent como llave. |
| `parent_metadata(record, chunk_id)` | Aplana metadata útil del parent para referencias, contexto y trazabilidad. Lee la estructura real `metadata.inherited` y `metadata.chunk`. |
| `expand_parent_documents(documents, parent_lookup)` | Reemplaza cada child recuperado por su parent completo, preserva el orden del ranking y deduplica parents repetidos. |
| `expanded_parent_document(parent, child, parent_id, child_id)` | Crea el documento parent expandido y agrega metadata técnica sobre el child que disparó la expansión. |
| `with_missing_parent_fallback(document)` | Conserva el child original cuando su `parent_id` no existe en el lookup y marca el fallback. |

El contrato interno se mantiene estable: los nodos posteriores siguen leyendo `state["documents"]` como una lista de `RetrievedDocument`.

## Parámetros de configuración

Valores relevantes definidos o importados desde `agents/consulta_normativa/langchain_rag/config.py`:

| Parámetro | Uso |
|---|---|
| `DEFAULT_PARENT_CHUNKS_PATH` | Ruta del JSONL canónico de parent chunks. Apunta al artefacto generado por la fase de chunking. |
| `RETRIEVAL_TOP_K` | Cantidad final de documentos solicitados al retriever antes de la expansión parent-document. |

El archivo de parents se genera antes del runtime con el flujo de corpus:

```bash
python -m pipeline.chunking.main build-parents
```

## Decisiones y guardrails importantes

| Aspecto | Implementación actual |
|---|---|
| Técnica small-to-big | La búsqueda ocurre sobre chunks pequeños; el contexto final puede usar el parent completo. |
| Expansión selectiva | Solo se expanden documentos con `document_type == "child_chunk"` y `parent_id` no vacío. |
| Tablas preservadas | Los documentos tipo `table` no se expanden ni se reemplazan. |
| Sin truncación adicional | El parent se entrega completo; no existe un límite runtime como `MAX_EXPANDED_PARENTS`. |
| Orden de ranking | El primer child que apunta a un parent define la posición del parent expandido. |
| Deduplicación | Si varios child chunks apuntan al mismo parent, se devuelve un solo parent y se acumulan los ids de children. |
| Identidad de parent | El lookup usa el `chunk_id` del parent, que debe coincidir con el `parent_id` de los child chunks. |
| Metadata real del corpus | Los campos heredados se leen desde `metadata.inherited`; estrategia y tablas desde `metadata.chunk`. |
| Falla de preparación | Si `parents.jsonl` no existe, el loader falla explícitamente con `FileNotFoundError`. |

## Metadata interna

| Campo | Uso |
|---|---|
| `document_id` | Identidad del parent expandido. Corresponde al `chunk_id` del parent. |
| `document_type` | Tipo del documento final. Para parents expandidos queda como `parent_chunk`. |
| `source_document_id` | Documento normativo fuente del parent. |
| `source_stem` | Nombre lógico de la fuente normativa. |
| `normative_document_type` | Tipo normativo heredado, por ejemplo `decreto`, `ley` o `resolución`. |
| `article`, `articles`, `chapter`, `paragraph`, `numeral`, `literal` | Ubicación normativa heredada desde el parent chunk. |
| `has_tables` | Indica si el parent referencia tablas. |
| `table_keys` | Claves lógicas de tablas en formato `source_stem:table_index`. |
| `parent_strategy` | Estrategia con la que se generó el parent chunk. |
| `parent_expansion_applied` | Indica que el documento final fue reemplazado por su parent. |
| `expanded_parent_id` | Id del parent usado en la expansión. |
| `expanded_from_child_id` | Primer child chunk que disparó la expansión. |
| `expanded_from_child_ids` | Lista de todos los child chunks recuperados que apuntaban al mismo parent. |
| `expanded_from_document_type` | Tipo del documento recuperado originalmente, normalmente `child_chunk`. |
| `parent_expansion_fallback` | Motivo por el que no se expandió un child cuando aplica fallback. |

Estos campos son metadata técnica para trazabilidad y evaluación. No deben interpretarse como evidencia normativa por sí mismos; la evidencia normativa es el texto recuperado y sus referencias.

## Fallos y comportamiento fallback

Parent-Document Retrieval conserva comportamiento explícito ante entradas incompletas:

- si `parent_lookup` es `None`, el nodo del grafo no modifica `documents`;
- si un documento no es `child_chunk`, se conserva igual;
- si un child no tiene `parent_id`, se conserva igual;
- si un child tiene `parent_id` pero el parent no existe en el lookup, se conserva el child y se agrega `parent_expansion_fallback = "missing_parent"`;
- si el JSONL de parents no existe, `load_parent_documents(...)` falla con `FileNotFoundError`;
- si un parent record no tiene `chunk_id` o `text`, el loader falla con `ValueError`.


## Ejemplo de integración
### Integracion en main.py

```python
from agents.consulta_normativa.langchain_rag.config import (
    DEFAULT_COLLECTION_NAME,
    DEFAULT_CHROMA_PATH,
    DEFAULT_PARENT_CHUNKS_PATH,
    RETRIEVAL_TOP_K,
)
from agents.consulta_normativa.langchain_rag.graph import build_langgraph_rag
from agents.consulta_normativa.langchain_rag.retrieval.parent_document_retrieval import load_parent_documents
from agents.shared.chroma_retrieval import chroma_retriever, open_existing_collection

collection = open_existing_collection(DEFAULT_CHROMA_PATH, DEFAULT_COLLECTION_NAME)
retriever = chroma_retriever(collection)
parent_lookup = load_parent_documents(DEFAULT_PARENT_CHUNKS_PATH)

graph = build_langgraph_rag(
    llm,
    retriever,
    top_k=RETRIEVAL_TOP_K,
    parent_lookup=parent_lookup,
)
```
En el runtime actual, `main.py` carga el lookup de parents y lo pasa al grafo durante la inicialización. Si `parent_lookup=None`, el grafo conserva el comportamiento sin expansión.

### Integracion en graph.py


```python
def build_langgraph_rag(
    llm: Any,
    retriever: Retriever,
    top_k: int = RETRIEVAL_TOP_K,
    parent_lookup: dict[str, RetrievedDocument] | None = None,
) -> Any:
    """Build the LangGraph RAG pipeline with explicit evidence branching."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)

    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)
    workflow.add_node("expand_parent_documents", expand_parent_documents_node(parent_lookup))
    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)
    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)
    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))
    workflow.add_node("format_result", format_result_node)

    # Construccion del grafo
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "normalize_documents")
    workflow.add_edge("normalize_documents", "expand_parent_documents")
    workflow.add_edge("expand_parent_documents", "record_retrieval_trace")
    workflow.add_conditional_edges(
        "record_retrieval_trace",
        evidence_route,
        {"with_evidence": "format_context", "without_evidence": "fallback_answer"},
    )
    workflow.add_edge("fallback_answer", "format_result")
    workflow.add_edge("format_context", "build_messages")
    workflow.add_edge("build_messages", "generate_answer")
    workflow.add_edge("generate_answer", "format_result")
    workflow.add_edge("format_result", END)
    return workflow.compile()


def expand_parent_documents_node(
    parent_lookup: dict[str, RetrievedDocument] | None,
) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that optionally expands child chunks to parent chunks."""

    def run(state: RagGraphState) -> RagGraphState:
        if parent_lookup is None:
            return {}
        return {"documents": expand_parent_documents(state.get("documents", []), parent_lookup)}

    return run
```
