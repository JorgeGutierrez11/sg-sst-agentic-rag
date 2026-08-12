# Plan de implementación: pipeline RAG con LangChain/LangGraph

Este plan propone una implementación paralela del RAG de consulta normativa usando LangChain y LangGraph dentro de `agents/consulta_normativa/`, sin reemplazar todavía el RAG base actual. El objetivo es conservar la misma lógica funcional —recuperar contexto desde Chroma, construir evidencia, generar respuesta con Groq y devolver referencias— pero expresarla como pipeline composable y, posteriormente, como grafo extensible.

## Objetivo

Crear una nueva carpeta dentro de `agents/consulta_normativa/` con una variante experimental del pipeline RAG usando LangChain/LangGraph.

La implementación debe permitir comparar contra el RAG base actual sin romperlo.

## Alcance

### Incluido

- Nueva carpeta para el pipeline LangChain/LangGraph.
- Reutilización de la colección Chroma existente.
- Reutilización de configuración runtime actual.
- Reutilización de `ChatGroq` como LLM.
- Conversión de resultados recuperados a contexto textual con referencias.
- Pipeline LangChain lineal equivalente al flujo actual.
- Grafo LangGraph mínimo equivalente al pipeline lineal.
- Tests unitarios con fakes/mocks, sin llamadas reales a Groq ni Chroma.

### Fuera de alcance

- Reemplazar el CLI actual.
- Cambiar la indexación en Chroma.
- Agregar memoria conversacional.
- Agregar reranking.
- Agregar recuperación jerárquica hacia parents.
- Agregar defensa formal contra prompt injection.
- Agregar validación avanzada de respuesta.
- Cambiar el modelo generativo.

## Estructura propuesta

```txt
agents/consulta_normativa/langchain_rag/
  __init__.py
  models.py
  formatting.py
  chain.py
  graph.py

agents/consulta_normativa/tests/
  test_langchain_rag_formatting.py
  test_langchain_rag_chain.py
  test_langchain_rag_graph.py
```

## Responsabilidades por archivo

| Archivo | Responsabilidad |
|---|---|
| `models.py` | Definir estructuras livianas para entrada/salida del pipeline experimental. |
| `formatting.py` | Convertir documentos recuperados y metadata en contexto y referencias. |
| `chain.py` | Implementar pipeline LangChain lineal: question → retrieval → context → prompt → LLM → answer. |
| `graph.py` | Implementar grafo LangGraph mínimo con nodos equivalentes al pipeline lineal. |
| `__init__.py` | Exportar únicamente las funciones públicas necesarias para pruebas o uso futuro. |

## Diseño funcional

El pipeline debe mantener la misma lógica conceptual del RAG base actual:

```txt
pregunta
  → recuperar documentos desde Chroma
  → normalizar documentos recuperados
  → construir contexto textual
  → construir prompt
  → invocar ChatGroq
  → devolver respuesta, contexto y referencias
```

La diferencia es que LangChain/LangGraph expresan el flujo como componentes composables.

## Interfaces propuestas

### `models.py`

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LangChainRagResult:
    answer: str
    references: list[str]
    context: str
    prompt: str


@dataclass(frozen=True)
class RetrievedDocument:
    document: str
    metadata: dict[str, Any]
```

### `formatting.py`

Funciones esperadas:

```python
def reference_from_metadata(metadata: dict[str, Any]) -> str: ...

def metadata_context(metadata: dict[str, Any]) -> str: ...

def build_context(documents: list[RetrievedDocument]) -> str: ...

def build_references(documents: list[RetrievedDocument]) -> list[str]: ...
```

Estas funciones pueden partir de la lógica existente en `agents/consulta_normativa/rag_base.py`, pero deben vivir en la nueva carpeta para evitar acoplar el experimento al flujo base.

### `chain.py`

Funciones esperadas:

```python
def build_groq_llm(): ...

def build_langchain_rag_chain(retriever, llm): ...

def answer_with_langchain(question: str, retriever, llm) -> LangChainRagResult: ...
```

El chain debe conservar las instrucciones del prompt base actual.

### `graph.py`

Funciones esperadas:

```python
def build_langgraph_rag(llm, retriever): ...

def answer_with_langgraph(question: str, graph) -> LangChainRagResult: ...
```

El grafo mínimo debe tener estos nodos:

```txt
retrieve
  → format_context
  → generate
  → format_result
```

## Plan por tareas

### Tarea 1 — Crear modelos y formateo compartido

**Archivos:**

- Crear `agents/consulta_normativa/langchain_rag/__init__.py`
- Crear `agents/consulta_normativa/langchain_rag/models.py`
- Crear `agents/consulta_normativa/langchain_rag/formatting.py`
- Crear `agents/consulta_normativa/tests/test_langchain_rag_formatting.py`

**Pasos:**

1. Crear `RetrievedDocument` y `LangChainRagResult`.
2. Copiar/adaptar la lógica de referencias y contexto desde `rag_base.py`.
3. Escribir tests para:
   - contexto vacío;
   - chunk normativo con artículo;
   - tabla con `table_index`;
   - metadata técnica útil.
4. Ejecutar:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_formatting
```

**Resultado esperado:** formateo equivalente al RAG base, aislado en la nueva carpeta.

---

### Tarea 2 — Implementar chain LangChain lineal

**Archivos:**

- Crear `agents/consulta_normativa/langchain_rag/chain.py`
- Crear `agents/consulta_normativa/tests/test_langchain_rag_chain.py`

**Pasos:**

1. Crear un adapter que reciba un retriever compatible con la salida actual de Chroma.
2. Convertir la salida del retriever a `RetrievedDocument`.
3. Construir el contexto usando `formatting.build_context()`.
4. Construir el prompt usando las instrucciones actuales.
5. Invocar el LLM usando interfaz LangChain.
6. Retornar `LangChainRagResult`.
7. Testear con fake retriever y fake LLM.
8. Ejecutar:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_chain
```

**Resultado esperado:** pipeline LangChain lineal funcional sin Chroma/Groq reales en tests.

---

### Tarea 3 — Implementar grafo LangGraph mínimo

**Archivos:**

- Crear `agents/consulta_normativa/langchain_rag/graph.py`
- Crear `agents/consulta_normativa/tests/test_langchain_rag_graph.py`

**Pasos:**

1. Definir estado del grafo con campos:
   - `question`
   - `documents`
   - `context`
   - `references`
   - `prompt`
   - `answer`
2. Crear nodo `retrieve`.
3. Crear nodo `format_context`.
4. Crear nodo `generate`.
5. Crear nodo `format_result`.
6. Conectar nodos en flujo lineal.
7. Testear con fake retriever y fake LLM.
8. Ejecutar:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_graph
```

**Resultado esperado:** grafo equivalente al chain lineal, listo para futuras ramas condicionales.

---

### Tarea 4 — Validación integrada sin cambiar el CLI actual

**Archivos:**

- Modificar solo si es necesario: `agents/consulta_normativa/langchain_rag/__init__.py`

**Pasos:**

1. Exportar funciones públicas mínimas:

```python
from agents.consulta_normativa.langchain_rag.chain import answer_with_langchain
from agents.consulta_normativa.langchain_rag.graph import answer_with_langgraph
```

2. Ejecutar tests enfocados:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_formatting agents.consulta_normativa.tests.test_langchain_rag_chain agents.consulta_normativa.tests.test_langchain_rag_graph
```

3. Ejecutar compile check:

```bash
python -m compileall agents/consulta_normativa agents/shared
```

**Resultado esperado:** implementación experimental disponible, sin alterar el CLI base.

## Criterios de aceptación

- [ ] Existe `agents/consulta_normativa/langchain_rag/`.
- [ ] El RAG base actual sigue intacto.
- [ ] El pipeline LangChain produce respuesta, contexto y referencias.
- [ ] El grafo LangGraph produce respuesta, contexto y referencias.
- [ ] Los tests no llaman Groq ni Chroma reales.
- [ ] La implementación reutiliza configuración runtime existente.
- [ ] No se agregan features fuera de alcance.

## Comandos de verificación

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_formatting agents.consulta_normativa.tests.test_langchain_rag_chain agents.consulta_normativa.tests.test_langchain_rag_graph
python -m compileall agents/consulta_normativa agents/shared
```

## Decisión de diseño

Esta implementación debe ser paralela y experimental. No debe reemplazar todavía el RAG base manual porque la línea base actual es más explícita para evaluación y depuración. LangGraph se introduce como preparación para etapas posteriores donde el flujo deje de ser lineal.
