# Informe de merge — técnicas de validación LangGraph RAG

Este informe revisa los cambios actuales después del merge que incorpora técnicas de validación al flujo LangGraph RAG. Es un análisis read-only: no se modifica código ni se integran técnicas adicionales. El objetivo actual debe seguir siendo que cada técnica quede aislada, testeable y fácil de conectar al grafo para evaluación futura, no activar todas al mismo tiempo.

## Resumen ejecutivo

- El merge incorpora tres técnicas de validación: **Retrieval Relevance Grading**, **Sufficient Context Gate** y **Self-Refine**.
- Solo **Self-Refine** está cableada al grafo actual; las otras dos existen como módulos/documentación, pero no participan en runtime.
- Hay un blocker de dependencias: los nuevos módulos importan `pydantic`, pero `requirements.txt` no lo declara.
- Los tests nuevos están escritos con estilo pytest, mientras el repositorio usa `python -m unittest`; hoy no son confiables como verificación oficial.
- La documentación nueva afirma integración runtime para técnicas que todavía no están cableadas, lo cual puede contaminar la evaluación experimental.

## Archivos del merge revisados

Cambios actuales relevantes:

```text
.gitignore
agents/consulta_normativa/langchain_rag/core/routes.py
agents/consulta_normativa/langchain_rag/core/state.py
agents/consulta_normativa/langchain_rag/graph.py
agents/consulta_normativa/langchain_rag/validation/retrieval_relevance_grading.py
agents/consulta_normativa/langchain_rag/validation/self_refine.py
agents/consulta_normativa/langchain_rag/validation/sufficient_context_gate.py
agents/consulta_normativa/tests/test_retrieval_relevance_grading.py
agents/consulta_normativa/tests/test_self_refine.py
agents/consulta_normativa/tests/test_sufficient_context_gate.py
docs/decisiones/tecnicas-candidatas-mejora-rag.md
docs/technical_documentation/validation/retrieval-relevance-grading.md
docs/technical_documentation/validation/self-refine.md
docs/technical_documentation/validation/sufficient-context-gate.md
```

También aparece un cambio en datos generados:

```text
data/processed/chroma/b86488ef-7d9e-481f-980f-f0f880abe4a5/length.bin
```

Ese archivo no pertenece al código de validación y debe revisarse antes de commit para evitar meter estado local de Chroma por accidente.

## Flujo actual después del merge

El grafo actual queda conceptualmente así para el camino con evidencia:

```text
retrieve
  ↓
normalize_documents
  ↓
expand_parent_documents
  ↓
record_retrieval_trace
  ↓
evidence_route
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

Y para el camino sin evidencia:

```text
evidence_route
  ↓
fallback_answer
  ↓
format_result
```

Punto crítico: **Retrieval Relevance Grading** y **Sufficient Context Gate** no aparecen en el flujo runtime actual. No deben describirse como activas hasta que se conecten explícitamente.

## Técnica 1 — Retrieval Relevance Grading

### Qué hace

Evalúa cada documento recuperado frente a la pregunta original y filtra documentos irrelevantes antes de que el sistema decida si hay evidencia suficiente.

Archivo principal:

```text
agents/consulta_normativa/langchain_rag/validation/retrieval_relevance_grading.py
```

Contratos detectados:

```python
class RelevanceGrade(BaseModel):
    relevant: bool
    reason: str

retrieval_relevance_grading_node(llm) -> Callable[[RagGraphState], RagGraphState]
grade_document_relevance(grader, question, document) -> RelevanceGrade
build_relevance_grading_messages(question, document) -> list[Any]
relevance_grading_fallback(documents, error) -> RagGraphState
```

Entrada esperada:

```text
state["question"]
state["documents"]
```

Salida esperada:

```text
state["documents"] filtrado
state["relevance_grading_trace"]
```

### Estado de integración

Estado actual: **módulo disponible, no cableado al grafo**.

No hay import ni nodo en `graph.py` para `retrieval_relevance_grading_node`. Tampoco hay ruta dedicada en `core/routes.py`.

Punto recomendado de inserción futuro:

```text
record_retrieval_trace
  ↓
retrieval_relevance_grading
  ↓
evidence_route
```

### Problemas encontrados

#### Blocker — dependencia `pydantic` no declarada

El módulo usa Pydantic, pero `requirements.txt` no declara `pydantic`. La importación falla en un entorno limpio.

Comando reportado por el subagente:

```bash
python -m unittest agents.consulta_normativa.tests.test_retrieval_relevance_grading
```

Resultado:

```text
ModuleNotFoundError: No module named 'pydantic'
```

#### Crítico — test nominal usa salida inválida

El modelo `RelevanceGrade` exige:

```python
{"relevant": True, "reason": "..."}
```

Pero el test usa respuestas como:

```python
{"relevant": True}
```

Con Pydantic instalado, eso debería fallar o activar fallback. El test no valida el contrato real.

#### Warning — documentación afirma integración no existente

`docs/technical_documentation/validation/retrieval-relevance-grading.md` describe un flujo con `grade_retrieval_relevance`, pero el grafo actual no ejecuta ese nodo.

### Mejora recomendada

- Mantener la técnica como módulo aislado.
- Agregar `pydantic` o cambiar el contrato para no depender de Pydantic en runtime.
- Convertir tests a `unittest.TestCase` o declarar pytest como runner oficial.
- Corregir fixtures para incluir `reason`.
- Documentar estado real: **implementada como módulo, no activa en runtime**.

## Técnica 2 — Sufficient Context Gate

### Qué hace

Evalúa si el contexto completo recuperado contiene evidencia suficiente para responder la pregunta antes de generar la respuesta.

Archivo principal:

```text
agents/consulta_normativa/langchain_rag/validation/sufficient_context_gate.py
```

Contratos detectados:

```python
class ContextSufficiency(str, Enum):
    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"

class SufficientContextGrade(BaseModel):
    level: ContextSufficiency
    reason: str
    missing_information: list[str]

sufficient_context_gate_node(llm) -> Callable[[RagGraphState], RagGraphState]
grade_context_sufficiency(grader, question, context) -> SufficientContextGrade
build_sufficient_context_messages(question, context) -> list[Any]
sufficient_context_fallback(error) -> RagGraphState
```

Entrada esperada:

```text
state["question"]
state["context"]
```

Salida esperada:

```text
state["context_sufficiency"]
state["sufficient_context_trace"]
```

### Estado de integración

Estado actual: **módulo disponible, no cableado al grafo**.

`core/routes.py` agrega:

```python
sufficient_context_route(state)
```

pero `graph.py` no registra un nodo de sufficient-context ni una arista condicional que use esa ruta.

Punto recomendado de inserción futuro:

```text
format_context
  ↓
sufficient_context_gate
  ↓
sufficient_context_route
  ├── answerable → build_messages
  └── insufficient → fallback_answer
```

### Problemas encontrados

#### Blocker — dependencia `pydantic` no declarada

El test enfocado falla por falta de Pydantic:

```bash
python -m unittest agents.consulta_normativa.tests.test_sufficient_context_gate
```

Resultado:

```text
ModuleNotFoundError: No module named 'pydantic'
```

#### Crítico — documentación afirma integración runtime que no existe

La documentación muestra `format_context -> assess_sufficient_context -> build_messages/fallback_answer`, pero `graph.py` mantiene `format_context -> build_messages`.

#### Warning — ruta demasiado permisiva

La ruta actual considera solo:

```python
if state.get("context_sufficiency") == "insufficient":
    return "insufficient"
return "answerable"
```

Cualquier valor ausente, inválido o mal escrito pasa como `answerable`. Si el fail-open es intencional, debe quedar trazado explícitamente; si no, puede esconder bugs de estado.

### Mejora recomendada

- Mantener el gate aislado hasta tener una variante experimental clara.
- Agregar tests para `sufficient_context_route`.
- Hacer explícito el comportamiento ante estado ausente/inválido.
- Documentar estado real: **implementado como módulo y ruta auxiliar, no activo en runtime**.

## Técnica 3 — Self-Refine

### Qué hace

Valida la respuesta generada y, si detecta problemas, pide una segunda generación refinada usando pregunta, contexto, respuesta inicial y feedback estructurado.

Archivo principal:

```text
agents/consulta_normativa/langchain_rag/validation/self_refine.py
```

Contratos detectados:

```python
class SelfRefineFeedback(BaseModel):
    needs_refinement: bool
    feedback: str
    issues: list[str]

self_refine_node(llm) -> Callable[[RagGraphState], RagGraphState]
generate_self_refine_feedback(grader, question, context, initial_answer) -> SelfRefineFeedback
generate_refined_answer(llm, question, context, initial_answer, feedback) -> str
build_feedback_messages(question, context, initial_answer) -> list[Any]
build_refinement_messages(question, context, initial_answer, feedback) -> list[Any]
self_refine_fallback(initial_answer, error, stage, feedback=None) -> RagGraphState
```

Entrada esperada:

```text
state["question"]
state["context"]
state["answer"]
```

Salida esperada:

```text
state["answer"] refinada o preservada
state["self_refine_trace"]
```

### Estado de integración

Estado actual: **cableada al grafo runtime**.

El flujo cambia de:

```text
generate_answer → format_result
```

a:

```text
generate_answer → self_refine → format_result
```

Esto sí modifica comportamiento, latencia y número de llamadas al LLM en el camino con evidencia.

### Problemas encontrados

#### Blocker — dependencia `pydantic` no declarada

Self-Refine está importada desde `graph.py`. Por eso la falta de `pydantic` puede romper el runtime completo al importar el paquete.

Comando reportado por el subagente:

```bash
python -m unittest agents.consulta_normativa.tests.test_self_refine
```

Resultado:

```text
ModuleNotFoundError: No module named 'pydantic'
```

#### Crítico — tests no son compatibles con el runner oficial

Los tests están escritos como funciones pytest-style. El repositorio documenta `python -m unittest` como runner. Aunque se instale Pydantic, existe riesgo de que la suite oficial no ejecute esos tests como se espera.

#### Warning — cambio runtime no opcional

Self-Refine queda activo en todo flujo con evidencia. Esto contradice parcialmente la estrategia del proyecto: las técnicas deben ser fáciles de agregar para evaluación, no necesariamente activarse todas por defecto.

#### Warning — trazas no llegan al resultado público

`self_refine_trace` queda en `RagGraphState`, pero `LangChainRagResult` no expone si la respuesta fue refinada, preservada o si hubo fallback. Esto dificulta atribuir mejoras/regresiones durante evaluación.

### Mejora recomendada

- Volver Self-Refine opcional mediante builder experimental, flag o variante explícita.
- Agregar prueba de integración del grafo que confirme `generate_answer -> self_refine -> format_result`.
- Exponer trazas de validación de forma uniforme para evaluación futura.
- No activar nuevas técnicas por defecto sin decisión experimental explícita.

## Riesgos transversales del merge

### 1. Dependencias no declaradas

Las tres técnicas dependen de `pydantic`, pero el root manifest no lo declara. Esto es el blocker más urgente.

### 2. Estrategia de testing inconsistente

El repositorio usa comandos `unittest`, pero los tests nuevos están escritos en estilo pytest. Esto deja el merge en tierra de nadie: o se adopta pytest explícitamente, o se convierten los tests a `unittest.TestCase`.

### 3. Documentación más integrada que el código

Las docs de validation describen técnicas como si estuvieran conectadas al grafo. En realidad:

| Técnica | Estado real |
|---|---|
| Retrieval Relevance Grading | Módulo aislado, no runtime |
| Sufficient Context Gate | Módulo + ruta auxiliar, no runtime |
| Self-Refine | Runtime activo |

Esto puede invalidar conclusiones experimentales si alguien asume que las tres corren.

### 4. Activación prematura de Self-Refine

Self-Refine ya altera el flujo principal. Debe decidirse si esa técnica queda como baseline activo o como variante experimental. Mi recomendación arquitectónica: variante experimental, no default.

### 5. Falta contrato común de validaciones

Cada técnica escribe trazas propias:

```text
relevance_grading_trace
sufficient_context_trace
self_refine_trace
```

Eso está bien inicialmente, pero falta una convención clara para exponerlas en resultados de evaluación sin acoplar el grafo a cada técnica.

### 6. Archivo Chroma generado en el merge

`data/processed/chroma/.../length.bin` aparece como añadido. Dado que `data/processed/` es regenerable/local, este archivo probablemente no debe formar parte del merge salvo que exista una razón explícita.

## Recomendación arquitectónica

No integrar las tres técnicas al flujo principal ahora.

Primero estabilizar el merge con esta prioridad:

1. Resolver dependencias (`pydantic`) o evitar import obligatorio.
2. Alinear tests con `unittest` o adoptar pytest oficialmente.
3. Corregir documentación para distinguir “módulo implementado” vs “activo en runtime”.
4. Convertir Self-Refine en variante opcional si la estrategia experimental exige no alterar el baseline.
5. Definir puntos de inserción claros para cada técnica.

Puntos de inserción recomendados:

```text
retrieve
  ↓
normalize_documents
  ↓
expand_parent_documents
  ↓
record_retrieval_trace
  ↓
retrieval_relevance_grading        # opcional experimental
  ↓
evidence_route
  ↓
format_context
  ↓
sufficient_context_gate            # opcional experimental
  ↓
build_messages
  ↓
generate_answer
  ↓
self_refine                        # opcional experimental
  ↓
format_result
```

## Mejoras probables antes de integración futura

- Crear builders o flags explícitos por técnica para evitar activar todo por defecto.
- Mantener cada técnica como módulo independiente con contrato de estado documentado.
- Agregar tests de integración mínimos por punto de inserción, no solo tests aislados del nodo.
- Exponer trazas de validación para evaluación ARES/expert validation.
- Corregir fixtures de structured output para que coincidan con los modelos Pydantic.
- Evitar que docs técnicas digan “runtime activo” hasta que `graph.py` lo confirme.

## Verificación realizada

Subagentes dedicados revisaron una técnica cada uno:

- Retrieval Relevance Grading.
- Sufficient Context Gate.
- Self-Refine.

Comandos enfocados intentados por subagentes:

```bash
python -m unittest agents.consulta_normativa.tests.test_retrieval_relevance_grading
python -m unittest agents.consulta_normativa.tests.test_sufficient_context_gate
python -m unittest agents.consulta_normativa.tests.test_self_refine
```

Resultado común:

```text
ModuleNotFoundError: No module named 'pydantic'
```

También se intentó pytest para Retrieval Relevance Grading:

```bash
python -m pytest agents/consulta_normativa/tests/test_retrieval_relevance_grading.py -q
```

Resultado:

```text
No module named pytest
```

## Conclusión

El merge sí trae tres técnicas de validación, pero no están en el mismo estado de madurez. Self-Refine ya está activa y cambia el flujo runtime; Retrieval Relevance Grading y Sufficient Context Gate están implementadas como piezas aisladas. Antes de evaluar o integrar más, hay que resolver dependencias, runner de tests, documentación engañosa y activación opcional por técnica.
