# Plan de integración: Self-Refine

## Objetivo

Corregir los riesgos funcionales y de pruebas de `Self-Refine`, y dejar una integración explícita en el grafo LangGraph RAG para evaluar esta técnica como variante controlada del flujo principal.

## Decisión de arquitectura

`Self-Refine` debe tratarse como una técnica de validación posterior a la generación de respuesta. Su responsabilidad no es recuperar ni filtrar documentos, sino revisar una respuesta inicial contra el contexto recuperado y, si detecta problemas, producir una versión refinada usando únicamente ese contexto.

Flujo objetivo cuando `Self-Refine` esté activo:

```text
retrieve
-> normalize_documents
-> expand_parent_documents
-> record_retrieval_trace
-> evidence_route
-> format_context | fallback_answer
-> build_messages
-> generate_answer
-> self_refine
-> format_result
```

Para evaluación experimental, no debe mezclarse con otras técnicas de validación activas en el mismo flujo, salvo que se esté evaluando explícitamente una variante combinada.

## Alcance

### Incluido

- Corregir comportamiento inseguro cuando la respuesta inicial esté vacía.
- Fortalecer trazabilidad de `self_refine_trace`.
- Normalizar los tests de `Self-Refine` al runner oficial `unittest`.
- Agregar pruebas de integración del grafo con `Self-Refine` activo.
- Integrar `self_refine_node` en el grafo de forma explícita y reversible.
- Verificar que `LangChainRagResult.answer` use la respuesta refinada cuando aplique.

### No incluido

- Borrar `Retrieval Relevance Grading`.
- Activar `Sufficient Context Gate`.
- Ejecutar varias iteraciones de refinamiento.
- Crear una arquitectura compleja de flags globales.
- Cambiar el pipeline offline de corpus.

## Archivos a modificar

- `agents/consulta_normativa/langchain_rag/validation/self_refine.py` — corregir fallback de respuesta vacía y mejorar contrato de trazas.
- `agents/consulta_normativa/langchain_rag/graph.py` — integrar `self_refine_node` después de `generate_answer`.
- `agents/consulta_normativa/tests/test_self_refine.py` — convertir tests a `unittest.TestCase` y ampliar casos críticos.
- `agents/consulta_normativa/tests/test_langchain_rag_graph.py` — cubrir wiring del grafo con Self-Refine.
- `requirements.txt` — verificar que `pydantic>=2,<3` permanezca declarado.

## Tareas de implementación

### 1. Confirmar dependencia Pydantic v2

**Archivo:** `requirements.txt`

Verificar que exista:

```txt
pydantic>=2,<3
```

**Criterio de aceptación:** `self_refine.py` puede importarse en un entorno instalado desde `requirements.txt`.

**Verificación:**

```bash
python -m unittest agents.consulta_normativa.tests.test_self_refine
```

Si falla por entorno local con `ModuleNotFoundError: No module named 'pydantic'`, reinstalar dependencias antes de continuar.

### 2. Normalizar tests a `unittest`

**Archivo:** `agents/consulta_normativa/tests/test_self_refine.py`

Convertir las funciones sueltas estilo pytest a una clase `unittest.TestCase`.

Estructura objetivo:

```python
import unittest


class SelfRefineNodeTests(unittest.TestCase):
    def test_answer_without_issues_is_preserved(self):
        ...


if __name__ == "__main__":
    unittest.main()
```

**Criterio de aceptación:** los tests se ejecutan con el runner oficial del repo:

```bash
python -m unittest agents.consulta_normativa.tests.test_self_refine
```

### 3. Corregir respuesta inicial vacía

**Archivo:** `agents/consulta_normativa/langchain_rag/validation/self_refine.py`

Problema actual: si `initial_answer` está vacío, el nodo devuelve solo `self_refine_trace` y no devuelve `answer`.

Comportamiento objetivo:

```python
return {
    "answer": initial_answer,
    "self_refine_trace": {
        "initial_answer": initial_answer,
        "needs_refinement": False,
        "refined": False,
        "feedback": "",
        "issues": [],
        "fallback": True,
        "error_stage": "input",
        "error": "EmptyInitialAnswer",
    },
}
```

**Criterio de aceptación:** el nodo siempre preserva la clave `answer`, incluso cuando no puede refinar.

### 4. Fortalecer contrato de trazabilidad

**Archivo:** `agents/consulta_normativa/langchain_rag/validation/self_refine.py`

Todas las rutas deben devolver `self_refine_trace` con las mismas claves:

- `initial_answer`
- `needs_refinement`
- `refined`
- `feedback`
- `issues`
- `fallback`
- `error_stage`
- `error`

**Criterio de aceptación:** ninguna rama devuelve trazas incompletas.

Casos a revisar:

- respuesta inicial vacía;
- error configurando structured output;
- error generando feedback;
- respuesta sin refinamiento requerido;
- refinamiento exitoso;
- error durante refinamiento;
- refinamiento vacío.

### 5. Mantener fail-open ante errores técnicos

**Archivo:** `agents/consulta_normativa/langchain_rag/validation/self_refine.py`

La política correcta es conservar la respuesta inicial cuando falle el proceso técnico de Self-Refine.

Debe preservarse este principio:

```text
Un fallo técnico de Self-Refine no debe borrar ni reemplazar la respuesta inicial.
```

**Criterio de aceptación:** ante errores del grader o del LLM de refinamiento, `result["answer"] == initial_answer`.

### 6. Agregar prueba de refinamiento con respuesta final usada por el grafo

**Archivo:** `agents/consulta_normativa/tests/test_langchain_rag_graph.py`

Agregar o ajustar una prueba de integración donde:

- el retriever devuelve evidencia;
- `generate_answer` produce una respuesta inicial;
- `self_refine_node` recibe feedback `needs_refinement=True`;
- el LLM devuelve una respuesta refinada;
- `format_result` construye `LangChainRagResult` con la respuesta refinada.

**Criterio de aceptación:**

```python
self.assertEqual(result.answer, expected_refined_answer)
```

### 7. Integrar `Self-Refine` en el grafo

**Archivo:** `agents/consulta_normativa/langchain_rag/graph.py`

Importar:

```python
from agents.consulta_normativa.langchain_rag.validation.self_refine import self_refine_node
```

Agregar nodo:

```python
workflow.add_node("self_refine", self_refine_node(llm))
```

Cambiar el tramo final del flujo:

```python
workflow.add_edge("build_messages", "generate_answer")
workflow.add_edge("generate_answer", "self_refine")
workflow.add_edge("self_refine", "format_result")
```

Eliminar o reemplazar:

```python
workflow.add_edge("generate_answer", "format_result")
```

**Criterio de aceptación:** toda respuesta con evidencia pasa por `Self-Refine` antes de crear el resultado público.

### 8. Evitar mezcla accidental con otra técnica activa

**Archivo:** `agents/consulta_normativa/langchain_rag/graph.py`

Si el objetivo experimental es evaluar `Self-Refine` de forma aislada, desactivar temporalmente `Retrieval Relevance Grading` del flujo principal.

Flujo aislado de Self-Refine:

```text
expand_parent_documents
-> record_retrieval_trace
```

en lugar de:

```text
expand_parent_documents
-> retrieval_relevance_grading
-> record_retrieval_trace
```

**Criterio de aceptación:** el grafo activo evalúa una sola técnica de validación en esta iteración.

### 9. Revisar contrato público de trazas

**Archivos:**

- `agents/consulta_normativa/langchain_rag/models.py`
- `agents/consulta_normativa/langchain_rag/graph.py`

Decidir si `self_refine_trace` debe quedar solo en estado interno o exponerse en el resultado público/debug.

Recomendación inicial: mantenerlo interno para no ampliar el contrato público hasta que la técnica esté estabilizada.

**Criterio de aceptación:** la decisión queda reflejada en tests. Si no se expone, los tests no deben esperar `self_refine_trace` en `LangChainRagResult`.

### 10. Ejecutar verificación enfocada

Comandos mínimos:

```bash
python -m unittest agents.consulta_normativa.tests.test_self_refine
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_graph
python -m compileall agents/consulta_normativa/langchain_rag agents/consulta_normativa/tests
```

Si se toca wiring compartido del RAG, ejecutar también:

```bash
python -m unittest agents.consulta_normativa.tests.test_rag_base agents.consulta_normativa.tests.test_langchain_rag_main agents.consulta_normativa.tests.test_langchain_rag_graph
```

## Riesgos a revisar después de implementar

- Self-Refine puede mejorar una respuesta, pero también puede introducir nuevas alucinaciones.
- No existe todavía una validación posterior fuerte de citas `[n]` contra el contexto.
- Aumenta latencia porque puede hacer una llamada adicional para feedback y otra para refinamiento.
- Si se combina con `Retrieval Relevance Grading`, será difícil atribuir mejoras o regresiones a una técnica específica.
- Si el contexto recuperado es incompleto, Self-Refine puede volver la respuesta más cauta, pero no puede recuperar evidencia ausente.

## Resultado esperado

Al terminar este plan, `Self-Refine` estará corregido, cubierto por pruebas ejecutables con `unittest` e integrado de forma explícita en el grafo cuando se quiera evaluar esta técnica. El flujo principal podrá usar Self-Refine como validación posterior a generación, sin mezclarla accidentalmente con otras técnicas experimentales.
