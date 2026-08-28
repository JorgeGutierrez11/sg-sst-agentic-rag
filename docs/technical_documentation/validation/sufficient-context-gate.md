# Sufficient-Context Gate para validación de suficiencia normativa

Sufficient-Context Gate valida si el contexto recuperado por el RAG contiene evidencia suficiente para responder la pregunta original antes de invocar al modelo generador. La técnica se ejecuta después de `format_context` y antes de `build_messages`, porque evalúa el contexto consolidado completo que recibiría el LLM.

A diferencia de Retrieval Relevance Grading, no evalúa documentos por separado. Evalúa el conjunto completo del contexto y clasifica la evidencia como `sufficient`, `partial` o `insufficient`.

## Propósito

El baseline del RAG solo distingue si hay documentos recuperados:

```text
documents -> hay evidencia / no hay evidencia
```

Ese criterio no responde una pregunta más importante:

```text
¿El contexto recuperado permite responder con respaldo normativo?
```

Sufficient-Context Gate agrega esa validación antes de generación:

```text
pregunta original + contexto recuperado -> sufficient_context_gate
                                      -> sufficient / partial / insufficient
```

El objetivo es evitar respuestas normales cuando la evidencia recuperada no alcanza y permitir respuestas parciales cuando existe soporte para una parte de la consulta.

## Ubicación en el pipeline LangGraph

El flujo activo con esta técnica queda así:

```text
retrieve
-> normalize_documents
-> expand_parent_documents
-> record_retrieval_trace
-> evidence_route
   ├── without_evidence -> fallback_answer -> format_result
   └── with_evidence
       -> format_context
       -> sufficient_context_gate
       -> sufficient_context_route
          ├── answerable -> build_messages -> generate_answer -> self_refine -> format_result
          ├── partial    -> build_messages -> generate_answer -> self_refine -> format_result
          └── insufficient -> insufficient_context_answer -> format_result
```

Cambios importantes del nuevo grafo:

- `sufficient_context_gate` se ejecuta después de `format_context`, no antes de armar el contexto.
- `partial` tiene ruta explícita y continúa hacia generación con una advertencia de respuesta parcial.
- `insufficient` ya no reutiliza `fallback_answer`; usa `insufficient_context_answer`, una respuesta específica para contexto recuperado pero insuficiente.
- `insufficient` no invoca `generate_answer` ni `self_refine`.
- `Self-Refine` permanece activo después de `generate_answer` para las rutas `answerable` y `partial`.
- Retrieval Relevance Grading no está activo en este flujo para evitar mezclar técnicas experimentales.

Archivos principales:

- `agents/consulta_normativa/langchain_rag/validation/sufficient_context_gate.py`
- `agents/consulta_normativa/langchain_rag/core/routes.py`
- `agents/consulta_normativa/langchain_rag/graph.py`
- `agents/consulta_normativa/langchain_rag/core/state.py`
- `agents/consulta_normativa/tests/test_sufficient_context_gate.py`
- `agents/consulta_normativa/tests/test_langchain_rag_graph.py`

## Resumen de implementación

| Pieza | Responsabilidad |
|---|---|
| `ContextSufficiency` | Enum con los estados `sufficient`, `partial` e `insufficient`. |
| `SufficientContextGrade` | Modelo Pydantic de salida estructurada del grader. |
| `sufficient_context_gate_node(llm)` | Nodo LangGraph que evalúa `state["question"]` y `state["context"]`. |
| `grade_context_sufficiency(...)` | Invoca el grader estructurado. |
| `build_sufficient_context_messages(...)` | Construye mensajes con la pregunta original y el contexto recuperado. |
| `sufficient_context_fallback(...)` | Aplica política fail-open ante errores técnicos. |
| `sufficient_context_route(state)` | Enruta `answerable`, `partial` o `insufficient`. |
| `insufficient_context_answer_node(state)` | Produce respuesta determinística cuando el contexto existe pero no basta. |
| `build_messages_node(state)` | Agrega advertencia cuando `context_sufficiency == "partial"`. |

El gate no modifica `state["documents"]`. Su salida agrega metadata de decisión al estado para controlar la generación.

## Estados de suficiencia

| Estado | Significado | Ruta del grafo |
|---|---|---|
| `sufficient` | El contexto permite responder los componentes sustantivos de la pregunta. | `answerable -> build_messages` |
| `partial` | El contexto permite responder una parte, pero falta evidencia para otros componentes. | `partial -> build_messages` con advertencia |
| `insufficient` | El contexto no permite responder útilmente con respaldo normativo. | `insufficient -> insufficient_context_answer` |

### `partial` como respuesta con advertencia

`partial` no bloquea la generación. En SG-SST una respuesta parcial puede ser útil si declara sus límites. Por eso el grafo agrega una nota al contexto antes de construir el prompt:

```text
Nota de suficiencia: el contexto recuperado solo permite una respuesta parcial.
Responde únicamente lo respaldado e indica explícitamente qué información falta.
```

Si el grader reporta `missing_information`, esa lista también se agrega al contexto usado para generación.

### `insufficient` como bloqueo de generación

`insufficient` sí bloquea la generación normal. El sistema no llama al LLM generador y devuelve una respuesta determinística:

```text
La evidencia recuperada no es suficiente para responder completamente la pregunta.
Información faltante:
- ...
```

Si no hay información faltante detallada, usa una variante breve indicando que falta respaldo normativo suficiente.

## Salida estructurada

El grader utiliza Pydantic:

```python
class SufficientContextGrade(BaseModel):
    level: ContextSufficiency
    reason: str
    missing_information: list[str]
```

| Campo | Uso |
|---|---|
| `level` | Clasificación `sufficient`, `partial` o `insufficient`. |
| `reason` | Justificación breve basada solo en pregunta y contexto. |
| `missing_information` | Información solicitada que no está respaldada por el contexto. |

Ejemplo de salida parcial:

```python
{
    "level": "partial",
    "reason": "El contexto permite identificar el responsable, pero no el plazo solicitado.",
    "missing_information": ["Plazo para realizar la investigación."],
}
```

## Campos de estado

| Campo | Uso |
|---|---|
| `question` | Pregunta original usada para evaluar suficiencia. |
| `context` | Contexto consolidado construido desde documentos recuperados. |
| `context_sufficiency` | Valor usado por `sufficient_context_route`. |
| `sufficient_context_trace` | Traza interna con nivel, razón, faltantes, fallback y error. |
| `messages` | Mensajes de generación; en `partial` incluyen la advertencia de suficiencia. |
| `answer` | Respuesta generada, refinada o respuesta determinística de insuficiencia. |

Ejemplo de traza interna:

```python
{
    "level": "partial",
    "reason": "El contexto responde solo una parte de la consulta.",
    "missing_information": ["Nivel de riesgo concreto de la actividad económica."],
    "fallback": False,
    "error": None,
}
```

`sufficient_context_trace` permanece como estado interno. No se expone en `LangChainRagResult` para no ampliar el contrato público mientras la técnica sigue en evaluación.

## Routing

La ruta actual distingue explícitamente los tres casos operativos:

```python
def sufficient_context_route(state: RagGraphState) -> str:
    if state.get("context_sufficiency") == "insufficient":
        return "insufficient"

    if state.get("context_sufficiency") == "partial":
        return "partial"

    return "answerable"
```

La conversión es:

```text
sufficient   -> answerable
partial      -> partial
insufficient -> insufficient
```

Esto evita ocultar `partial` dentro de `answerable` y permite probar que el prompt recibe una advertencia específica.

## Relación con otras técnicas

| Técnica | Estado en este flujo | Motivo |
|---|---|---|
| Parent-Document Retrieval | Activa antes del gate | El gate evalúa el contexto después de expandir child chunks a parents. |
| Retrieval Relevance Grading | Inactiva | Evita mezclar validación por documento con validación de contexto completo en el mismo experimento. |
| Self-Refine | Activa después de generación | Revisa la respuesta generada cuando el gate permite responder. |

La secuencia activa evalúa suficiencia del contexto antes de generar y luego permite que Self-Refine revise la respuesta inicial si hubo generación.

## Fallbacks y guardrails

Sufficient-Context Gate usa política fail-open ante errores técnicos: un fallo del grader no prueba que el contexto sea insuficiente.

| Caso | Comportamiento |
|---|---|
| Contexto vacío | Devuelve `context_sufficiency="insufficient"` sin invocar el LLM. |
| Falla `with_structured_output(...)` | Permite continuar como `sufficient` por fallback técnico. |
| Falla `grader.invoke(...)` | Permite continuar como `sufficient` por fallback técnico. |
| Salida malformada | Permite continuar como `sufficient` por fallback técnico. |
| `insufficient` válido | Bloquea generación y usa `insufficient_context_answer`. |
| `partial` válido | Genera respuesta con advertencia explícita de límites. |

En fallback técnico, la traza marca `fallback=True` y registra el tipo de error. Esto distingue “el grader dijo sufficient” de “el grader falló y se permitió continuar”.

## Pruebas

Pruebas unitarias del gate:

```bash
python -m unittest agents.consulta_normativa.tests.test_sufficient_context_gate
```

Casos cubiertos:

- `sufficient` escribe `context_sufficiency="sufficient"` sin fallback;
- `partial` conserva `missing_information`;
- `insufficient` escribe `context_sufficiency="insufficient"`;
- contexto vacío produce `insufficient` sin invocar el LLM;
- fallo configurando structured output usa fallback técnico;
- fallo en `grader.invoke(...)` usa fallback técnico;
- salida malformada activa fallback técnico.

Pruebas de integración del grafo:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_graph
```

Casos relevantes:

- el nodo `sufficient_context_gate` queda registrado;
- `sufficient` continúa hacia generación y Self-Refine;
- `partial` continúa hacia generación con advertencia de respuesta parcial;
- `insufficient` no ejecuta `generate_answer` y termina con respuesta específica;
- `sufficient_context_trace` existe en estado interno, pero no en `LangChainRagResult`.

Verificación complementaria:

```bash
python -m compileall agents/consulta_normativa/langchain_rag agents/consulta_normativa/tests
python -m unittest agents.consulta_normativa.tests.test_rag_base agents.consulta_normativa.tests.test_langchain_rag_main agents.consulta_normativa.tests.test_langchain_rag_graph
```

## Coste operacional

El gate realiza una sola llamada LLM por consulta con evidencia recuperada.

```text
consulta con evidencia suficiente/parcial:
1 llamada al gate + 1 llamada al generador + Self-Refine según corresponda

consulta con contexto insuficiente:
1 llamada al gate + 0 llamadas al generador + 0 llamadas a Self-Refine
```

Su coste no escala en número de llamadas con `top_k`, porque evalúa el contexto completo en una sola invocación.

## Riesgos

- Puede clasificar como `insufficient` un contexto que sí contiene evidencia útil parcial.
- Puede clasificar como `sufficient` un contexto que omite excepciones o condiciones normativas importantes.
- El fallback técnico es fail-open; debe monitorearse porque permite generación cuando el gate falla.
- Combinado con Self-Refine, mejora el control pero aumenta latencia y dificulta atribuir mejoras a una sola técnica.
- No reemplaza evaluación ARES ni validación experta SST.

## Ejemplo de integración en LangGraph

```python
from agents.consulta_normativa.langchain_rag.core.routes import evidence_route, sufficient_context_route
from agents.consulta_normativa.langchain_rag.validation.self_refine import self_refine_node
from agents.consulta_normativa.langchain_rag.validation.sufficient_context_gate import sufficient_context_gate_node


workflow.add_node("retrieve", retrieve_node(retriever, top_k))
workflow.add_node("normalize_documents", normalize_documents_node)
workflow.add_node("expand_parent_documents", expand_parent_documents_node(parent_lookup))
workflow.add_node("record_retrieval_trace", record_retrieval_trace_node)
workflow.add_node("fallback_answer", fallback_answer_node)
workflow.add_node("format_context", format_context_node)
workflow.add_node("sufficient_context_gate", sufficient_context_gate_node(llm))
workflow.add_node("insufficient_context_answer", insufficient_context_answer_node)
workflow.add_node("build_messages", build_messages_node)
workflow.add_node("generate_answer", generate_answer_node(llm))
workflow.add_node("self_refine", self_refine_node(llm))
workflow.add_node("format_result", format_result_node)

workflow.add_edge("retrieve", "normalize_documents")
workflow.add_edge("normalize_documents", "expand_parent_documents")
workflow.add_edge("expand_parent_documents", "record_retrieval_trace")
workflow.add_conditional_edges(
    "record_retrieval_trace",
    evidence_route,
    {"with_evidence": "format_context", "without_evidence": "fallback_answer"},
)
workflow.add_edge("fallback_answer", "format_result")
workflow.add_edge("format_context", "sufficient_context_gate")
workflow.add_conditional_edges(
    "sufficient_context_gate",
    sufficient_context_route,
    {
        "answerable": "build_messages",
        "partial": "build_messages",
        "insufficient": "insufficient_context_answer",
    },
)
workflow.add_edge("insufficient_context_answer", "format_result")
workflow.add_edge("build_messages", "generate_answer")
workflow.add_edge("generate_answer", "self_refine")
workflow.add_edge("self_refine", "format_result")
```
