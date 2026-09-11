# Full Conversation Memory

## Técnica

**Full Conversation Memory** es la primera técnica implementada para la dimensión de contexto empresarial.

Ubicación:

```text
business_context/techniques/full_conversation_memory.py
```

Su función es construir:

```python
business_context["current_context"]
```

utilizando:

```text
perfil empresarial
+
historial completo de conversaciones anteriores
```

No resume, selecciona ni recupera recuerdos.

---

## Implementación

Se agregó:

```python
build_full_conversation_context(...)
```

La función recibe `BusinessContext` y genera un contexto textual con dos secciones:

```text
PERFIL EMPRESARIAL

HISTORIAL DE CONVERSACIÓN
```

Ejemplo:

```text
PERFIL EMPRESARIAL
- Actividad económica: Mantenimiento de motocicletas
- Número de trabajadores: 8
- Clase de riesgo: I

HISTORIAL DE CONVERSACIÓN
Turno 1
Usuario: Tenemos 8 trabajadores.
Agente: ...

Turno 2
Usuario: Un trabajador sufrió una fractura.
Agente: ...
```

El resultado se almacena en:

```python
business_context["current_context"]
```

---

## Nodo LangGraph

Se agregó:

```python
full_conversation_memory_node(...)
```

El nodo fue conectado después de `business_profile`:

```text
business_profile
       ↓
full_conversation_memory
       ↓
retrieve
```

**Motivo:** primero se actualiza el perfil con información del mensaje actual y después se construye el contexto empresarial.

El historial usado por la técnica corresponde a los turnos anteriores. El turno actual se guarda al final mediante:

```python
save_conversation_turn_node
```

---

## Persistencia

La técnica utiliza el `BusinessContext` persistido por LangGraph mediante:

```text
checkpointer + thread_id
```

Esto permite que una segunda pregunta tenga acceso al perfil y al historial generados durante preguntas anteriores.

Conversaciones con diferentes `thread_id` permanecen aisladas.

---

## Alcance

La técnica termina en:

```python
state["business_context"]["current_context"]
```

Actualmente no modifica:

- la consulta de retrieval;
- Query Rewriting;
- documentos recuperados;
- generación de la respuesta.

**Motivo:** la dimensión de contexto empresarial produce contexto; otras dimensiones deciden cómo consumirlo.

---

## Validación

Se probaron:

- perfil + historial;
- historial sin perfil;
- contexto vacío;
- ausencia de mutación del estado original;
- ejecución del nodo;
- persistencia entre turnos;
- presencia del turno anterior en `current_context`;
- integración con la CLI.

La implementación quedó integrada sin regresiones en la suite actual de `langchain_rag`.



# main.py

```python
"""Direct executable entrypoint for the experimental LangChain RAG variant."""

from __future__ import annotations
from uuid import uuid4 # nuevo import para generar un identificador único para cada hilo de conversación

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agents.consulta_normativa.langchain_rag.config import DEFAULT_CHROMA_PATH, DEFAULT_COLLECTION_NAME, DEFAULT_TOP_K

OPERATIONAL_ERROR_CODE = 2

Retriever = Callable[[str, int], dict[str, Any]]


class OperationalError(Exception):
    """Controlled error for expected runtime setup and execution failures."""


@dataclass(frozen=True)
class RuntimeDependencies:
    """Lazy-loaded dependencies required by the executable RAG flow."""

    build_deepseek_llm: Callable[[], Any]
    #build_langgraph_rag: Callable[[Any, Retriever, int], Any]
    #answer_with_langgraph: Callable[[str, Any], Any]
    build_langgraph_rag: Callable[..., Any] # La firma anterior ya quedó obsoleta porque ahora ambas funciones aceptan parámetros adicionales.
    answer_with_langgraph: Callable[..., Any]
    chroma_retriever: Callable[[Any], Retriever]
    open_existing_collection: Callable[[Any, str], Any]


@dataclass(frozen=True)
class RagRuntime:
    """Reusable runtime built once for direct or interactive execution."""

    #answer_with_langgraph: Callable[[str, Any], Any]
    answer_with_langgraph: Callable[..., Any]
    graph: Any
    thread_id: str


def main(argv: list[str] | None = None) -> int:
    """Run the direct experimental LangChain RAG entrypoint."""

    parser = argparse.ArgumentParser(prog="python -m agents.consulta_normativa.langchain_rag.main")
    parser.add_argument("question", nargs="?", help="Optional question to answer once before exiting.")
    args = parser.parse_args(argv)

    try:
        runtime = build_runtime()
    except OperationalError as error:
        return fail("initialization", error)
    except Exception as error:  # noqa: BLE001 - CLI must never print traceback for operational setup failures.
        return fail("initialization", OperationalError(str(error)))

    if args.question:
        return run_once(runtime, args.question)
    return run_interactive_loop(runtime)


def build_runtime() -> RagRuntime:
    """Build the Chroma retriever and DeepSeek-backed LLM for the session."""

    dependencies = load_dependencies()

    try:
        llm = dependencies.build_deepseek_llm()
    except Exception as error:  # noqa: BLE001 - keep missing key/package/provider errors controlled.
        raise OperationalError(str(error)) from error

    try:
        from langgraph.checkpoint.memory import InMemorySaver # nuevo import para el checkpointer de memoria
        
        collection = dependencies.open_existing_collection(DEFAULT_CHROMA_PATH, DEFAULT_COLLECTION_NAME)
        retriever = dependencies.chroma_retriever(collection)

        checkpointer = InMemorySaver() # nuevo checkpointer de memoria
        graph = dependencies.build_langgraph_rag(llm, retriever, DEFAULT_TOP_K, checkpointer=checkpointer)

        # Guardar diagrama en disco
        png_bytes = graph.get_graph().draw_mermaid_png()
        with open("data/images/base_rag_graph.png", "wb") as f:
            f.write(png_bytes)

        print("Grafo guardado exitosamente como 'base_rag_graph.png'")
    except Exception as error:  # noqa: BLE001 - Chroma path, package, and collection failures are operational.
        raise OperationalError(str(error)) from error
    
    thread_id = f"cli-session-{uuid4()}" # Generar un identificador único para cada hilo de conversación
    return RagRuntime(
        answer_with_langgraph=dependencies.answer_with_langgraph,
        graph=graph,
        thread_id=thread_id, # Agregar el identificador único al runtime para su uso en la conversación
    )


def load_dependencies() -> RuntimeDependencies:
    """Load optional runtime dependencies lazily so failures stay controlled."""

    try:
        from agents.consulta_normativa.langchain_rag.core.llm import build_deepseek_llm
        from agents.consulta_normativa.langchain_rag.graph import answer_with_langgraph, build_langgraph_rag
        from agents.consulta_normativa.manual_implementation.rag_base import chroma_retriever
        from agents.consulta_normativa.langchain_rag.retrieval.chroma_retrieval import open_existing_collection
    except ModuleNotFoundError as error:
        raise OperationalError(f"Required runtime dependency is not installed: {error}") from error

    return RuntimeDependencies(
        build_deepseek_llm=build_deepseek_llm,
        build_langgraph_rag=build_langgraph_rag,
        answer_with_langgraph=answer_with_langgraph,
        chroma_retriever=chroma_retriever,
        open_existing_collection=open_existing_collection,
    )


def run_interactive_loop(runtime: RagRuntime) -> int:
    """Read questions until the user exits."""

    print("Experimental LangChain RAG ready. Type 'exit' or 'quit' to leave.")
    while True:
        try:
            question = input("Question> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            return 0

        run_once(runtime, question)


def run_once(runtime: RagRuntime, question: str) -> int:
    """Answer one question and keep expected failures controlled."""

    try:
        result = runtime.answer_with_langgraph(question, runtime.graph, thread_id=runtime.thread_id) # Pasar el thread_id al llamar a answer_with_langgraph
    except Exception as error:  # noqa: BLE001 - direct CLI should report RAG failures without traceback.
        return fail("RAG execution", OperationalError(str(error)))

    print_answer(result.answer, result.references)

    # DEBUG: mostrar current_context generado por la técnica
    snapshot = runtime.graph.get_state(
        {
            "configurable": {
                "thread_id": runtime.thread_id,
            }
        }
    )

    business_context = snapshot.values.get(
        "business_context",
        {},
    )

    current_context = business_context.get(
        "current_context",
        "",
    )

    print("\n--- CURRENT BUSINESS CONTEXT ---")
    print(current_context or "[vacío]")
    print("--- END CURRENT BUSINESS CONTEXT ---\n")


    return 0


def print_answer(answer: str, references: list[str]) -> None:
    """Print the answer and its source references."""

    print("Answer:")
    print(answer)
    if references:
        print()
        print("References:")
        for reference in references:
            print(f"- {reference}")


def fail(stage: str, error: Exception) -> int:
    """Print one controlled operational error and return the CLI error code."""

    print(f"Error during {stage}:", file=sys.stderr)
    print(str(error), file=sys.stderr)
    return OPERATIONAL_ERROR_CODE


if __name__ == "__main__":
    raise SystemExit(main())

```

# graph.py

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
# tecnica 1 full_conversation_memory
from agents.consulta_normativa.langchain_rag.business_context.techniques.full_conversation_memory import (full_conversation_memory_node)

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
    workflow.add_node("full_conversation_memory",full_conversation_memory_node) # Agregar nodo full_conversation_memory
    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)
    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)

    
    

    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)

    



    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))

    workflow.add_node("save_conversation_turn", save_conversation_turn_node) # Agregar nodo de historial de conversación


    workflow.add_node("format_result", format_result_node)

    # Construccion del grafo
    #workflow.set_entry_point("retrieve")
    workflow.set_entry_point("business_profile") # se cambia el punto de entrada a "business_profile"
    workflow.add_edge("business_profile","full_conversation_memory")
    workflow.add_edge("full_conversation_memory","retrieve")
    
    workflow.add_edge("retrieve", "normalize_documents")
    workflow.add_edge("normalize_documents", "record_retrieval_trace")

    
    workflow.add_conditional_edges(
        "record_retrieval_trace",
        evidence_route,
        {"with_evidence": "format_context", "without_evidence": "fallback_answer"},)
    
    #workflow.add_edge("fallback_answer", "format_result")
    workflow.add_edge("fallback_answer","save_conversation_turn")

    workflow.add_edge("format_context", "build_messages")



    workflow.add_edge("build_messages", "generate_answer")

    #workflow.add_edge("generate_answer", "format_result")
    workflow.add_edge("generate_answer","save_conversation_turn")
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