# Retrieval Relevance Grading para evidencia normativa

Retrieval Relevance Grading valida si cada documento recuperado aporta evidencia útil para responder la pregunta original del usuario. La técnica filtra documentos irrelevantes antes de construir el contexto que recibirá el LLM.

La implementación está inspirada en el *retrieval evaluator* de Corrective Retrieval-Augmented Generation (CRAG), pero no implementa CRAG completo.

## Propósito

El baseline del RAG considera que hay evidencia cuando Chroma devuelve al menos un documento. Ese criterio puede dejar pasar fragmentos semánticamente cercanos, pero inútiles para la pregunta.

Esta técnica agrega una validación explícita:

```text
pregunta original + documento recuperado -> relevance grader -> conservar o filtrar
```

Evalúa **relevancia**, no suficiencia. Un documento puede ser relevante aunque solo responda una parte de la pregunta o necesite complementarse con otros fragmentos.

## Ubicación en el pipeline LangGraph

En el flujo base con esta técnica, el grader se ejecuta después de normalizar documentos y antes de registrar/enrutar la evidencia:

```text
retrieve -> normalize_documents -> retrieval_relevance_grading -> record_retrieval_trace
         -> evidence_route -> format_context/build_messages/generate_answer o fallback_answer
         -> format_result
```

`retrieval_relevance_grading` modifica `state["documents"]`: conserva los documentos aceptados y elimina los rechazados. Luego `evidence_route` puede reutilizar el contrato existente: si queda al menos un documento, continúa con generación; si no queda evidencia utilizable, usa fallback.

Archivos principales:

- `agents/consulta_normativa/langchain_rag/validation/retrieval_relevance_grading.py`
- `agents/consulta_normativa/langchain_rag/graph.py`
- `agents/consulta_normativa/langchain_rag/core/state.py`
- `agents/consulta_normativa/tests/test_retrieval_relevance_grading.py`

## Resumen de implementación

| Pieza | Responsabilidad |
|---|---|
| `RelevanceGrade` | Modelo Pydantic con `relevant: bool` y `reason: str`. |
| `retrieval_relevance_grading_node(llm)` | Nodo LangGraph que evalúa documentos, filtra irrelevantes y escribe trazas. |
| `grade_document_relevance(...)` | Invoca el grader estructurado para un documento. |
| `build_relevance_grading_messages(...)` | Construye los mensajes con pregunta original, metadata y contenido. |
| `format_relevance_metadata(...)` | Selecciona metadata normativa útil para el juicio. |
| `relevance_grading_fallback(...)` | Conserva documentos cuando falla la configuración del grader. |

El grader usa `state["question"]`, no `state["retrieval_query"]`, porque la relevancia se evalúa contra la necesidad original del usuario.

## Criterios de relevancia

Un documento es **relevante** cuando contiene información normativa que contribuye directamente a responder al menos una parte de la pregunta.

Un documento es **no relevante** cuando:

- solo comparte vocabulario general de SG-SST;
- menciona términos de la pregunta sin aportar evidencia útil;
- trata una obligación, sujeto, procedimiento o situación diferente;
- pertenece a la misma norma, pero el fragmento concreto no ayuda a responder;
- requiere inferencias no respaldadas por su contenido.

La pertenencia al dominio SG-SST o la coincidencia léxica no bastan para conservar un documento.

## Campos de estado

| Campo | Uso |
|---|---|
| `question` | Pregunta original usada por el grader. |
| `documents` | Entrada: documentos recuperados. Salida: documentos conservados. |
| `relevance_grading_trace` | Conteos y decisiones por documento. |
| `retrieval_traces` | Trazas posteriores de recuperación/evidencia usadas por el grafo. |

Ejemplo de `relevance_grading_trace`:

```python
{
    "input_count": 5,
    "relevant_count": 3,
    "rejected_count": 2,
    "fallback_count": 0,
    "documents": [
        {
            "index": 0,
            "chroma_id": "...",
            "source": "resolucion_1401_2007",
            "article": "6",
            "relevant": True,
            "reason": "El fragmento indica responsabilidades sobre investigación de accidentes.",
            "fallback": False,
            "error": None,
        }
    ],
}
```

## Fallbacks y guardrails

La técnica usa una política conservadora: un fallo técnico del grader no debe descartar evidencia normativa potencialmente válida.

| Caso | Comportamiento |
|---|---|
| No hay documentos | Devuelve `documents=[]` y traza con conteos en cero. |
| Falla `with_structured_output(...)` | Conserva todos los documentos y marca fallback global. |
| Falla un documento individual | Conserva ese documento y marca fallback individual. |
| Todos son rechazados | Conserva el primer documento original como fallback conservador. |

El último guardrail evita que un juicio LLM convierta una recuperación no vacía en ausencia total de evidencia.


## Ejemplo de integración en LangGraph

Este ejemplo muestra el flujo base más el nuevo nodo. No incluye variantes adicionales como expansión de parent documents.

```python
from agents.consulta_normativa.langchain_rag.validation.retrieval_relevance_grading import (
    retrieval_relevance_grading_node,
)


workflow.add_node("retrieve", retrieve_node(retriever, top_k))
workflow.add_node("normalize_documents", normalize_documents_node)
workflow.add_node("retrieval_relevance_grading", retrieval_relevance_grading_node(llm))
workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)
workflow.add_node("fallback_answer", fallback_answer_node)
workflow.add_node("format_context", format_context_node)
workflow.add_node("build_messages", build_messages_node)
workflow.add_node("generate_answer", generate_answer_node(llm))
workflow.add_node("format_result", format_result_node)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "normalize_documents")
workflow.add_edge("normalize_documents", "retrieval_relevance_grading")
workflow.add_edge("retrieval_relevance_grading", "record_retrieval_trace")
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
```

## Notas operativas

- La técnica puede realizar una llamada LLM adicional por documento recuperado.
- No es reranking: no reordena documentos ni calcula scores calibrados.
- No reemplaza un `Sufficient Context Gate`: conservar documentos relevantes no prueba que el conjunto baste para responder toda la pregunta.
- Debe evaluarse de forma aislada frente al baseline para medir precisión, recall, latencia y efecto en fidelidad de respuesta.
