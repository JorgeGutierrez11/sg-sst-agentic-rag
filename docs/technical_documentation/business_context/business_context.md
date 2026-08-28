# Contexto empresarial

## Propósito

El módulo `business_context` concentra la información empresarial persistente que puede ser reutilizada por otras dimensiones del agente.

Su responsabilidad es:

- mantener un perfil empresarial;
- conservar el historial conversacional;
- construir un contexto empresarial reutilizable;
- aislar la memoria por conversación mediante `thread_id`.

No realiza Query Rewriting, recuperación normativa ni generación de respuestas.

---

## Estructura implementada

```text
business_context/
├── models.py
├── profile.py
├── profile_extractor.py
├── profile_node.py
├── history.py
├── history_node.py
└── techniques/
```

---

## Cambios realizados

### `models.py`

Se definieron los contratos:

- `BusinessProfile`
- `BusinessProfileExtractionResult`
- `ConversationTurn`
- `BusinessContext`

`BusinessContext` mantiene:

```text
profile
history
current_context
```

**Motivo:** separar los datos empresariales persistentes del resto del estado interno del RAG.

---

### `profile.py`

Se agregó:

```python
update_business_profile(...)
```

Permite actualizar y sobrescribir información empresarial previamente almacenada.

Fuentes aceptadas:

```text
user_explicit
verified_derived
```

**Motivo:** impedir que cualquier salida libre del LLM sea persistida automáticamente como un hecho empresarial.

---

### `profile_extractor.py`

Se implementó extracción estructurada mediante:

```python
llm.with_structured_output(...)
```

El extractor obtiene únicamente información explícita del mensaje actual:

- actividad económica;
- código CIIU;
- número de trabajadores;
- clase de riesgo.

También conserva evidencia textual del mensaje que respalda cada dato.

**Motivo:** evitar inferencias durante la construcción del perfil.

Ejemplo:

```text
"Mi CIIU es 1240, ¿qué riesgo soy?"
```

solo permite extraer:

```text
ciiu_code = 1240
```

No se infiere `risk_class`.

---

### `profile_node.py`

Se agregó el nodo:

```python
business_profile_node(...)
```

Flujo:

```text
question
   ↓
profile extractor
   ↓
update_business_profile
   ↓
business_context.profile
```

**Motivo:** integrar la actualización del perfil dentro de LangGraph sin mezclarla con otras etapas.

---

### `history.py`

Se agregó:

```python
append_conversation_turn(...)
```

Cada turno se almacena como:

```python
{
    "user": "...",
    "assistant": "..."
}
```

**Motivo:** conservar el historial de forma estructurada y reutilizable por diferentes técnicas de memoria.

---

### `history_node.py`

Se agregó:

```python
save_conversation_turn_node(...)
```

El nodo se ejecuta después de obtener una respuesta y agrega el turno actual al historial.

También se ejecuta cuando se produce una respuesta fallback.

**Motivo:** el historial debe representar todas las interacciones reales de la conversación.

---

## Cambios en `state.py`

Se agregó:

```python
business_context: BusinessContext
```

**Motivo:** permitir que el contexto empresarial viaje dentro del estado del grafo sin mezclar sus campos con el resto del RAG.

---

## Persistencia

`build_langgraph_rag(...)` ahora puede recibir:

```python
checkpointer
```

y `answer_with_langgraph(...)` puede recibir:

```python
thread_id
```

La CLI utiliza:

```python
InMemorySaver()
```

y genera un `thread_id` por sesión.

Esto permite conservar:

```text
profile
history
current_context
```

entre preguntas de una misma conversación y mantener aisladas conversaciones diferentes.

---

## Flujo actual

```text
START
  ↓
business_profile
  ↓
técnica de contexto empresarial
  ↓
retrieve
  ↓
...
  ↓
generate / fallback
  ↓
save_conversation_turn
  ↓
format_result
```

---

## Validación

Se agregaron pruebas para:

- actualización y sobrescritura del perfil;
- extracción estructurada;
- rechazo de valores inválidos;
- persistencia por `thread_id`;
- aislamiento entre conversaciones;
- almacenamiento del historial;
- integración con CLI.

La suite correspondiente a la implementación actual ejecutó:

```text
47 tests passed
```

Los tests legacy que dependen de rutas inexistentes en esta rama no forman parte de esta validación.
