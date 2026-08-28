# Summarization-Based Conversational Memory

Summarization-Based Conversational Memory es una técnica de contexto empresarial que mantiene la continuidad de la conversación mediante un **resumen acumulado de los turnos antiguos**, conservando completos únicamente los turnos más recientes.

Su objetivo es reducir el crecimiento del contexto respecto a Full Conversation Memory sin eliminar el historial original.

## Propósito

Full Conversation Memory incorpora todos los turnos completos:

```text
perfil
+
turno 1
+
turno 2
+
turno 3
+
...
```

Esto provoca que `current_context` crezca continuamente.

Summarization-Based Conversational Memory cambia esta representación por:

```text
perfil
+
resumen de turnos antiguos
+
últimos 2 turnos completos
```

El historial completo continúa almacenado en `history`.

## Política implementada

La técnica conserva siempre los **dos turnos más recientes sin resumir**.

Ejemplo con cinco turnos:

```text
turno 1 ┐
turno 2 │ → SUMMARY
turno 3 ┘

turno 4 ┐
turno 5 ┘ → completos
```

Cuando aparecen nuevos turnos, el resumen se actualiza incrementalmente:

```text
summary anterior
+
nuevos turnos antiguos
        ↓
nuevo summary acumulado
```

De esta forma no se vuelve a resumir todo el historial en cada ejecución.

## Estructura de datos

Se añadieron dos campos a `BusinessContext`:

```python
history_summary: str
summarized_turns: int
```

Su función es:

- `history_summary`: almacena el resumen acumulado.
- `summarized_turns`: indica cuántos turnos de `history` ya están representados en el resumen.

`history` continúa almacenando la conversación completa.

## Implementación

La técnica se implementó en:

```text
business_context/
└── techniques/
    └── summarization_memory.py
```

Las principales funciones son:

```text
get_turns_pending_summarization()
        ↓
identifica turnos antiguos todavía no resumidos

get_recent_turns()
        ↓
mantiene los turnos recientes completos

update_conversation_summary()
        ↓
actualiza el resumen acumulado mediante el LLM

build_summarization_context()
        ↓
construye current_context

summarization_memory_node()
        ↓
integra la técnica con LangGraph
```

## Construcción de `current_context`

La representación final generada es:

```text
PERFIL EMPRESARIAL
...

RESUMEN DE CONVERSACIONES ANTERIORES
...

CONVERSACIÓN RECIENTE
...
```

Por tanto:

```text
profile
+
history_summary
+
turnos no resumidos
        ↓
current_context
```

## Manejo de fallos

Si el LLM encargado del resumen falla:

```text
NO se modifica history_summary
NO se modifica summarized_turns
```

Los turnos que aún no han sido resumidos permanecen completos dentro de `current_context`.

Esto evita pérdida de información conversacional.

## Integración en LangGraph

Para evaluar esta técnica se reemplazó el nodo de Full Conversation Memory:

```text
START
  ↓
business_profile
  ↓
summarization_memory
  ↓
retrieve
  ↓
...
```

Las técnicas de memoria no se ejecutan simultáneamente durante la evaluación.

## Pruebas

Se implementaron pruebas para validar:

- selección de turnos antiguos;
- conservación de los últimos dos turnos;
- creación del primer resumen;
- actualización incremental;
- manejo de fallos del LLM;
- construcción de `current_context`;
- ausencia de mutaciones sobre el contexto original;
- funcionamiento del nodo LangGraph.

Resultado:

```text
test_summarization_memory.py
11 passed
```

Adicionalmente, las pruebas específicas de actualización del resumen obtuvieron:

```text
test_summarization_update.py
5 passed
```

## Resultado

La técnica permite mantener contexto empresarial conversacional reduciendo la cantidad de información histórica incluida literalmente en `current_context`, mientras conserva `history` completo como fuente original de la conversación.


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

    build_groq_llm: Callable[[], Any]
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
    """Build the Chroma retriever and Groq-backed LLM for the session."""

    dependencies = load_dependencies()

    try:
        llm = dependencies.build_groq_llm()
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
        from agents.consulta_normativa.langchain_rag.core.llm import build_groq_llm
        from agents.consulta_normativa.langchain_rag.graph import answer_with_langgraph, build_langgraph_rag
        from agents.consulta_normativa.manual_implementation.rag_base import chroma_retriever
        from agents.shared.chroma_retrieval import open_existing_collection
    except ModuleNotFoundError as error:
        raise OperationalError(f"Required runtime dependency is not installed: {error}") from error

    return RuntimeDependencies(
        build_groq_llm=build_groq_llm,
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
# tecnica 2 summarization_memory
from agents.consulta_normativa.langchain_rag.business_context.techniques.summarization_memory import (summarization_memory_node)



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
    workflow.add_node("summarization_memory", summarization_memory_node(llm)) # Agregar nodo summarization_memory
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
    workflow.add_edge("business_profile","summarization_memory")
    workflow.add_edge("summarization_memory","retrieve")
    
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