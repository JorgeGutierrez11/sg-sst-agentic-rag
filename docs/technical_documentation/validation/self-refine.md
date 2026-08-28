# Self-Refine para respuestas normativas

Self-Refine valida la respuesta inicial generada por el RAG y, si detecta problemas, produce una versión refinada usando únicamente la pregunta original y el contexto normativo recuperado. La técnica se ejecuta después de `generate_answer` y antes de `format_result`.

La implementación sigue el patrón Self-Refine de retroalimentación y refinamiento, pero limita el proceso a **una sola iteración** para mantener controlados el coste y la latencia.

## Propósito

El baseline genera una respuesta final directamente desde el contexto recuperado. Self-Refine agrega una revisión posterior para detectar:

- afirmaciones no respaldadas por el contexto;
- contradicciones con la evidencia recuperada;
- omisiones de información disponible;
- citas `[n]` mal utilizadas;
- respuestas parciales presentadas como completas.

La técnica no realiza nuevo retrieval y no modifica los documentos recuperados. Solo puede conservar `state["answer"]` o reemplazarlo por una respuesta refinada.

## Ubicación en el pipeline LangGraph

En el flujo base con esta técnica, `self_refine` se ejecuta después de la generación inicial:

```text
retrieve -> normalize_documents -> record_retrieval_trace -> evidence_route
         -> format_context/build_messages/generate_answer/self_refine o fallback_answer
         -> format_result
```

Self-Refine solo corre en la rama con evidencia, porque necesita una respuesta inicial generada desde `state["context"]`. La rama `without_evidence` continúa usando `fallback_answer` directamente.

Archivos principales:

- `agents/consulta_normativa/langchain_rag/validation/self_refine.py`
- `agents/consulta_normativa/langchain_rag/graph.py`
- `agents/consulta_normativa/langchain_rag/core/state.py`
- `agents/consulta_normativa/tests/test_self_refine.py`

## Resumen de implementación

| Pieza | Responsabilidad |
|---|---|
| `SelfRefineFeedback` | Modelo Pydantic con la decisión de refinamiento, feedback e issues. |
| `self_refine_node(llm)` | Nodo LangGraph que coordina feedback, refinamiento y fallback. |
| `generate_self_refine_feedback(...)` | Invoca el grader estructurado sobre pregunta, contexto y respuesta inicial. |
| `generate_refined_answer(...)` | Genera una respuesta corregida cuando `needs_refinement=True`. |
| `build_feedback_messages(...)` | Construye los mensajes de evaluación. |
| `build_refinement_messages(...)` | Construye los mensajes de refinamiento. |
| `build_self_refine_trace(...)` | Centraliza el contrato completo de trazabilidad. |
| `self_refine_fallback(...)` | Conserva la respuesta inicial ante errores técnicos. |

El nodo usa `state["question"]`, `state["context"]` y `state["answer"]`. La pregunta evaluada es la original del usuario, no una posible `retrieval_query` intermedia.

## Flujo interno

```text
respuesta inicial -> feedback estructurado
                  -> si no requiere refinamiento: conservar respuesta inicial
                  -> si requiere refinamiento: generar respuesta refinada
```

La fase de feedback devuelve:

```python
class SelfRefineFeedback(BaseModel):
    needs_refinement: bool
    feedback: str
    issues: list[str]
```

Si `needs_refinement` es `False`, no se hace una segunda llamada de generación. Si es `True`, el refinador recibe la pregunta, el contexto, la respuesta inicial, el feedback y los issues detectados.

## Campos de estado

| Campo | Uso |
|---|---|
| `question` | Pregunta original usada para evaluar si la respuesta contestó lo solicitado. |
| `context` | Contexto numerado usado para generar y revisar la respuesta. |
| `answer` | Entrada: respuesta inicial. Salida: respuesta inicial o refinada. |
| `self_refine_trace` | Traza interna del proceso de feedback/refinamiento/fallback. |

`self_refine_trace` mantiene siempre el mismo contrato:

```python
{
    "initial_answer": "...",
    "needs_refinement": True,
    "refined": True,
    "feedback": "La respuesta debe corregir el plazo citado.",
    "issues": ["El plazo no coincide con el fragmento [1]."],
    "fallback": False,
    "error_stage": None,
    "error": None,
}
```

## Fallbacks y guardrails

Self-Refine usa política `fail-open`: un error técnico de esta etapa no debe borrar una respuesta ya generada.

| Caso | Comportamiento |
|---|---|
| Respuesta inicial vacía | Devuelve `answer` sin modificar y registra `EmptyInitialAnswer`. |
| Falla `with_structured_output(...)` | Conserva la respuesta inicial y marca `feedback_configuration`. |
| Falla la generación de feedback | Conserva la respuesta inicial y marca `feedback`. |
| `needs_refinement=False` | Conserva la respuesta inicial sin llamar al refinador. |
| Falla el refinamiento | Conserva la respuesta inicial y marca `refinement`. |
| Respuesta refinada vacía | La trata como error y conserva la respuesta inicial. |

La respuesta refinada no vuelve a pasar por un segundo ciclo de evaluación.


## Ejemplo de integración en LangGraph

Este ejemplo muestra el flujo base más el nuevo nodo. No incluye variantes adicionales como expansión de parent documents ni otras técnicas de validación.

```python
from agents.consulta_normativa.langchain_rag.validation.self_refine import self_refine_node


workflow.add_node("retrieve", retrieve_node(retriever, top_k))
workflow.add_node("normalize_documents", normalize_documents_node)
workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)
workflow.add_node("fallback_answer", fallback_answer_node)
workflow.add_node("format_context", format_context_node)
workflow.add_node("build_messages", build_messages_node)
workflow.add_node("generate_answer", generate_answer_node(llm))
workflow.add_node("self_refine", self_refine_node(llm))
workflow.add_node("format_result", format_result_node)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "normalize_documents")
workflow.add_edge("normalize_documents", "record_retrieval_trace")
workflow.add_conditional_edges(
    "record_retrieval_trace",
    evidence_route,
    {"with_evidence": "format_context", "without_evidence": "fallback_answer"},
)
workflow.add_edge("fallback_answer", "format_result")
workflow.add_edge("format_context", "build_messages")
workflow.add_edge("build_messages", "generate_answer")
workflow.add_edge("generate_answer", "self_refine")
workflow.add_edge("self_refine", "format_result")
workflow.add_edge("format_result", END)
```

## Notas operativas

- Agrega una llamada LLM de feedback por respuesta generada.
- Agrega una segunda llamada LLM solo cuando `needs_refinement=True`.
- Puede mejorar grounding y citas, pero no garantiza corrección normativa formal.
- No valida determinísticamente entailment ni citas; depende del comportamiento del modelo.
- Debe evaluarse de forma aislada frente al baseline para medir fidelidad, relevancia de respuesta, latencia y posibles regresiones.
