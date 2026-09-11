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
"""LangGraph RAG flow for normative consultation."""

from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.config import DEFAULT_TOP_K
from agents.consulta_normativa.langchain_rag.core.instrumentation import record_retrieval_trace_node
from agents.consulta_normativa.langchain_rag.core.llm import invoke_llm_text
from agents.consulta_normativa.langchain_rag.core.routes import evidence_route
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState
from agents.consulta_normativa.langchain_rag.formatting import build_context, build_references, recovered_documents
from agents.consulta_normativa.langchain_rag.models import LangChainRagResult
from agents.consulta_normativa.langchain_rag.prompts import BASE_SYSTEM_INSTRUCTIONS, build_base_prompt, build_human_prompt

# importar nodo de perfil de negocio y nodo de historial de conversación
from agents.consulta_normativa.langchain_rag.business_context.profile_node import (business_profile_node)
from agents.consulta_normativa.langchain_rag.business_context.history_node import (save_conversation_turn_node)
# tecnica self-refine
from agents.consulta_normativa.langchain_rag.validation.self_refine import (self_refine_node)


Retriever = Callable[[str, int], dict[str, Any]] 

# se agregó checkpointer: Any | None = None, para permitir la integración con un sistema de checkpointing
def build_langgraph_rag(llm: Any, retriever: Retriever, top_k: int = DEFAULT_TOP_K, checkpointer: Any | None = None,) -> Any:
    """Build the LangGraph RAG pipeline with explicit evidence branching."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)
    

    workflow.add_node("business_profile", business_profile_node(llm)) # Agregar nodo de perfil de negocio
  
    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)
    workflow.add_node("record_retrieval_trace",record_retrieval_trace_node)
    

    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)

   


    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))

    # Agregar Self-Refine
    workflow.add_node("self_refine",self_refine_node(llm),)

    workflow.add_node("save_conversation_turn", save_conversation_turn_node) # Agregar nodo de historial de conversación


    workflow.add_node("format_result", format_result_node)

    # Construccion del grafo
    #workflow.set_entry_point("retrieve")
    workflow.set_entry_point("business_profile")
    workflow.add_edge("business_profile", "retrieve")
    
    
    workflow.add_edge("retrieve", "normalize_documents")
    workflow.add_edge("normalize_documents", "record_retrieval_trace")

    
    workflow.add_conditional_edges(
        "record_retrieval_trace",
        evidence_route,
        {"with_evidence": "format_context", "without_evidence": "fallback_answer"},)
    

    
    workflow.add_edge("fallback_answer","save_conversation_turn")

    workflow.add_edge("format_context", "build_messages") 



    workflow.add_edge("build_messages", "generate_answer")

    workflow.add_edge("generate_answer","self_refine") # nuevo
    workflow.add_edge("self_refine", "save_conversation_turn") # nuevo
    workflow.add_edge("save_conversation_turn","format_result")


    workflow.add_edge("format_result", END)
    return workflow.compile(checkpointer=checkpointer,) #se agregó checkpointer=checkpointer, para permitir la integración con un sistema de checkpointing

# se agregó thread_id: str | None = None,
def answer_with_langgraph(question: str, graph: Any, thread_id: str | None = None,) -> LangChainRagResult:
    """Run a compiled LangGraph-like object and return its RAG result."""

    if thread_id is None:
        state = graph.invoke({"question": question}) # si no hay un thread_id, se invoca el grafo sin configuración adicional
    else:
        state = graph.invoke({"question": question},{"configurable": {"thread_id": thread_id,}},) #se agrea por si hay un thread_id, se pasa como parte de la configuración del grafo

    result = state.get("result") if isinstance(state, dict) else None
    if not isinstance(result, LangChainRagResult):
        raise ValueError("LangGraph execution did not produce a LangChainRagResult.")
    return result


def retrieve_node(retriever: Retriever, top_k: int) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that retrieves raw Chroma-like results."""

    def run(state: RagGraphState) -> RagGraphState:
        retrieval_query = state.get("retrieval_query") or state["question"]
        return {"raw_results": retriever(retrieval_query, top_k)}

    return run


def normalize_documents_node(state: RagGraphState) -> RagGraphState:
    """Normalize raw retrieval output into retrieved documents."""

    return {"documents": recovered_documents(state.get("raw_results", {}))}


def fallback_answer_node(state: RagGraphState) -> RagGraphState:
    """Return the deterministic manual fallback without invoking the LLM."""
    context = "No se recuperó contexto."

    return {
        "context": context,
        "references": [],
        "prompt": build_base_prompt(state["question"], context),
        "answer": fallback_answer(context, []),
    }


def format_context_node(state: RagGraphState) -> RagGraphState:
    """Build context and references from retrieved documents."""

    documents = state.get("documents", [])
    return {
        "context": build_context(documents),
        "references": build_references(documents),
    }


def build_messages_node(state: RagGraphState) -> RagGraphState:
    """Build LangChain chat messages equivalent to the manual prompt input."""

    try:
        # pyrefly: ignore [missing-import]
        from langchain_core.messages import HumanMessage, SystemMessage
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langchain is not installed: {error}") from error

    context = state["context"]
    return {
        "messages": [
            SystemMessage(content=BASE_SYSTEM_INSTRUCTIONS),
            HumanMessage(content=build_human_prompt(state["question"], context)),
        ],
        "prompt": build_base_prompt(state["question"], context),
    }


def generate_answer_node(llm: Any) -> Callable[[RagGraphState], RagGraphState]:
    """Build a graph node that invokes the LLM with LangChain messages."""

    def run(state: RagGraphState) -> RagGraphState:
        return {"answer": invoke_llm_text(llm, state["messages"])}

    return run


def fallback_answer(context: str, references: list[str]) -> str:
    """Replicate the manual deterministic fallback answer exactly."""

    if context == "No se recuperó contexto.":
        return "La evidencia recuperada es insuficiente para responder la pregunta."
    return "\n".join(["Borrador fundamentado solo en el contexto recuperado:", context, "Referencias:", *references])


def format_result_node(state: RagGraphState) -> RagGraphState:
    """Build the public result object from graph state."""

    return {
        "result": LangChainRagResult(
            answer=state["answer"],
            references=state.get("references", []),
            context=state["context"],
            prompt=state["prompt"],
        )
    }

```

## Notas operativas

- Agrega una llamada LLM de feedback por respuesta generada.
- Agrega una segunda llamada LLM solo cuando `needs_refinement=True`.
- Puede mejorar grounding y citas, pero no garantiza corrección normativa formal.
- No valida determinísticamente entailment ni citas; depende del comportamiento del modelo.
- Debe evaluarse de forma aislada frente al baseline para medir fidelidad, relevancia de respuesta, latencia y posibles regresiones.


# ver rusltados de la tecnica
En main.py, después de obtener el snapshot, agrega temporalmente:
```python
self_refine_trace = snapshot.values.get(
    "self_refine_trace",
    {},
)

print("\n--- SELF REFINE TRACE -----------------------------------------------------")
print(self_refine_trace)
print("--- END SELF REFINE TRACE -------------------------------------------------\n")
```