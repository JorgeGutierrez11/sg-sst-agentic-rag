## Objetivo

Convertir `agents/consulta_normativa/langchain_rag/` en una implementación real con primitivas de LangChain/LangGraph — no una copia del RAG manual con otro nombre — manteniendo **contexto, referenciado y respuesta final** equivalentes al RAG manual (`manual_implementation/`, que queda congelado y no se toca).

## Decisión de arquitectura

La generación cumple "interfaz estándar de LangChain" con `SystemMessage` / `HumanMessage` + `llm.invoke(messages)` directo, sin harness de agente.

Por lo tanto, esta sección no implementa un agente LangChain con `create_agent(...)`; implementa un **flujo LangGraph controlado que usa primitivas de mensajes/modelo de LangChain**.

## Confirmado: el manual ya evalúa evidencia antes de responder

El RAG manual tiene lógica equivalente a `assess_evidence` / `fallback_answer`. Por lo tanto `langchain_rag/` debe **replicar ese mismo criterio y el mismo fallback**, no inventar uno nuevo. Esto es lo que hace legítimo mantener la rama condicional en el grafo sin violar el requisito de equivalencia.

El criterio esperado, según el comportamiento actual, es simple: hay evidencia si la lista normalizada de documentos no está vacía (`bool(documents)`). La Fase 2 debe confirmarlo contra el código manual antes de implementar, no asumir que existe un umbral más complejo.

## Diseño del grafo

```
retrieve
  → llama al retriever con el mismo criterio (top_k, filtros) que usa el manual

normalize_documents
  → resultados crudos del retriever → list[RetrievedDocument]

assess_evidence
  → replica EXACTAMENTE la condición/umbral que usa el manual para decidir
    si hay evidencia suficiente (mismo criterio, no una aproximación)

  ├── sin evidencia
  │     → fallback_answer
  │       → replica el mismo texto/lógica de la rama equivalente del manual
  │     → format_result
  │
  └── con evidencia
        → format_context
          → build_context_and_references, mismo algoritmo/output que el manual
        → build_messages
          → SystemMessage(BASE_SYSTEM_INSTRUCTIONS) + HumanMessage(pregunta + contexto)
        → generate_answer
          → llm.invoke(messages)
        → format_result
          → LangChainRagResult(answer, references, context, prompt)
```

## Estado del grafo

```python
class RagGraphState(TypedDict, total=False):
    question: str
    raw_results: dict[str, Any]
    documents: list[RetrievedDocument]
    has_evidence: bool
    context: str
    references: list[str]
    messages: list[Any]
    answer: str
    result: LangChainRagResult
```

## Extracción de la respuesta

No usar `result["messages"][-1]` a ciegas.

En el diseño actual, `generate_answer` invoca el modelo directamente con `llm.invoke(messages)`, por lo que el resultado esperado es un `AIMessage` o un objeto equivalente con `.content`. La extracción primaria debe leer ese contenido de forma explícita.

Si en el futuro se recibe un estado con lista de mensajes, entonces sí se debe filtrar por `AIMessage` con contenido no vacío antes de extraer el texto. Esa regla queda como protección futura, no como supuesto principal del diseño actual.

## Contrato público (sin cambios)

```python
LangChainRagResult(
    answer: str,
    references: list[str],
    context: str,
    prompt: str,
)
```

## Fases de implementación

### Fase 1 — Dependencias y contrato
1. Confirmar disponibilidad de `langchain`, `langgraph`; mantener `langchain-groq`.
2. **Fijar versión exacta de LangChain/LangGraph en `requirements.txt`.** La API es reciente y cambia rápido; sin pin, un upgrade silencioso puede romper la equivalencia con el manual sin que se note en tests.
3. Imports perezosos para que tests sin dependencias opcionales no fallen al importar el paquete.
4. Confirmar el contrato público `LangChainRagResult` (sin cambios respecto al actual).

### Fase 2 — Extraer el criterio de evidencia del manual
1. Localizar en `manual_implementation/` la condición exacta usada para decidir "evidencia suficiente" y el texto/lógica de la respuesta cuando no la hay. El criterio esperado es `bool(documents)`, pero debe confirmarse contra el código.
2. Documentar ambos (condición + fallback) como referencia fija para `langchain_rag/` — sin importar código del manual, solo replicando el criterio.
3. No modificar nada dentro de `manual_implementation/`.

### Fase 3 — Construir `graph.py` como orquestador principal
1. Implementar `StateGraph` con los nodos del diseño anterior: `retrieve → normalize_documents → assess_evidence → (fallback_answer | format_context → build_messages → generate_answer) → format_result`.
2. `retrieve`, `format_context`/`build_references` deben producir el mismo resultado que el manual dado el mismo input. Si no se pueden importar directamente sin tocar `manual_implementation/`, replicar el algoritmo exacto en `formatting.py` local a `langchain_rag/`.
3. `assess_evidence` y `fallback_answer` replican el criterio documentado en la Fase 2 — no aproximaciones ni umbrales nuevos.
4. `generate_answer` usa `llm.invoke(messages)` con mensajes LangChain (`SystemMessage`/`HumanMessage`), no `create_agent`.
5. `prompts.py`: separar instrucciones de sistema, plantilla de pregunta y formato de contexto para uso con mensajes.

### Fase 4 — `main.py` mínimo
1. Construir el grafo una sola vez al iniciar runtime:
   ```python
   graph = build_langgraph_rag(llm=llm, retriever=retriever, top_k=DEFAULT_TOP_K)
   ```
2. Responder con `answer_with_langgraph(question, graph)` como única ruta.
3. Sin subcomandos, sin banderas experimentales, sin selección entre chain/graph.
4. Eliminar `chain.py` y cualquier import hacia él — no hay ninguna construcción en este diseño que lo justifique.

### Fase 5 — Duplicación de helpers (deuda técnica aceptada)
1. Mantener helpers determinísticos locales en `langchain_rag/formatting.py`.
2. No se unifica con `agents/shared/` en esta sección (fuera de alcance); se acepta la duplicación de helpers de formato como costo consciente, no accidental.

### Fase 6 — Tests (fake-based, sin Groq ni Chroma real)
1. `graph.py`, ruta con evidencia: recupera, arma contexto/referencias, invoca `llm.invoke` con los mensajes esperados.
2. `graph.py`, ruta sin evidencia: no invoca al LLM y devuelve el mismo fallback documentado en la Fase 2.
3. **Test de equivalencia directo:** dado el mismo fixture de documentos/pregunta, comparar `context`, `references` y entrada de generación (`messages` o contenido equivalente del prompt) contra el manual — no basta con inspección visual.
4. Comparar `answer` exactamente solo en la ruta sin evidencia o cuando se use un LLM fake determinístico. No exigir equivalencia textual exacta entre respuestas generadas por LLMs reales.
5. `main.py` construye runtime una sola vez y responde usando la única ruta.
6. `chain.py` no existe ni se importa en ningún test.

## Criterios de aceptación

- El grafo usa `StateGraph` con nodos explícitos y la rama condicional por evidencia, replicando exactamente el criterio del manual.
- `context` y `references` son equivalentes a los del RAG manual dado el mismo input, verificado con test de equivalencia.
- `answer` es equivalente al manual en la ruta fallback o con LLM fake determinístico; no se exige igualdad textual para respuestas generadas por LLM real.
- La generación usa `SystemMessage`/`HumanMessage` + `llm.invoke`, no `create_agent`.
- `chain.py` no se conserva — se elimina junto con sus imports.
- No se modifica nada dentro de `agents/consulta_normativa/manual_implementation/`.
- No se modifica código fuera de `agents/consulta_normativa/langchain_rag/` (salvo `requirements.txt` y `agents/shared/` solo si es estrictamente necesario).
- `main.py` es mínimo, sin subcomandos.
- Versión de LangChain/LangGraph fijada en `requirements.txt`.
- Sin llamadas reales a Groq ni a Chroma real en tests.

## Próximo paso

Extraer y documentar (Fase 2) el criterio exacto de evidencia y el fallback del manual antes de escribir una sola línea de `graph.py`. Todo lo demás del plan depende de que ese criterio quede fijado primero.
