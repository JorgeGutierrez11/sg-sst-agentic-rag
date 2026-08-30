# Plan de integración: Retrieval Relevance Grading

## Objetivo

Integrar `Retrieval Relevance Grading` como la técnica de validación activa en el grafo LangGraph RAG, desactivando temporalmente `Self-Refine` del flujo principal para comparar una sola intervención de validación a la vez.

## Decisión de arquitectura

El grafo debe activar solo una técnica de validación en esta iteración: filtrado de relevancia documental antes de construir el contexto. `Self-Refine` debe quedar disponible como módulo, pero fuera del runtime principal.

Flujo objetivo:

```text
retrieve
-> normalize_documents
-> expand_parent_documents
-> retrieval_relevance_grading
-> record_retrieval_trace
-> evidence_route
-> format_context | fallback_answer
-> build_messages
-> generate_answer
-> format_result
```

Este orden permite evaluar relevancia después de la expansión a parent documents y antes de construir contexto, referencias y respuesta final.

## Alcance

### Incluido

- Declarar la dependencia requerida por la técnica.
- Corregir tests de `Retrieval Relevance Grading` para el runner oficial del repo.
- Fortalecer la política fail-open y la trazabilidad.
- Integrar `retrieval_relevance_grading_node` en `graph.py`.
- Desactivar `self_refine_node` del flujo principal sin borrar el módulo.
- Verificar que el grafo siga produciendo `LangChainRagResult`.

### No incluido

- Activar `Sufficient Context Gate`.
- Desactivar el llamado en el grafo a `Self-Refine`.
- Crear una arquitectura de flags compleja.
- Cambiar el pipeline offline de corpus.
- Modificar la colección Chroma o los datos procesados.

## Archivos a modificar

- `requirements.txt` — agregar `pydantic>=2,<3` si no existe.
- `agents/consulta_normativa/langchain_rag/validation/retrieval_relevance_grading.py` — mejorar seguridad, fallback y trazas.
- `agents/consulta_normativa/langchain_rag/graph.py` — integrar esta técnica y desactivar Self-Refine del camino principal.
- `agents/consulta_normativa/tests/test_retrieval_relevance_grading.py` — ajustar tests al contrato real y a `unittest`.
- `agents/consulta_normativa/tests/test_langchain_rag_graph.py` — actualizar o agregar cobertura del nuevo wiring del grafo si aplica.

## Tareas de implementación

### 1. Declarar dependencia Pydantic v2

**Archivo:** `requirements.txt`

Agregar:

```txt
pydantic>=2,<3
```

**Criterio de aceptación:** importar `retrieval_relevance_grading.py` no falla por dependencia ausente.

**Verificación:**

```bash
python -m unittest agents.consulta_normativa.tests.test_retrieval_relevance_grading
```

Al inicio puede fallar por assertions de tests, pero no debe fallar con `ModuleNotFoundError: No module named 'pydantic'`.

### 2. Corregir contrato de los fakes de test

**Archivo:** `agents/consulta_normativa/tests/test_retrieval_relevance_grading.py`

Los fakes que simulan `with_structured_output(...).invoke(...)` deben devolver todos los campos requeridos por `RelevanceGrade`:

```python
{
    "relevant": True,
    "reason": "El documento contiene evidencia normativa directa.",
}
```

o:

```python
{
    "relevant": False,
    "reason": "El documento solo comparte términos generales, sin aportar evidencia útil.",
}
```

**Criterio de aceptación:** los tests no dependen de validaciones incompletas que disparen fail-open accidentalmente.

### 3. Normalizar tests a `unittest`

**Archivo:** `agents/consulta_normativa/tests/test_retrieval_relevance_grading.py`

Convertir tests estilo pytest a clases `unittest.TestCase`, porque el comando oficial del repo es:

```bash
python -m unittest agents.consulta_normativa.tests.test_retrieval_relevance_grading
```

**Casos mínimos:**

- Sin documentos: devuelve lista vacía y traza con contadores en cero.
- Documento relevante: conserva el documento.
- Documento irrelevante: filtra el documento.
- Error configurando structured output: conserva todos los documentos por fail-open.
- Error calificando un documento individual: conserva ese documento y marca fallback individual.
- Todos los documentos rechazados: aplica política conservadora definida en la tarea 4.

### 4. Agregar protección contra falso negativo total

**Archivo:** `agents/consulta_normativa/langchain_rag/validation/retrieval_relevance_grading.py`

Después de evaluar todos los documentos, si la entrada tenía documentos pero todos fueron rechazados por el grader, conservar al menos el primer documento original.

Política objetivo:

```text
Si el grader rechaza todos los documentos, conservar el top-1 original como fallback conservador.
```

La traza debe indicar explícitamente que ese documento fue conservado por fallback conservador, no porque el grader lo haya considerado relevante.

**Criterio de aceptación:** el nodo nunca convierte una recuperación no vacía en una lista vacía solo por juicio LLM.

### 5. Mejorar trazabilidad del fallback global

**Archivo:** `agents/consulta_normativa/langchain_rag/validation/retrieval_relevance_grading.py`

Actualmente `relevance_grading_fallback(...)` conserva documentos pero devuelve:

```python
"documents": []
```

Cambiarlo para producir una traza por documento conservado:

```python
build_document_trace(
    index=index,
    document=document,
    relevant=True,
    reason="Documento conservado por política fail-open porque el grader no pudo configurarse.",
    fallback=True,
    error=type(error).__name__,
)
```

**Criterio de aceptación:** todo documento conservado por fallback queda visible en la traza.

**Criterio de aceptación:** el archivo pasa revisión básica de formato/diff.

### 7. Integrar `Retrieval Relevance Grading` en el grafo principal

**Archivo:** `agents/consulta_normativa/langchain_rag/graph.py`

Importar:

```python
from agents.consulta_normativa.langchain_rag.validation.retrieval_relevance_grading import (
    retrieval_relevance_grading_node,
)
```

Agregar nodo:

```python
workflow.add_node(
    "retrieval_relevance_grading",
    retrieval_relevance_grading_node(llm),
)
```

Cambiar el flujo:

```python
workflow.add_edge("expand_parent_documents", "retrieval_relevance_grading")
workflow.add_edge("retrieval_relevance_grading", "record_retrieval_trace")
```

Desactivar el edge anterior:

```python
workflow.add_edge("expand_parent_documents", "record_retrieval_trace")
```

**Criterio de aceptación:** `record_retrieval_trace` recibe documentos ya filtrados por relevancia.

### 8. Desactivar `Self-Refine` del flujo principal

**Archivo:** `agents/consulta_normativa/langchain_rag/graph.py`

Quitar `self_refine_node` del camino principal. El módulo puede quedar importable y testeable, pero no debe ejecutarse por defecto.

Flujo objetivo al final de generación:

```python
workflow.add_edge("build_messages", "generate_answer")
workflow.add_edge("generate_answer", "format_result")
```

Eliminar o comentar:

```python
workflow.add_node("self_refine", self_refine_node(llm))
workflow.add_edge("generate_answer", "self_refine")
workflow.add_edge("self_refine", "format_result")
```

También remover el import si ya no se usa.

**Criterio de aceptación:** el grafo principal genera una respuesta una sola vez y no aplica refinamiento posterior.

### 9. Actualizar tests del grafo

**Archivo:** `agents/consulta_normativa/tests/test_langchain_rag_graph.py`

Verificar que el grafo:

- llama el flujo de retrieval;
- normaliza documentos;
- expande parent documents si `parent_lookup` existe;
- filtra por relevancia antes de construir contexto;
- no ejecuta Self-Refine por defecto;
- sigue produciendo `LangChainRagResult`.

Si los tests existentes usan fakes de LLM, estos deben soportar:

- invocación normal para generar respuesta;
- `with_structured_output(RelevanceGrade)` para el grader.

**Criterio de aceptación:** los tests del grafo reflejan el flujo nuevo, no el wiring anterior.

### 10. Ejecutar verificación enfocada

Comandos mínimos:

```bash
python -m unittest agents.consulta_normativa.tests.test_retrieval_relevance_grading
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_graph
python -m compileall agents/consulta_normativa/langchain_rag agents/consulta_normativa/tests
```

Si el cambio toca rutas compartidas, ejecutar además:

```bash
python -m unittest agents.consulta_normativa.tests.test_rag_base agents.consulta_normativa.tests.test_langchain_rag_main agents.consulta_normativa.tests.test_langchain_rag_graph
```

## Riesgos a revisar después de implementar

- Falsos negativos del grader eliminando evidencia normativa útil.
- Aumento de latencia por una llamada LLM por documento.
- Diferencia entre evaluar child chunks y parent chunks; este plan evalúa después de parent expansion.
- Cambios en `references`: si un documento es filtrado, su referencia desaparece de la respuesta.
- Posible degradación de recall aunque mejore precisión aparente.
- Interacción futura con `Sufficient Context Gate`; no debe activarse en la misma iteración.

## Resultado esperado

Al terminar este plan, el runtime principal usará `Retrieval Relevance Grading` como filtro previo al armado de contexto, mientras `Self-Refine` quedará desactivada del grafo principal. La técnica tendrá dependencia declarada, tests ejecutables con `unittest`, fallback conservador y trazabilidad suficiente para analizar su impacto experimental.
