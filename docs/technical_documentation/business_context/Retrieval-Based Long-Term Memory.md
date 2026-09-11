# Retrieval-Based Long-Term Memory

Retrieval-Based Long-Term Memory es una técnica de contexto empresarial que almacena interacciones anteriores como memorias semánticas y recupera únicamente aquellas más relacionadas con la consulta actual.

Su objetivo es evitar incorporar todo el historial completo y, en su lugar, seleccionar los recuerdos potencialmente relevantes mediante búsqueda vectorial.

## Propósito

A diferencia de Full Conversation Memory:

```text
perfil
+
todos los turnos
```

y Summarization-Based Memory:

```text
perfil
+
resumen
+
turnos recientes
```

esta técnica utiliza:

```text
perfil
+
Top-K memorias relevantes
```

La memoria se recupera en función de similitud semántica con la pregunta actual.

## Representación de memoria

Cada turno se almacena con:

```python
{
    "text": "...",
    "user": "...",
    "assistant": "...",
}
```

El campo `text` se utiliza para la búsqueda semántica.

La implementación final indexa únicamente el mensaje del usuario:

```python
def build_memory_text(
    turn: ConversationTurn,
) -> str:
    return turn["user"]
```

La respuesta del agente se conserva como parte del payload, pero no participa en el embedding.

Esto reduce el ruido producido por respuestas normativas extensas.

## Estructura de datos

Se añadió a `BusinessContext`:

```python
retrieved_memories: list[RetrievedBusinessMemory]
```

Cada memoria recuperada contiene:

```python
class RetrievedBusinessMemory(TypedDict):
    memory_id: str
    user: str
    assistant: str
    score: float | None
```

Por tanto:

```text
BusinessContext
│
├── profile
├── history
│
├── retrieved_memories
│
└── current_context
```

## Implementación

La técnica se implementó en:

```text
business_context/
└── techniques/
    └── retrieval_long_term_memory.py
```

Las principales funciones son:

```text
build_memory_namespace()
        ↓
crea un namespace aislado por conversación

build_memory_text()
        ↓
genera el texto que será indexado

store_conversation_memory()
        ↓
almacena un turno en el Store

search_relevant_memories()
        ↓
realiza búsqueda semántica Top-K

build_retrieval_memory_context()
        ↓
construye current_context

retrieval_long_term_memory_node()
        ↓
recupera memorias antes del retrieval normativo

store_latest_conversation_memory_node()
        ↓
almacena el turno terminado
```

## Aislamiento entre conversaciones

Las memorias no se almacenan globalmente.

Cada conversación utiliza:

```text
("business-context", thread_id)
```

Ejemplo:

```text
Chat A
→ ("business-context", "thread-a")

Chat B
→ ("business-context", "thread-b")
```

Esto permite utilizar el sistema sin autenticación y mantener independientes las memorias de conversaciones simultáneas.

## Almacenamiento y recuperación

El flujo de almacenamiento es:

```text
pregunta
   ↓
respuesta
   ↓
save_conversation_turn
   ↓
store_long_term_memory
   ↓
embedding
   ↓
Store
```

La recuperación ocurre antes de consultar el corpus normativo:

```text
pregunta actual
   ↓
retrieval_long_term_memory
   ↓
búsqueda semántica
   ↓
Top-K memorias
   ↓
current_context
   ↓
retrieve normativo
```

La pregunta actual se busca antes de almacenar el nuevo turno, evitando recuperar la interacción que todavía se está procesando.

## Embeddings

La memoria utiliza:

```text
Qwen/Qwen3-Embedding-0.6B
```

El modelo se utiliza de forma diferente para documentos y consultas.

Las memorias almacenadas se procesan como documentos:

```text
embed_documents()
```

La pregunta actual se procesa como consulta:

```text
embed_query()
```

utilizando el prompt de query definido por Qwen.

Esto permite adaptar la representación vectorial al escenario de retrieval.

## Construcción de `current_context`

La salida de la técnica tiene la estructura:

```text
PERFIL EMPRESARIAL
...

MEMORIA CONVERSACIONAL RECUPERADA

Memoria 1
Usuario: ...
Agente: ...

Memoria 2
Usuario: ...
Agente: ...
```

Conceptualmente:

```text
profile
+
retrieved_memories
        ↓
current_context
```

## Integración en LangGraph

El inicio del grafo queda:

```text
START
  ↓
business_profile
  ↓
retrieval_long_term_memory
  ↓
retrieve
  ↓
...
```

Al finalizar:

```text
generate_answer / fallback_answer
          ↓
save_conversation_turn
          ↓
store_long_term_memory
          ↓
format_result
          ↓
END
```

El grafo utiliza dos mecanismos independientes:

```text
Checkpointer
    ↓
estado de la conversación

Store
    ↓
memoria semántica recuperable
```

## Persistencia

Durante la evaluación se utilizan:

```python
InMemorySaver
InMemoryStore
```

Por tanto, el estado y las memorias persisten durante la ejecución del proceso, pero se eliminan al reiniciar el programa.

La separación entre conversaciones continúa realizándose mediante `thread_id`.

## Pruebas

Se implementaron pruebas para validar:

- construcción del texto de memoria;
- almacenamiento de turnos;
- búsqueda semántica;
- recuperación Top-K;
- consultas vacías;
- aislamiento entre conversaciones;
- construcción de `current_context`;
- funcionamiento sin perfil;
- funcionamiento sin memorias;
- ausencia de mutaciones sobre el contexto original;
- recuperación mediante nodo LangGraph;
- almacenamiento mediante nodo LangGraph.

Resultado:

```text
test_retrieval_long_term_memory.py
13 passed
```

## Prueba interactiva

Se probó una conversación con información sobre:

```text
1. accidente de un trabajador
2. cambio de número de trabajadores y actividad económica
3. referencia posterior al accidente
```

Ante:

```text
qué te había comentado sobre el accidente?
```

la memoria relacionada con el accidente fue recuperada en primera posición, mientras que el turno relacionado con la panadería obtuvo una similitud inferior.

Esto confirmó que la técnica puede recuperar información conversacional relevante mediante búsqueda semántica.

## Resultado

Retrieval-Based Long-Term Memory permite mantener un historial completo fuera del contexto inmediato y recuperar únicamente recuerdos relacionados con la consulta actual.

La técnica produce correctamente:

```text
perfil empresarial
+
memorias semánticamente relevantes
        ↓
current_context
```

El consumo posterior de `current_context` por técnicas como Query Rewriting o por el nodo de generación corresponde a la integración general del agente y no a esta técnica de contexto empresarial.


# GRAPH.PY

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
# tecnica de memoria a largo plazo
from agents.consulta_normativa.langchain_rag.business_context.techniques.retrieval_long_term_memory import (retrieval_long_term_memory_node,store_latest_conversation_memory_node,)


Retriever = Callable[[str, int], dict[str, Any]] 

# se agregó checkpointer: Any | None = None, para permitir la integración con un sistema de checkpointing y store: Any | None = None, para permitir la integración con un sistema de almacenamiento de memoria a largo plazo.
def build_langgraph_rag(llm: Any, retriever: Retriever, top_k: int = DEFAULT_TOP_K, checkpointer: Any | None = None,store: Any | None = None,) -> Any:
    """Build the LangGraph RAG pipeline with explicit evidence branching."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)
    

    workflow.add_node("business_profile", business_profile_node(llm)) # Agregar nodo de perfil de negocio
    workflow.add_node("retrieval_long_term_memory",retrieval_long_term_memory_node(),) # Agregar nodo de memoria a largo plazo
    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)
    workflow.add_node("record_retrieval_trace",record_retrieval_trace_node)
    

    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)

   


    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))


    workflow.add_node("save_conversation_turn", save_conversation_turn_node) # Agregar nodo de historial de conversación

    workflow.add_node("store_long_term_memory",store_latest_conversation_memory_node,) # Agregar nodo de almacenamiento de memoria a largo plazo

    workflow.add_node("format_result", format_result_node)

    # Construccion del grafo
    #workflow.set_entry_point("retrieve")
    workflow.set_entry_point("business_profile")
    workflow.add_edge("business_profile", "retrieval_long_term_memory") # Agregar arista desde el nodo de perfil de negocio al nodo de memoria a largo plazo
    workflow.add_edge("retrieval_long_term_memory", "retrieve") # Agregar arista desde el nodo de memoria a largo plazo al nodo de recuperación
    
    workflow.add_edge("retrieve", "normalize_documents")
    workflow.add_edge("normalize_documents", "record_retrieval_trace")

    
    workflow.add_conditional_edges(
        "record_retrieval_trace",
        evidence_route,
        {"with_evidence": "format_context", "without_evidence": "fallback_answer"},)
    

    
    workflow.add_edge("fallback_answer","save_conversation_turn")

    workflow.add_edge("format_context", "build_messages") 



    workflow.add_edge("build_messages", "generate_answer")

    # nuevo
    workflow.add_edge(
        "generate_answer",
        "save_conversation_turn",
    )


    workflow.add_edge("save_conversation_turn","store_long_term_memory") # nuevo
    workflow.add_edge("store_long_term_memory", "format_result") # nuevo

    workflow.add_edge("format_result", END)
    return workflow.compile(checkpointer=checkpointer,store=store,) #se agregó checkpointer=checkpointer, y store=store, para permitir la integración con un sistema de checkpointing y almacenamiento de memoria a largo plazo.

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

# MAIN.PY

```python
"""Direct executable entrypoint for the experimental LangChain RAG variant."""

from __future__ import annotations
from uuid import uuid4 # nuevo import para generar un identificador único para cada hilo de conversación

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from langchain_core.embeddings import Embeddings



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

# nueva clase para adaptar los embeddings de Qwen a la memoria a largo plazo basada en recuperación
class QwenMemoryEmbeddings(Embeddings):
    """Qwen embeddings adapted for retrieval-based conversational memory."""

    def __init__(
        self,
        embedding_function: Any,
    ) -> None:
        # Reutilizamos el SentenceTransformer que Chroma ya cargó.
        self._model = embedding_function._model

        self._normalize_embeddings = (
            embedding_function.normalize_embeddings
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Embed stored conversation memories as documents."""

        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=self._normalize_embeddings,
        )

        return [
            vector.tolist()
            for vector in vectors
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        """Embed a memory-search query using Qwen's query prompt."""

        vector = self._model.encode(
            text,
            prompt_name="query",
            convert_to_numpy=True,
            normalize_embeddings=self._normalize_embeddings,
        )

        return vector.tolist()


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
        from chromadb.utils.embedding_functions import (
            SentenceTransformerEmbeddingFunction,
        )
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.store.memory import InMemoryStore

        collection = dependencies.open_existing_collection(
            DEFAULT_CHROMA_PATH,
            DEFAULT_COLLECTION_NAME,
        )

        retriever = dependencies.chroma_retriever(
            collection
        )

        # Memoria de corto plazo asociada al thread.
        checkpointer = InMemorySaver()

        # Mismo modelo de embeddings utilizado por el RAG.
        memory_embedding_function = (
            SentenceTransformerEmbeddingFunction(
                model_name="Qwen/Qwen3-Embedding-0.6B",
                normalize_embeddings=True,
            )
        )

        memory_embeddings = QwenMemoryEmbeddings(
            memory_embedding_function
        )

        # Store independiente para Retrieval-Based
        # Long-Term Memory.
        memory_store = InMemoryStore(
            index={
                "dims": 1024,
                "embed": memory_embeddings,
                "fields": ["text"],
            }
        )

        graph = dependencies.build_langgraph_rag(
            llm,
            retriever,
            DEFAULT_TOP_K,
            checkpointer=checkpointer,
            store=memory_store,
        )

        # Guardar diagrama en disco
        png_bytes = graph.get_graph().draw_mermaid_png()

        with open(
            "data/images/base_rag_graph.png",
            "wb",
        ) as f:
            f.write(png_bytes)

        print(
            "Grafo guardado exitosamente "
            "como 'base_rag_graph.png'"
        )

    except Exception as error:
        raise OperationalError(
            str(error)
        ) from error
    
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

    retrieved_memories = business_context.get(
        "retrieved_memories",
        [],
    )

    print("\n-------------------------- CURRENT BUSINESS CONTEXT ---------------------------------------")
    print(current_context or "[vacío]")
    print("-------------------------- END CURRENT BUSINESS CONTEXT ---------------------------------------\n")

    print(
        "\n-------------------------- RETRIEVED MEMORIES ---------------------------------------"
    )

    if not retrieved_memories:
        print("[ninguna]")
    else:
        for memory in retrieved_memories:
            print(f"\nID: {memory['memory_id']}")
            print(f"Score: {memory['score']}")
            print(f"Usuario: {memory['user']}")
            print(f"Agente: {memory['assistant']}")

    print(
        "-------------------------- END RETRIEVED MEMORIES -----------------------------------\n"
    )


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