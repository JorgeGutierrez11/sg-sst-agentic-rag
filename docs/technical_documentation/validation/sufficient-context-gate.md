# Sufficient-Context Gate para validación de suficiencia de evidencia normativa

Sufficient-Context Gate es una técnica experimental de validación que determina si el contexto recuperado por el sistema RAG contiene evidencia suficiente para responder la pregunta original del usuario antes de invocar al modelo generador.

A diferencia de Retrieval Relevance Grading, esta técnica no evalúa cada documento individualmente. Analiza el **conjunto completo del contexto recuperado** y determina si permite responder la consulta de forma completa, parcial o si la evidencia es insuficiente.

La implementación adopta el concepto de *Sufficient Context* como mecanismo de control previo a la generación, pero no pretende reproducir una arquitectura externa completa.

## Propósito

El baseline del RAG únicamente verifica si existen documentos recuperados:

```text
documents
    ↓
bool(documents)
    ↓
hay evidencia / no hay evidencia
```

Este criterio no permite distinguir entre:

```text
Hay documentos recuperados
```

y:

```text
Los documentos recuperados contienen información suficiente
para responder la pregunta.
```

Sufficient-Context Gate introduce una segunda validación:

```text
pregunta original
        +
contexto recuperado completo
        ↓
Sufficient-Context Gate
        ↓
sufficient / partial / insufficient
```

Su objetivo es impedir que el modelo generador responda cuando el contexto disponible no contiene evidencia suficiente y, al mismo tiempo, permitir respuestas parciales cuando una parte de la consulta sí está respaldada.

## Diferencia respecto a Retrieval Relevance Grading

Las dos técnicas pertenecen a la dimensión de validación y control, pero evalúan aspectos diferentes.

| Técnica                     | Unidad evaluada              | Pregunta que responde                                         |
| --------------------------- | ---------------------------- | ------------------------------------------------------------- |
| Retrieval Relevance Grading | Cada documento individual    | ¿Este documento aporta evidencia relacionada con la consulta? |
| Sufficient-Context Gate     | Contexto recuperado completo | ¿El conjunto de evidencia permite responder la pregunta?      |

Ejemplo:

```text
Pregunta:
¿Quién debe investigar un accidente y cuál es el plazo?

Documento 1:
El empleador debe conformar un equipo investigador.

Documento 2:
Se especifican los integrantes del equipo.
```

Los dos documentos pueden ser **relevantes**, pero el contexto puede seguir siendo **parcial** si no contiene el plazo solicitado.

Por tanto:

```text
relevancia ≠ suficiencia
```

## Ubicación en el pipeline LangGraph

La técnica se ejecuta después de construir el contexto y antes de crear los mensajes que serán enviados al modelo generador.

Flujo experimental:

```text
question
   ↓
retrieve
   ↓
normalize_documents
   ↓
record_retrieval_trace
   ↓
evidence_route
   ├── without_evidence ─────────────→ fallback_answer
   │
   └── with_evidence
            ↓
       format_context
            ↓
   assess_sufficient_context
            ↓
      ┌─────┼──────────────┐
      │     │              │
sufficient partial    insufficient
      │     │              │
      └──┬──┘              ↓
         │            fallback_answer
         ↓
   build_messages
         ↓
   generate_answer
         ↓
    format_result
```

La ubicación después de `format_context` es deliberada: el gate evalúa el mismo contexto consolidado que posteriormente recibiría el modelo generador.

## Archivos principales

```text
agents/consulta_normativa/langchain_rag/
├── validation/
│   └── sufficient_context_gate.py
├── core/
│   ├── state.py
│   └── routes.py
└── graph.py

agents/consulta_normativa/tests/
└── test_sufficient_context_gate.py
```

## Resumen de implementación

| Pieza                                    | Responsabilidad                                                       |
| ---------------------------------------- | --------------------------------------------------------------------- |
| `ContextSufficiency`                     | Define los tres estados posibles de suficiencia.                      |
| `SufficientContextGrade`                 | Define mediante Pydantic la salida estructurada del evaluador.        |
| `SUFFICIENT_CONTEXT_SYSTEM_PROMPT`       | Define los criterios utilizados para decidir suficiencia.             |
| `sufficient_context_gate_node(llm)`      | Construye el nodo LangGraph encargado de evaluar el contexto.         |
| `grade_context_sufficiency(...)`         | Ejecuta la evaluación estructurada mediante el LLM.                   |
| `build_sufficient_context_messages(...)` | Construye los mensajes con pregunta original y contexto recuperado.   |
| `sufficient_context_fallback(...)`       | Aplica la política `fail-open` cuando el evaluador falla.             |
| `sufficient_context_route(...)`          | Convierte el resultado del gate en una decisión de routing del grafo. |

## Estados de suficiencia

La técnica utiliza tres categorías cerradas:

```python
class ContextSufficiency(str, Enum):
    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
```

### `sufficient`

El contexto contiene evidencia para responder todos los componentes sustantivos solicitados por el usuario.

```text
Pregunta:
¿Quién debe investigar los accidentes de trabajo?

Contexto:
Contiene las disposiciones que determinan quién debe realizar
la investigación y la composición del equipo investigador.

Resultado:
sufficient
```

### `partial`

El contexto permite responder al menos una parte sustantiva de la consulta, pero falta evidencia para uno o más componentes.

```text
Pregunta:
¿Quién debe investigar el accidente y cuál es el plazo?

Contexto:
Permite identificar quién investiga,
pero no contiene información sobre el plazo.

Resultado:
partial
```

El estado `partial` **no produce abstención automática**.

Continúa hacia generación porque el prompt base del agente ya establece que, cuando el contexto responda solo parcialmente, el modelo debe indicar qué parte puede responder y qué parte no puede respaldar.

### `insufficient`

El contexto no permite responder de manera útil ningún componente sustantivo de la pregunta.

```text
Pregunta:
¿Cuáles son los requisitos para renovar un pasaporte colombiano?

Contexto:
Fragmentos relacionados con SG-SST.

Resultado:
insufficient
```

En este caso el flujo termina en `fallback_answer`.

## Salida estructurada

El grader utiliza Pydantic:

```python
class SufficientContextGrade(BaseModel):
    level: ContextSufficiency
    reason: str
    missing_information: list[str]
```

Los campos representan:

| Campo                 | Función                                                                          |
| --------------------- | -------------------------------------------------------------------------------- |
| `level`               | Clasificación `sufficient`, `partial` o `insufficient`.                          |
| `reason`              | Justificación breve de la decisión basada en pregunta y contexto.                |
| `missing_information` | Componentes solicitados por el usuario que no están respaldados por el contexto. |

Ejemplo:

```python
{
    "level": "partial",
    "reason": (
        "El contexto permite determinar quién debe realizar "
        "la investigación, pero no contiene el plazo solicitado."
    ),
    "missing_information": [
        "Plazo para realizar la investigación del accidente."
    ],
}
```

Cuando el contexto es suficiente:

```python
{
    "level": "sufficient",
    "reason": "...",
    "missing_information": [],
}
```

## Unidad de evaluación

La técnica evalúa:

```python
state["question"]
state["context"]
```

No ejecuta una evaluación independiente por cada `RetrievedDocument`.

Esto permite reconocer información complementaria distribuida entre distintos fragmentos.

Por ejemplo:

```text
D1 → quién investiga
D2 → plazo
D3 → condiciones adicionales

D1 + D2 + D3
        ↓
contexto completo
        ↓
sufficient
```

Evaluar cada documento por separado no permitiría determinar correctamente la suficiencia conjunta.

## Uso de la pregunta original

La evaluación utiliza:

```python
state["question"]
```

La suficiencia se determina respecto a la necesidad original del usuario y no respecto a una consulta modificada para recuperación.

Esto desacopla el control de suficiencia de posibles transformaciones previas de la consulta.

## Criterios utilizados por el grader

El prompt establece las siguientes reglas principales:

* evaluar el contexto completo como un conjunto;
* no responder directamente la pregunta;
* no utilizar conocimiento externo;
* no asumir información que no esté respaldada por el contexto;
* no considerar suficiente un contexto únicamente por pertenecer al dominio SG-SST;
* revisar todos los componentes de preguntas compuestas;
* clasificar como `partial` cuando solo algunos componentes puedan responderse;
* considerar que la evidencia puede estar distribuida entre varios fragmentos;
* registrar qué información solicitada falta cuando el resultado sea `partial` o `insufficient`.

## Routing

La técnica introduce una ruta específica:

```python
def sufficient_context_route(state: RagGraphState) -> str:
    if state.get("context_sufficiency") == "insufficient":
        return "insufficient"

    return "answerable"
```

La conversión es:

```text
sufficient   → answerable
partial      → answerable
insufficient → insufficient
```

Esto permite separar la clasificación detallada del gate de las rutas operativas del grafo.

### Ruta `answerable`

Continúan:

```text
sufficient
partial
```

hacia:

```text
build_messages
      ↓
generate_answer
```

### Ruta `insufficient`

Continúa hacia:

```text
fallback_answer
```

sin invocar el modelo generador.

## Relación con `evidence_route`

`evidence_route` y `sufficient_context_route` cumplen funciones diferentes.

### `evidence_route`

Comprueba:

```text
¿hay documentos?
```

### `sufficient_context_route`

Comprueba:

```text
¿qué determinó el Sufficient-Context Gate
sobre esos documentos?
```

Por eso se conservan ambas rutas:

```text
retrieve
   ↓
¿hay documentos?
   ↓
sí
   ↓
¿son suficientes?
```

Esto evita ejecutar innecesariamente el gate cuando el retriever no produjo ningún documento.

## Campos de estado

La técnica agrega:

```python
context_sufficiency: str
sufficient_context_trace: dict[str, Any]
```

al contrato `RagGraphState`.

### `context_sufficiency`

Contiene el valor utilizado para routing:

```text
sufficient
partial
insufficient
```

### `sufficient_context_trace`

Conserva información de observabilidad:

```python
{
    "level": "partial",
    "reason": "...",
    "missing_information": [
        "..."
    ],
    "fallback": False,
    "error": None,
}
```

## Fallos y comportamiento fallback

La técnica utiliza una política `fail-open`.

Un fallo técnico del gate no demuestra que el contexto sea insuficiente.

Por tanto:

```text
gate funciona
    ↓
usar clasificación

gate falla
    ↓
permitir generación
```

Operativamente se devuelve:

```python
"context_sufficiency": "sufficient"
```

para permitir que el grafo continúe.

Sin embargo, la traza no afirma que el contexto haya sido realmente clasificado como suficiente:

```python
{
    "level": None,
    "reason": (
        "La suficiencia del contexto no pudo evaluarse. "
        "Se permite continuar por política fail-open."
    ),
    "missing_information": [],
    "fallback": True,
    "error": "RuntimeError",
}
```

Esto permite distinguir:

```text
El grader determinó sufficient
```

de:

```text
El grader falló y se permitió continuar.
```

## Contexto vacío

Si el nodo recibe:

```python
context = ""
```

no invoca el grader.

Devuelve directamente:

```python
{
    "context_sufficiency": "insufficient",
    ...
}
```

Esto evita realizar llamadas innecesarias al LLM cuando no existe evidencia para analizar.

En el flujo normal, `evidence_route` debería impedir que este caso llegue al gate, pero el nodo conserva este comportamiento defensivo para poder funcionar correctamente de forma aislada.

## Observabilidad

Durante una ejecución real se registra:

```text
Sufficient-context gate |
level=sufficient |
reason=... |
missing=[]
```

o:

```text
Sufficient-context gate |
level=insufficient |
reason=... |
missing=[...]
```

Esto permite inspeccionar:

* la clasificación asignada;
* la justificación del grader;
* qué información considera ausente;
* si se utilizó la política `fail-open`;
* si ocurrió un error técnico.

## Pruebas unitarias

Archivo:

```text
agents/consulta_normativa/tests/test_sufficient_context_gate.py
```

Las pruebas utilizan `FakeLLM` y `FakeGrader`, por lo que no requieren:

* Chroma;
* Groq;
* modelo de embeddings;
* conexión a Internet;
* ejecución completa del grafo.

Se validaron seis comportamientos.

### 1. Contexto suficiente

Comprueba:

```text
sufficient
→ continuar
```

### 2. Contexto parcialmente suficiente

Comprueba:

```text
partial
→ conservar información faltante
→ continuar
```

### 3. Contexto insuficiente

Comprueba:

```text
insufficient
→ clasificación correcta
```

### 4. Contexto vacío

Comprueba:

```text
context = ""
→ insufficient
```

sin depender de la respuesta del LLM.

### 5. Fallo durante evaluación

Comprueba:

```text
grader.invoke() falla
→ fail-open
```

### 6. Fallo al configurar structured output

Comprueba:

```text
with_structured_output() falla
→ fail-open
```

Comando:

```bash
python -m pytest agents/consulta_normativa/tests/test_sufficient_context_gate.py -v
```

Resultado observado:

```text
6 passed
```

## Validación manual del flujo real

La técnica fue integrada temporalmente al RAG y ejecutada mediante:

```bash
python -m agents.consulta_normativa.langchain_rag.main
```

### Caso 1: contexto suficiente

Consulta:

```text
¿Quién debe investigar los accidentes de trabajo?
```

El gate produjo:

```text
level=sufficient
missing=[]
```

El contexto contenía disposiciones de la Resolución 1401 de 2007 y del Decreto 1072 de 2015 que permitían responder la consulta.

El grafo continuó hacia generación.

### Caso 2: pregunta compuesta con evidencia completa

Consulta:

```text
¿Quién debe investigar los accidentes de trabajo
y cuál es el plazo exacto para hacerlo?
```

Inicialmente esta consulta se planteó con la intención de producir un caso `partial`.

Sin embargo, el retrieval recuperó también evidencia sobre el plazo de quince días, por lo que el gate clasificó correctamente:

```text
level=sufficient
missing=[]
```

Esto confirma que el gate evalúa el contenido realmente recuperado y no una clasificación esperada previamente.

### Caso 3: contexto insuficiente

Consulta:

```text
¿Cuáles son los requisitos para renovar un pasaporte colombiano?
```

El retrieval produjo documentos pertenecientes al dominio SG-SST, pero estos no contenían evidencia relacionada con la pregunta.

El gate produjo:

```text
level=insufficient
```

y el grafo terminó en:

```text
fallback_answer
```

sin realizar una llamada posterior al modelo generador.

La respuesta fue:

```text
La evidencia recuperada es insuficiente para responder la pregunta.
```

## Estado de validación del caso `partial`

El comportamiento `partial` está cubierto mediante pruebas unitarias.

Todavía no se ha observado un caso `partial` durante una ejecución real contra Chroma.

Por tanto, la implementación permite y enruta correctamente este estado según los tests disponibles, pero su comportamiento con evidencia recuperada real deberá comprobarse posteriormente con una consulta cuyo contexto contenga realmente solo una parte de la información solicitada.

## Coste operacional

A diferencia de Retrieval Relevance Grading, que realiza potencialmente una llamada LLM por documento, Sufficient-Context Gate realiza una sola evaluación sobre el contexto completo.

Con un flujo básico:

```text
retrieval
    ↓
Sufficient-Context Gate
    ↓
generation
```

una consulta respondible agrega aproximadamente:

```text
1 llamada al gate
+
1 llamada al generador
```

Una consulta clasificada como `insufficient` realiza:

```text
1 llamada al gate
+
0 llamadas al generador
```

porque termina mediante fallback determinístico.

## Riesgos

### Abstención excesiva

El grader puede clasificar como `insufficient` contextos que contienen evidencia útil pero incompleta.

La categoría `partial` reduce este riesgo permitiendo continuar hacia generación cuando existe evidencia para responder solo una parte.

### Falsos positivos de suficiencia

El grader puede considerar suficiente un contexto que realmente omite condiciones, excepciones o elementos normativos importantes.

La técnica no debe interpretarse como una garantía formal de completitud jurídica.

### Uso indebido de conocimiento externo

El grader debe evaluar únicamente pregunta y contexto.

La información registrada en `reason` y `missing_information` tampoco debe utilizar conocimiento externo para completar lo que cree que debería contener una respuesta.

### Coste y latencia

La técnica introduce una llamada adicional al LLM para cada consulta con documentos recuperados.

Sin embargo, su coste no escala directamente con `top_k` en número de llamadas, ya que evalúa el contexto completo en una sola invocación.

## Cómo activar la técnica

### 1. Importar el nodo

En `graph.py`:

```python
from agents.consulta_normativa.langchain_rag.validation.sufficient_context_gate import (
    sufficient_context_gate_node,
)
```

### 2. Importar la ruta

En `graph.py`:

```python
from agents.consulta_normativa.langchain_rag.core.routes import (
    evidence_route,
    sufficient_context_route,
)
```

### 3. Registrar el nodo

Después de `format_context`:

```python
workflow.add_node(
    "assess_sufficient_context",
    sufficient_context_gate_node(llm),
)
```

### 4. Sustituir la conexión directa a generación

El baseline contiene:

```python
workflow.add_edge(
    "format_context",
    "build_messages",
)
```

Durante el experimento esta conexión debe desactivarse.

Agregar:

```python
workflow.add_edge(
    "format_context",
    "assess_sufficient_context",
)

workflow.add_conditional_edges(
    "assess_sufficient_context",
    sufficient_context_route,
    {
        "answerable": "build_messages",
        "insufficient": "fallback_answer",
    },
)
```

El resultado es:

```text
format_context
      ↓
assess_sufficient_context
      ↓
 ┌────┴────────┐
 │             │
answerable insufficient
 │             │
 ↓             ↓
build_messages fallback
```

## Cambio requerido en `RagGraphState`

Agregar:

```python
# Sufficient-Context Gate
context_sufficiency: str
sufficient_context_trace: dict[str, Any]
```

## Cambio requerido en `routes.py`

Agregar:

```python
def sufficient_context_route(state: RagGraphState) -> str:
    """Route according to the sufficient-context assessment."""

    if state.get("context_sufficiency") == "insufficient":
        return "insufficient"

    return "answerable"
```
## Ejemplo de integración en LangGraph
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
from agents.consulta_normativa.langchain_rag.query_understanding.rewrite_query import rewrite_query_node

# ************  SUFFICIENT-CONTEXT GATE
from agents.consulta_normativa.langchain_rag.core.routes import (sufficient_context_route)
from agents.consulta_normativa.langchain_rag.validation.sufficient_context_gate import (sufficient_context_gate_node)



Retriever = Callable[[str, int], dict[str, Any]]


def build_langgraph_rag(llm: Any, retriever: Retriever, top_k: int = DEFAULT_TOP_K) -> Any:
    """Build the LangGraph RAG pipeline with explicit evidence branching."""

    try:
        # pyrefly: ignore [missing-import]
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(f"langgraph is not installed: {error}") from error

    workflow = StateGraph(RagGraphState)
    


    workflow.add_node("retrieve", retrieve_node(retriever, top_k))
    workflow.add_node("normalize_documents", normalize_documents_node)
    workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)

    
    

    workflow.add_node("fallback_answer", fallback_answer_node)
    workflow.add_node("format_context", format_context_node)

    # ************ SUFFICIENT-CONTEXT GATE
    workflow.add_node("assess_sufficient_context",sufficient_context_gate_node(llm))

    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))
    workflow.add_node("format_result", format_result_node)

    # Construccion del grafo
    workflow.set_entry_point("retrieve")
    
    workflow.add_edge("retrieve", "normalize_documents")
    workflow.add_edge("normalize_documents", "record_retrieval_trace")

    
    workflow.add_conditional_edges(
        "record_retrieval_trace",
        evidence_route,
        {"with_evidence": "format_context", "without_evidence": "fallback_answer"},)
    
    workflow.add_edge("fallback_answer", "format_result")
    #workflow.add_edge("format_context", "build_messages")

    # ************ SUFFICIENT-CONTEXT GATE
    workflow.add_edge(
        "format_context",
        "assess_sufficient_context",
    )

    workflow.add_conditional_edges(
        "assess_sufficient_context",
        sufficient_context_route,
        {
            "answerable": "build_messages",
            "insufficient": "fallback_answer",
        },
    )


    workflow.add_edge("build_messages", "generate_answer")
    workflow.add_edge("generate_answer", "format_result")
    workflow.add_edge("format_result", END)
    return workflow.compile()


def answer_with_langgraph(question: str, graph: Any) -> LangChainRagResult:
    """Run a compiled LangGraph-like object and return its RAG result."""

    state = graph.invoke({"question": question})
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