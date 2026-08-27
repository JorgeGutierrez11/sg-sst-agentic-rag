# Self-Refine para validación y refinamiento de respuestas normativas

Self-Refine es una técnica experimental de validación posterior a la generación que revisa la respuesta inicial producida por el sistema RAG y determina si contiene problemas que puedan corregirse utilizando exclusivamente la pregunta original y el contexto normativo recuperado.

A diferencia de Retrieval Relevance Grading y Sufficient-Context Gate, Self-Refine no modifica los documentos recuperados ni decide si el sistema debe generar una respuesta. La técnica se ejecuta **después de la generación inicial** y actúa directamente sobre la respuesta producida.

La implementación adopta el patrón de retroalimentación y refinamiento de Self-Refine, pero limita el proceso a **como máximo una iteración de refinamiento**.

## Propósito

El baseline del RAG genera directamente una respuesta a partir del contexto recuperado:

```text
contexto recuperado
        ↓
   generación
        ↓
respuesta final
```

Una vez producida la respuesta, el baseline no realiza una evaluación posterior que compruebe si:

* realmente responde la pregunta original;
* todas las afirmaciones están respaldadas por el contexto;
* existen contradicciones con la evidencia recuperada;
* se introdujeron normas, artículos, fechas, cifras u obligaciones no presentes en el contexto;
* se omitió información directamente disponible;
* las citas `[n]` corresponden realmente con los fragmentos utilizados;
* una respuesta parcial fue presentada incorrectamente como completa.

Self-Refine introduce una etapa posterior a la generación:

```text
pregunta original
        +
contexto recuperado
        +
respuesta inicial
        ↓
evaluación Self-Refine
        ↓
¿necesita refinamiento?
    ├── no
    │    ↓
    │ respuesta inicial
    │
    └── sí
         ↓
    retroalimentación
         ↓
     refinamiento
         ↓
    respuesta refinada
```

El objetivo es permitir que el sistema detecte y corrija problemas presentes en su primera respuesta sin realizar una nueva recuperación documental ni utilizar conocimiento externo.

## Diferencia respecto a las otras técnicas de validación

Las tres técnicas implementadas en la dimensión de validación y control actúan en momentos diferentes del pipeline.

| Técnica | Unidad evaluada | Momento | Pregunta que responde |
| --- | --- | --- | --- |
| Retrieval Relevance Grading | Documento individual | Después del retrieval | ¿Este documento aporta evidencia relevante? |
| Sufficient-Context Gate | Contexto recuperado completo | Antes de generación | ¿La evidencia permite responder la pregunta? |
| Self-Refine | Respuesta generada | Después de generación | ¿La respuesta producida necesita ser corregida? |

Por tanto:

```text
Retrieval Relevance Grading
        ↓
calidad de documentos

Sufficient-Context Gate
        ↓
suficiencia del contexto

Self-Refine
        ↓
calidad de la respuesta generada
```

Self-Refine no sustituye las técnicas anteriores.

Una respuesta puede haber sido generada a partir de documentos relevantes y contexto suficiente y aun así contener una afirmación incorrecta, una omisión o una cita mal utilizada.

## Ubicación en el pipeline LangGraph

Para evaluar Self-Refine de forma aislada, la técnica se incorpora después de `generate_answer` y antes de `format_result`.

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
   │                                      ↓
   │                                 format_result
   │
   └── with_evidence
            ↓
       format_context
            ↓
       build_messages
            ↓
      generate_answer
            ↓
        self_refine
            ↓
       format_result
```

La ubicación posterior a `generate_answer` es necesaria porque Self-Refine utiliza como entrada:

```python
state["answer"]
```

que corresponde a la primera respuesta producida por el generador.

El nodo puede reemplazar este valor por una respuesta refinada antes de que `format_result` construya el resultado público del agente.

## Archivos principales

```text
agents/consulta_normativa/langchain_rag/
├── validation/
│   └── self_refine.py
├── core/
│   └── state.py
└── graph.py

agents/consulta_normativa/tests/
└── test_self_refine.py
```

## Resumen de implementación

La técnica está compuesta por las siguientes piezas:

| Pieza | Responsabilidad |
| --- | --- |
| `SelfRefineFeedback` | Define mediante Pydantic la salida estructurada de la fase de retroalimentación. |
| `SELF_REFINE_FEEDBACK_SYSTEM_PROMPT` | Define los criterios utilizados para revisar la respuesta inicial. |
| `SELF_REFINE_REFINEMENT_SYSTEM_PROMPT` | Define las restricciones utilizadas durante la generación de la respuesta corregida. |
| `self_refine_node(llm)` | Construye el nodo LangGraph y coordina evaluación, decisión y refinamiento. |
| `generate_self_refine_feedback(...)` | Solicita al LLM una evaluación estructurada de la respuesta inicial. |
| `generate_refined_answer(...)` | Produce una nueva respuesta cuando el grader solicita refinamiento. |
| `build_feedback_messages(...)` | Construye los mensajes utilizados durante la fase de evaluación. |
| `build_refinement_messages(...)` | Construye los mensajes utilizados durante la fase de refinamiento. |
| `self_refine_fallback(...)` | Conserva la respuesta inicial cuando ocurre un fallo técnico. |

## Flujo interno

El nodo implementa dos fases diferentes.

```text
RESPUESTA INICIAL
       ↓
┌──────────────────────┐
│ Fase 1: Feedback     │
└──────────────────────┘
       ↓
needs_refinement
   ├── False
   │      ↓
   │ conservar respuesta
   │
   └── True
          ↓
┌──────────────────────┐
│ Fase 2: Refinement   │
└──────────────────────┘
          ↓
    respuesta refinada
```

La segunda llamada al LLM únicamente ocurre cuando:

```python
needs_refinement is True
```

Por tanto, una respuesta considerada correcta no se vuelve a generar innecesariamente.

## Salida estructurada de la fase de feedback

La fase de evaluación utiliza Pydantic:

```python
class SelfRefineFeedback(BaseModel):
    needs_refinement: bool
    feedback: str
    issues: list[str]
```

Los campos tienen las siguientes funciones:

| Campo | Uso |
| --- | --- |
| `needs_refinement` | Determina si la respuesta inicial debe pasar por una nueva generación. |
| `feedback` | Contiene instrucciones concretas sobre qué debe corregirse. |
| `issues` | Registra problemas específicos detectados en la respuesta. |

Ejemplo:

```python
{
    "needs_refinement": True,
    "feedback": (
        "La respuesta indica un plazo incorrecto. "
        "Debe corregirse utilizando el fragmento [1]."
    ),
    "issues": [
        "El plazo indicado no coincide con la evidencia recuperada."
    ],
}
```

Esta salida estructurada evita utilizar texto libre para controlar el flujo del nodo.

## Fase 1: generación de retroalimentación

La primera fase recibe tres elementos:

```text
pregunta original
        +
contexto normativo recuperado
        +
respuesta inicial
```

Los mensajes se construyen mediante:

```python
build_feedback_messages(...)
```

con la estructura:

```text
PREGUNTA ORIGINAL:
{question}

CONTEXTO NORMATIVO RECUPERADO:
{context}

RESPUESTA INICIAL:
{initial_answer}
```

El grader debe determinar si la respuesta necesita ser refinada.

## Criterios de evaluación

El prompt de feedback solicita revisar especialmente:

* si la respuesta responde realmente la pregunta original;
* si las afirmaciones normativas o factuales están respaldadas;
* si introduce información que no aparece en el contexto;
* si contradice la evidencia recuperada;
* si omite información directamente relevante disponible;
* si las citas `[n]` corresponden con los fragmentos numerados;
* si presenta como completa una respuesta que solo puede respaldarse parcialmente.

La decisión se realiza exclusivamente utilizando:

```text
pregunta original
+
contexto recuperado
+
respuesta inicial
```

El grader no debe utilizar conocimiento externo para determinar qué información debería contener la respuesta.

## Pregunta utilizada para la evaluación

Self-Refine utiliza:

```python
state["question"]
```

es decir, la pregunta original del usuario.

No utiliza:

```python
state["retrieval_query"]
```

aunque una técnica previa de transformación de consulta haya generado una versión diferente para retrieval.

Esto mantiene la evaluación alineada con la necesidad original del usuario:

```text
pregunta original
       ↓
¿la respuesta realmente respondió esto?
```

y no con una consulta intermedia utilizada únicamente para recuperar documentos.

## Contexto utilizado

La técnica recibe:

```python
state["context"]
```

El contexto es el mismo contexto numerado utilizado previamente para generar la respuesta inicial.

Esto es especialmente importante para verificar citas:

```text
[1] ...
[2] ...
[3] ...
```

Self-Refine puede comprobar si una afirmación que utiliza:

```text
[2]
```

está realmente respaldada por el fragmento `[2]`.

La técnica no realiza un nuevo retrieval.

## Decisión de refinamiento

Después de obtener `SelfRefineFeedback`, existen dos caminos.

### Respuesta aceptable

Si:

```python
feedback.needs_refinement is False
```

el nodo conserva:

```python
answer = initial_answer
```

y no realiza una segunda llamada de generación.

Flujo:

```text
respuesta inicial
      ↓
feedback
      ↓
needs_refinement = False
      ↓
respuesta inicial
```

### Respuesta con problemas

Si:

```python
feedback.needs_refinement is True
```

el sistema ejecuta:

```python
generate_refined_answer(...)
```

utilizando:

```text
pregunta original
+
contexto recuperado
+
respuesta inicial
+
feedback
+
issues
```

## Fase 2: refinamiento

Los mensajes para refinamiento tienen la siguiente estructura:

```text
PREGUNTA ORIGINAL:
{question}

CONTEXTO NORMATIVO RECUPERADO:
{context}

RESPUESTA INICIAL:
{initial_answer}

RETROALIMENTACIÓN:
{feedback}

PROBLEMAS DETECTADOS:
- {issue_1}
- {issue_2}
- ...
```

El modelo recibe instrucciones explícitas para:

* utilizar exclusivamente el contexto recuperado;
* corregir afirmaciones contradictorias;
* eliminar afirmaciones no respaldadas;
* incorporar información omitida solamente si aparece en el contexto;
* conservar las citas `[n]`;
* verificar que cada cita utilizada corresponda con un fragmento existente;
* indicar explícitamente cuando la evidencia solo permite una respuesta parcial;
* devolver únicamente la respuesta final refinada.

## Una sola iteración

La implementación actual no ejecuta un ciclo indefinido de:

```text
generar
↓
evaluar
↓
refinar
↓
evaluar nuevamente
↓
refinar nuevamente
↓
...
```

En su lugar utiliza:

```text
respuesta inicial
      ↓
feedback
      ↓
máximo un refinamiento
      ↓
respuesta final
```

Por tanto:

```python
máximo de refinamientos = 1
```

Una respuesta refinada no vuelve a pasar por el grader dentro de la implementación actual.

Esta decisión mantiene controlado el número de llamadas al LLM y permite evaluar experimentalmente la técnica sin introducir un ciclo de terminación variable.

## Reemplazo de la respuesta en el estado

Si el refinamiento termina correctamente:

```python
return {
    "answer": refined_answer.strip(),
    ...
}
```

Por tanto, el valor existente:

```python
state["answer"]
```

es reemplazado por la respuesta refinada.

`format_result` no necesita conocer si ocurrió refinamiento.

Simplemente utiliza:

```python
state["answer"]
```

que puede contener:

```text
respuesta inicial
```

o:

```text
respuesta refinada
```

dependiendo de la decisión del nodo.

## Campos de estado

La técnica agrega una traza al contrato `RagGraphState`:

```python
# Self-Refine
self_refine_trace: dict[str, Any]
```

La respuesta continúa utilizando el campo ya existente:

```python
answer: str
```

No se crea un campo público separado como:

```python
refined_answer
```

porque el refinamiento sustituye directamente la respuesta que continuará por el pipeline.

## Traza de Self-Refine

Cuando la respuesta requiere refinamiento y este termina correctamente, la traza tiene una estructura equivalente a:

```python
{
    "initial_answer": initial_answer,
    "needs_refinement": True,
    "refined": True,
    "feedback": feedback.feedback,
    "issues": feedback.issues,
    "fallback": False,
    "error_stage": None,
    "error": None,
}
```

Cuando no requiere refinamiento:

```python
{
    "initial_answer": initial_answer,
    "needs_refinement": False,
    "refined": False,
    "feedback": feedback.feedback,
    "issues": feedback.issues,
    "fallback": False,
    "error_stage": None,
    "error": None,
}
```

Los campos permiten distinguir:

| Campo | Interpretación |
| --- | --- |
| `initial_answer` | Respuesta producida originalmente por `generate_answer`. |
| `needs_refinement` | Decisión tomada por el grader. |
| `refined` | Indica si realmente se produjo una nueva respuesta. |
| `feedback` | Instrucción de corrección generada por el grader. |
| `issues` | Problemas concretos identificados. |
| `fallback` | Indica si ocurrió un fallo técnico y se conservó la respuesta inicial. |
| `error_stage` | Fase donde ocurrió el error. |
| `error` | Tipo de excepción registrada. |

## Fallos y comportamiento fallback

Self-Refine utiliza una política `fail-open`.

Un fallo de la etapa de refinamiento no implica que la respuesta inicial deba descartarse.

Por tanto:

```text
Self-Refine funciona
        ↓
usar resultado de Self-Refine

Self-Refine falla
        ↓
conservar respuesta inicial
```

La política evita que una respuesta ya generada se pierda únicamente porque falle una etapa experimental posterior.

## Fallo al configurar structured output

El nodo intenta crear el grader mediante:

```python
feedback_grader = llm.with_structured_output(
    SelfRefineFeedback
)
```

Si esta operación falla:

```text
with_structured_output()
        ↓
      error
        ↓
conservar respuesta inicial
```

La traza registra:

```python
{
    "refined": False,
    "fallback": True,
    "error_stage": "feedback_configuration",
    "error": "RuntimeError",
}
```

## Fallo durante generación de feedback

Si falla:

```python
grader.invoke(...)
```

el sistema conserva la respuesta inicial.

La traza utiliza:

```python
"error_stage": "feedback"
```

Ejemplo conceptual:

```text
respuesta inicial
      ↓
grader
      ↓
    ERROR
      ↓
respuesta inicial
```

No se intenta ejecutar refinamiento porque no existe una retroalimentación válida.

## Fallo durante refinamiento

Si:

```python
needs_refinement = True
```

pero falla la segunda llamada al LLM:

```python
generate_refined_answer(...)
```

el sistema conserva nuevamente:

```python
initial_answer
```

y registra:

```python
{
    "needs_refinement": True,
    "refined": False,
    "fallback": True,
    "error_stage": "refinement",
    ...
}
```

Esto permite saber que el grader sí detectó un problema, pero la corrección no pudo producirse.

## Respuesta refinada vacía

Una respuesta refinada compuesta únicamente por espacios:

```python
"   "
```

no se considera una salida válida.

La implementación crea:

```python
ValueError(
    "Self-Refine produced an empty refined answer."
)
```

y aplica nuevamente el fallback:

```text
respuesta refinada vacía
          ↓
        error
          ↓
 conservar respuesta inicial
```

## Respuesta inicial vacía

Si el nodo recibe:

```python
state["answer"] = ""
```

no realiza ninguna llamada al LLM.

Devuelve una traza defensiva:

```python
{
    "needs_refinement": False,
    "refined": False,
    "feedback": "",
    "issues": [],
    "fallback": True,
    "error_stage": "input",
    "error": "EmptyInitialAnswer",
}
```

En el flujo normal, `generate_answer` debería producir una respuesta antes de llegar a Self-Refine, pero esta validación permite que el nodo tenga un comportamiento controlado si recibe un estado incompleto.

## Decisiones y guardrails importantes

| Aspecto | Implementación actual |
| --- | --- |
| Momento de ejecución | Después de `generate_answer`. |
| Pregunta utilizada | `state["question"]`, es decir, la consulta original. |
| Contexto utilizado | El mismo `state["context"]` utilizado por el generador. |
| Respuesta evaluada | `state["answer"]`. |
| Salida del feedback | `SelfRefineFeedback` mediante `with_structured_output(...)`. |
| Número de iteraciones | Máximo una iteración de refinamiento. |
| Nuevo retrieval | No. |
| Conocimiento externo | Prohibido tanto para feedback como para refinamiento. |
| Respuesta correcta | Se conserva sin regenerarla. |
| Respuesta problemática | Se genera una versión refinada. |
| Fallo del feedback | Se conserva la respuesta inicial. |
| Fallo del refinamiento | Se conserva la respuesta inicial. |
| Respuesta refinada vacía | Se considera fallo y se conserva la inicial. |
| Observabilidad | Se registra `self_refine_trace`. |
| Política ante errores | `fail-open`. |

## Observabilidad

Durante la fase de feedback se registra:

```text
Self-Refine feedback |
needs_refinement=True |
issues=[...] |
feedback=...
```

Cuando ocurre refinamiento correctamente:

```text
Self-Refine completed |
refined=True |
issues=[...]
```

Los errores también quedan registrados mediante el logger indicando la etapa donde ocurrió el fallo.

La traza permite posteriormente analizar experimentalmente:

* cuántas respuestas fueron marcadas para refinamiento;
* qué problemas fueron detectados;
* cuántas respuestas fueron efectivamente refinadas;
* cuántas ejecuciones utilizaron fallback;
* en qué etapa ocurrió un fallo técnico.

## Pruebas unitarias

Archivo:

```text
agents/consulta_normativa/tests/test_self_refine.py
```

La suite define siete pruebas para los principales caminos de ejecución.

### 1. Respuesta sin problemas

Comprueba:

```text
needs_refinement = False
        ↓
conservar respuesta inicial
        ↓
no ejecutar refinamiento
```

Prueba:

```python
test_answer_without_issues_is_preserved()
```

### 2. Respuesta con problemas

Comprueba:

```text
needs_refinement = True
        ↓
ejecutar refinamiento
        ↓
reemplazar respuesta inicial
```

Prueba:

```python
test_answer_with_issues_is_refined()
```

### 3. Fallo durante feedback

Comprueba:

```text
feedback falla
     ↓
fail-open
     ↓
respuesta inicial
```

Prueba:

```python
test_feedback_failure_preserves_initial_answer()
```

### 4. Fallo al configurar structured output

Comprueba:

```text
with_structured_output() falla
        ↓
fail-open
        ↓
respuesta inicial
```

Prueba:

```python
test_structured_output_failure_preserves_initial_answer()
```

### 5. Fallo durante refinamiento

Comprueba:

```text
feedback correcto
        ↓
needs_refinement = True
        ↓
refinamiento falla
        ↓
respuesta inicial
```

Prueba:

```python
test_refinement_failure_preserves_initial_answer()
```

### 6. Respuesta inicial vacía

Comprueba que:

```text
answer = ""
    ↓
no llamar al LLM
```

Prueba:

```python
test_empty_initial_answer_does_not_call_llm()
```

### 7. Respuesta refinada vacía

Comprueba que una salida vacía durante refinamiento active el fallback:

```text
refined_answer = "   "
        ↓
ValueError
        ↓
respuesta inicial
```

Prueba:

```python
test_empty_refined_answer_preserves_initial_answer()
```

La suite puede ejecutarse mediante:

```bash
python -m pytest agents/consulta_normativa/tests/test_self_refine.py -v
```

## Coste operacional

Self-Refine introduce al menos una llamada adicional al LLM para cada respuesta que alcanza el nodo.

Caso donde la respuesta inicial es aceptada:

```text
generación inicial
       ↓
feedback Self-Refine
       ↓
needs_refinement = False
```

Coste adicional:

```text
1 llamada LLM
```

Caso donde la respuesta requiere corrección:

```text
generación inicial
       ↓
feedback Self-Refine
       ↓
needs_refinement = True
       ↓
refinamiento
```

Coste adicional:

```text
2 llamadas LLM
```

Por tanto, respecto al baseline:

```text
respuesta aceptada:
1 generación + 1 evaluación

respuesta refinada:
1 generación + 1 evaluación + 1 refinamiento
```

El número de llamadas no depende directamente del número de documentos recuperados, porque Self-Refine evalúa la respuesta y el contexto completo en una sola llamada de feedback.

## Riesgos

### Correcciones incorrectas

El grader puede identificar como problema una afirmación que realmente está respaldada y provocar una modificación innecesaria.

Self-Refine no constituye una garantía formal de corrección normativa.

### Introducción de nuevos errores

La segunda generación puede corregir un problema y simultáneamente introducir otro.

La implementación actual no vuelve a evaluar la respuesta refinada, debido a que se limita a una sola iteración.

### Uso de conocimiento externo

Tanto el grader como el refinador son modelos LLM y podrían utilizar conocimiento paramétrico.

Los prompts prohíben explícitamente completar información que no aparezca en el contexto, pero esta restricción depende del cumplimiento del modelo.

### Verificación de citas

Self-Refine solicita comprobar la coherencia de las citas `[n]`, pero la implementación continúa dependiendo de una evaluación mediante LLM.

No realiza una comprobación determinística de entailment entre cada afirmación y cada fragmento citado.

### Latencia

Todas las respuestas generadas requieren una llamada adicional para feedback.

Las respuestas marcadas para refinamiento requieren dos llamadas adicionales respecto al baseline.

### Dependencia del mismo modelo

La implementación actual recibe:

```python
self_refine_node(llm)
```

y utiliza el mismo objeto `llm` tanto para estructurar la retroalimentación como para producir la respuesta refinada.

Por tanto, el modelo encargado de detectar errores puede compartir los mismos sesgos o limitaciones del modelo que produjo la respuesta inicial.

## Cómo activar la técnica

Self-Refine se monta temporalmente en `graph.py` para realizar su evaluación experimental.

### 1. Importar el nodo

Agregar:

```python
from agents.consulta_normativa.langchain_rag.validation.self_refine import (
    self_refine_node,
)
```

### 2. Registrar el nodo

Después de registrar `generate_answer`:

```python
workflow.add_node(
    "self_refine",
    self_refine_node(llm),
)
```

Por ejemplo:

```python
workflow.add_node("build_messages", build_messages_node)
workflow.add_node("generate_answer", generate_answer_node(llm))

workflow.add_node(
    "self_refine",
    self_refine_node(llm),
)

workflow.add_node("format_result", format_result_node)
```

### 3. Desactivar la conexión del baseline

El baseline conecta directamente:

```python
workflow.add_edge(
    "generate_answer",
    "format_result",
)
```

Para probar Self-Refine esta conexión debe quitarse o comentarse:

```python
# workflow.add_edge(
#     "generate_answer",
#     "format_result",
# )
```

No deben mantenerse simultáneamente ambas rutas, porque `generate_answer` debe pasar primero por Self-Refine antes de construir el resultado final.

### 4. Agregar las conexiones de Self-Refine

Agregar:

```python
workflow.add_edge(
    "generate_answer",
    "self_refine",
)

workflow.add_edge(
    "self_refine",
    "format_result",
)
```

El cambio es:

```text
BASELINE

generate_answer
      ↓
format_result
```

por:

```text
SELF-REFINE

generate_answer
      ↓
 self_refine
      ↓
format_result
```

## Cambio requerido en `RagGraphState`

En:

```text
agents/consulta_normativa/langchain_rag/core/state.py
```

agregar:

```python
# Self-Refine
self_refine_trace: dict[str, Any]
```

No es necesario agregar un campo `refined_answer`, ya que la técnica actualiza directamente:

```python
state["answer"]
```

## Ejemplo de integración en LangGraph

La configuración experimental del grafo para Self-Refine debe mantener el retrieval base y agregar únicamente la etapa posterior a generación.

```python
"""LangGraph RAG flow for normative consultation."""
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

# ************ NELSON: SELF-REFINE
from agents.consulta_normativa.langchain_rag.validation.self_refine import (self_refine_node)


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



    workflow.add_node("build_messages", build_messages_node)
    workflow.add_node("generate_answer", generate_answer_node(llm))

    # ************ NELSON: SELF-REFINE
    workflow.add_node(
        "self_refine",
        self_refine_node(llm),
    )

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
    workflow.add_edge("format_context", "build_messages")



    workflow.add_edge("build_messages", "generate_answer")
    #workflow.add_edge("generate_answer", "format_result")

    # ************ NELSON: SELF-REFINE
    workflow.add_edge("generate_answer", "self_refine")
    workflow.add_edge("self_refine", "format_result")
    

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

El flujo resultante es:

```text
retrieve
   ↓
normalize_documents
   ↓
record_retrieval_trace
   ↓
evidence_route
   ├── without_evidence
   │        ↓
   │   fallback_answer
   │        ↓
   │   format_result
   │
   └── with_evidence
            ↓
       format_context
            ↓
       build_messages
            ↓
      generate_answer
            ↓
        self_refine
            ↓
       format_result
```

## Cómo retirar la técnica

Una vez finalizada la evaluación experimental de Self-Refine, para volver al baseline se deben revertir únicamente los cambios específicos de la técnica.

Eliminar o comentar el import:

```python
from agents.consulta_normativa.langchain_rag.validation.self_refine import (
    self_refine_node,
)
```

Eliminar el nodo:

```python
workflow.add_node(
    "self_refine",
    self_refine_node(llm),
)
```

Eliminar las conexiones:

```python
workflow.add_edge(
    "generate_answer",
    "self_refine",
)

workflow.add_edge(
    "self_refine",
    "format_result",
)
```

Y restaurar:

```python
workflow.add_edge(
    "generate_answer",
    "format_result",
)
```

De esta forma:

```text
generate_answer
      ↓
 self_refine
      ↓
format_result
```

vuelve a:

```text
generate_answer
      ↓
format_result
```

sin modificar el resto del comportamiento del RAG.
