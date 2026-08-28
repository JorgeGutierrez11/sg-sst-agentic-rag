# Plan de integración: Sufficient Context Gate

## Objetivo

Integrar `Sufficient Context Gate` como técnica de validación del contexto completo antes de generar respuesta, corrigiendo primero los problemas reales detectados: falta de wiring en el grafo, política ambigua para `partial`, ausencia de respuesta específica para contexto insuficiente y tests no ejecutables con `unittest`.

## Decisión de arquitectura

El gate debe ejecutarse **después de `format_context`** y **antes de `build_messages`**, porque evalúa el contexto completo ya construido.

Flujo objetivo:

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
          ├── partial -> build_messages -> generate_answer -> self_refine -> format_result
          └── insufficient -> insufficient_context_answer -> format_result
```

La decisión para esta primera integración es tratar `partial` como **answerable con advertencia**, no como bloqueo total. En SG-SST una respuesta parcial puede ser útil, pero debe explicitar que la evidencia no cubre todo lo solicitado.

## Alcance

### Incluido

- Integrar `sufficient_context_gate_node` en el grafo.
- Usar `sufficient_context_route` como ruta condicional posterior al gate.
- Diferenciar `sufficient`, `partial` e `insufficient`.
- Crear una respuesta específica para contexto insuficiente.
- Agregar advertencia de suficiencia cuando el contexto sea parcial.
- Convertir pruebas del gate a `unittest`.
- Agregar pruebas de integración del grafo.

### No incluido

- Borrar `Self-Refine`.
- Activar o mezclar `Retrieval Relevance Grading` si el experimento requiere evaluar solo esta técnica.
- Exponer `sufficient_context_trace` en `LangChainRagResult` como contrato público.
- Implementar entailment determinístico o verificación formal de citas.
- Cambiar el pipeline offline de corpus.

## Archivos a modificar

- `agents/consulta_normativa/langchain_rag/validation/sufficient_context_gate.py` — mantener contrato del nodo y revisar edge cases.
- `agents/consulta_normativa/langchain_rag/core/routes.py` — separar rutas para `sufficient`, `partial` e `insufficient`.
- `agents/consulta_normativa/langchain_rag/graph.py` — integrar gate, ruta condicional y respuesta de insuficiencia.
- `agents/consulta_normativa/tests/test_sufficient_context_gate.py` — convertir a `unittest.TestCase`.
- `agents/consulta_normativa/tests/test_langchain_rag_graph.py` — cubrir el wiring del grafo.

## Tareas de implementación

### 1. Normalizar tests del gate a `unittest`

**Archivo:** `agents/consulta_normativa/tests/test_sufficient_context_gate.py`

Convertir funciones sueltas estilo pytest a una clase `unittest.TestCase`.

Estructura objetivo:

```python
import unittest


class SufficientContextGateNodeTests(unittest.TestCase):
    def test_sufficient_context_is_answerable(self):
        ...


if __name__ == "__main__":
    unittest.main()
```

Casos mínimos:

- `sufficient` escribe `context_sufficiency="sufficient"` y traza sin fallback.
- `partial` escribe `context_sufficiency="partial"` y conserva `missing_information`.
- `insufficient` escribe `context_sufficiency="insufficient"`.
- contexto vacío produce `insufficient` sin invocar el LLM.
- fallo en `with_structured_output(...)` usa fallback técnico.
- fallo en `grader.invoke(...)` usa fallback técnico.
- salida malformada del LLM activa fallback técnico.

**Verificación:**

```bash
python -m unittest agents.consulta_normativa.tests.test_sufficient_context_gate
```

### 2. Separar explícitamente la ruta `partial`

**Archivo:** `agents/consulta_normativa/langchain_rag/core/routes.py`

Problema actual: `sufficient_context_route` solo bloquea `insufficient`; cualquier otro valor cae como `answerable`.

Comportamiento objetivo:

```python
def sufficient_context_route(state: RagGraphState) -> str:
    if state.get("context_sufficiency") == "insufficient":
        return "insufficient"

    if state.get("context_sufficiency") == "partial":
        return "partial"

    return "answerable"
```

**Criterio de aceptación:** `partial` queda visible como decisión de routing, no oculto dentro de `answerable`.

### 3. Crear respuesta específica para contexto insuficiente

**Archivo:** `agents/consulta_normativa/langchain_rag/graph.py`

Agregar un nodo distinto de `fallback_answer_node`, porque “no se recuperó contexto” no es lo mismo que “sí hubo contexto, pero no es suficiente”.

Implementación objetivo:

```python
def insufficient_context_answer_node(state: RagGraphState) -> RagGraphState:
    trace = state.get("sufficient_context_trace", {})
    missing_information = trace.get("missing_information", [])

    missing_text = "\n".join(
        f"- {item}" for item in missing_information
    )

    if missing_text:
        answer = (
            "La evidencia recuperada no es suficiente para responder completamente "
            "la pregunta. Información faltante:\n"
            f"{missing_text}"
        )
    else:
        answer = (
            "La evidencia recuperada no es suficiente para responder "
            "la pregunta con respaldo normativo."
        )

    return {
        "answer": answer,
        "references": state.get("references", []),
        "prompt": state.get("prompt", ""),
    }
```

**Criterio de aceptación:** cuando el gate devuelve `insufficient`, el grafo no llama a `generate_answer`.

### 4. Integrar `sufficient_context_gate` en el grafo

**Archivo:** `agents/consulta_normativa/langchain_rag/graph.py`

Importar:

```python
from agents.consulta_normativa.langchain_rag.core.routes import (
    evidence_route,
    sufficient_context_route,
)
from agents.consulta_normativa.langchain_rag.validation.sufficient_context_gate import (
    sufficient_context_gate_node,
)
```

Registrar nodos:

```python
workflow.add_node("sufficient_context_gate", sufficient_context_gate_node(llm))
workflow.add_node("insufficient_context_answer", insufficient_context_answer_node)
```

Cambiar el tramo posterior a `format_context`:

```python
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
```

Reemplazar la conexión directa anterior:

```python
workflow.add_edge("format_context", "build_messages")
```

**Criterio de aceptación:** toda rama con evidencia pasa por evaluación de suficiencia antes de generación.

### 5. Agregar advertencia para contexto parcial

**Archivo:** `agents/consulta_normativa/langchain_rag/graph.py`

Si `context_sufficiency == "partial"`, el generador debe recibir una instrucción clara para responder solo lo respaldado y declarar límites.

Modificar `build_messages_node` de forma mínima:

```python
context = state["context"]

if state.get("context_sufficiency") == "partial":
    trace = state.get("sufficient_context_trace", {})
    missing_information = trace.get("missing_information", [])
    missing_text = "\n".join(f"- {item}" for item in missing_information)

    context = (
        f"{context}\n\n"
        "Nota de suficiencia: el contexto recuperado solo permite una respuesta parcial. "
        "Responde únicamente lo respaldado e indica explícitamente qué información falta."
    )

    if missing_text:
        context = f"{context}\nInformación faltante identificada:\n{missing_text}"
```

**Criterio de aceptación:** `partial` no se presenta como respuesta completa.

### 6. Agregar tests de integración del grafo

**Archivo:** `agents/consulta_normativa/tests/test_langchain_rag_graph.py`

Agregar pruebas para:

1. **Gate registrado**

```python
self.assertIn("sufficient_context_gate", FakeStateGraph.latest.nodes)
```

2. **Flujo sufficient**

- `context_sufficiency="sufficient"`.
- Ejecuta `build_messages`.
- Ejecuta `generate_answer`.
- Si `self_refine` sigue activo, luego pasa por `self_refine`.
- Termina en `format_result`.

3. **Flujo partial**

- `context_sufficiency="partial"`.
- Ejecuta generación.
- El prompt/contexto entregado al generador contiene advertencia de respuesta parcial.

4. **Flujo insufficient**

- `context_sufficiency="insufficient"`.
- No ejecuta `generate_answer`.
- Produce respuesta específica de insuficiencia.
- Termina en `format_result`.

**Criterio de aceptación:** los tests fallan si el módulo existe pero no está conectado al grafo.

### 7. Mantener traza interna sin ampliar contrato público

**Archivos:**

- `agents/consulta_normativa/langchain_rag/graph.py`
- `agents/consulta_normativa/tests/test_langchain_rag_graph.py`

Decisión inicial: no agregar `sufficient_context_trace` a `LangChainRagResult` todavía.

Sí verificar en tests internos que el estado final contiene:

```python
state["sufficient_context_trace"]
```

cuando el gate se ejecuta.

**Criterio de aceptación:** la trazabilidad existe para evaluación interna sin inflar el contrato público.

### 8. Verificación final

Ejecutar:

```bash
python -m unittest agents.consulta_normativa.tests.test_sufficient_context_gate
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_graph
python -m compileall agents/consulta_normativa/langchain_rag agents/consulta_normativa/tests
```

Si se toca comportamiento compartido del RAG, ejecutar también:

```bash
python -m unittest agents.consulta_normativa.tests.test_rag_base agents.consulta_normativa.tests.test_langchain_rag_main agents.consulta_normativa.tests.test_langchain_rag_graph
```

## Riesgos a revisar después de implementar

- `partial` puede mejorar honestidad de respuesta, pero también volver respuestas demasiado conservadoras.
- El fallback técnico del gate es fail-open; debe monitorearse porque permite generación aunque la evaluación haya fallado.
- Si se combina con `Self-Refine`, será más difícil atribuir mejoras o regresiones a una sola técnica.
- El gate depende del juicio del LLM; no reemplaza evaluación ARES ni validación experta.
- La respuesta de insuficiencia debe ser clara sin parecer ausencia total de recuperación.

## Resultado esperado

Al terminar este plan, `Sufficient Context Gate` estará activo después de `format_context`, antes de generación. El grafo distinguirá contexto suficiente, parcial e insuficiente; las pruebas correrán con `unittest`; y el sistema evitará generar respuestas normales cuando el contexto no permita responder con respaldo normativo.
