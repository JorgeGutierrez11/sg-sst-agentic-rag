# Plan de implementación Parent-Document / Small-to-Big Retrieval

Este plan implementa la expansión runtime de child chunks hacia parent chunks. La preparación del corpus ya existe: el chunking genera parents y children con `parent_id`; lo que falta es que el retrieval use esos parents como contexto ampliado después de seleccionar la evidencia pequeña.

## 1. Objetivo

Implementar **Parent-Document / Small-to-Big Retrieval** como una capa común post-retrieval:

```text
retrieval activo
        ↓
child/table documents recuperados
        ↓
normalización
        ↓
expansión child → parent
        ↓
contexto ampliado
```

La expansión debe funcionar igual si el retrieval previo viene de Chroma, BM25 o Hybrid Retrieval. No debe modificar el chunking ni reconstruir índices.

## 2. Estado actual

El proyecto ya tiene la base Small-to-Big en los artefactos del corpus:

```text
data/processed/chunks/parents.jsonl
data/processed/chunks/regex_constrained_semantic/chunks.jsonl
data/processed/table_documents.jsonl
```

Estado actual por etapa:

| Etapa | Estado |
|---|---|
| Parent chunks | Implementado |
| Child chunks con `parent_id` | Implementado |
| Retrieval denso sobre child/table | Implementado |
| Retrieval BM25 sobre child/table | Implementado |
| Hybrid Retrieval sobre child/table | Planificado / integrable |
| Expansión child → parent | Faltante |
| Context assembly con parent ampliado | Faltante |
| Evaluación Small-to-Big | Faltante |

El retrieval actual recupera unidades pequeñas. Eso es correcto: primero se busca el fragmento preciso y después se debe ampliar contexto con el parent.

## 3. Problemas detectados

### Falta expansión runtime

Actualmente el sistema recupera child chunks y table documents, pero no resuelve:

```text
child.metadata.parent_id → parent chunk
```

Por eso el contexto final sigue siendo el texto pequeño recuperado, no el parent completo.

### No se deben expandir tablas inicialmente

Las tablas responden información concreta y sus documentos ya contienen contexto suficiente para el caso inicial. Además, resolver tablas hacia parents por `table_key` puede introducir ambigüedad.

Regla inicial:

```text
child_chunk → expandir a parent
table       → conservar como evidencia directa
```

### No hace falta truncar parents individualmente

Los parent chunks tienen un tamaño acotado por el proceso de chunking. Además, el cambio previsto hacia una API DeepSeek con ventana de 1M tokens reduce la presión de truncamiento.

Decisión inicial:

```text
expandir parent completo
deduplicar por parent_id
no cortar por tokens
```

Si después las pruebas muestran latencia, costo o ruido excesivo, se puede agregar una ventana alrededor del child recuperado. No implementarlo ahora.

### No crear un límite nuevo de parents expandidos

La expansión opera sobre los documentos finales que ya sobrevivieron el retrieval, RRF o reranking. Por eso no se agrega un hiperparámetro adicional como `MAX_EXPANDED_PARENTS`.

Regla inicial:

```text
expandir todos los child chunks finales
deduplicar por parent_id
mantener tablas directas
```

Si llegan 5 o 10 chunks finales, esos son los únicos candidatos a expansión. La expansión aumenta el contexto de cada evidencia seleccionada; no aumenta cuántas evidencias entran.

### Mantener orden de ranking original

Aunque fuentes externas como Liu et al. (*Lost in the Middle*) y el informe de Chroma sobre *context rot* advierten que los modelos pueden usar peor la información en el medio de contextos largos, esta primera implementación no reordena documentos por estrategia de inicio/final.

Decisión inicial:

```text
orden final de retrieval/reranking
        ↓
expansión
        ↓
mismo orden en build_context
```

El reordenamiento estratégico del contexto queda como mejora posterior, no como parte de este plan.

### Expansión incondicional

Todo `child_chunk` final con `parent_id` válido se expande a su parent. No se implementa auto-merging con umbral en esta fase.

Motivo:

- no requiere contar cuántos children tiene cada parent;
- no introduce umbrales que deban calibrarse;
- evita perder evidencia cuando un único child final es suficiente para justificar el parent.

Auto-merging con umbral queda como alternativa posterior si la evaluación muestra contexto diluido por matches únicos débiles.

### Verificar correspondencia `chunk_id` ↔ `parent_id` antes de integrar

La expansión depende de que `child.metadata.parent_id` apunte exactamente a `parent.chunk_id` en `parents.jsonl`.

Antes de escribir la integración del grafo, debe existir una prueba o verificación que confirme:

```text
para todo child_chunk indexable con parent_id:
    parent_id existe en parents.jsonl
```

Si esto falla masivamente, el fallback de “parent faltante, conservar child” ocultaría el problema y la técnica parecería funcionar sin expandir nada. Este es el guardrail más importante del plan.

## 4. Diseño propuesto

### Arquitectura objetivo

```text
agents/consulta_normativa/langchain_rag/retrieval
└── parent_document_retrieval.py
        ├── load_parent_documents
        ├── build_parent_lookup
        └── expand_parent_documents

agents/consulta_normativa/langchain_rag/graph.py
        retrieve
          ↓
        normalize_documents
          ↓
        reranking si aplica
          ↓
        expand_parent_documents
          ↓
        record_retrieval_trace
          ↓
        assess_evidence
          ↓
        build_context
```

### Flujo para retrieval individual

```text
query
  ↓
Chroma o BM25 retrieval
  ↓
normalize documents
  ↓
reranking si aplica
  ↓
expand child chunks to parents
  ↓
build context
```

### Flujo para Hybrid Retrieval

```text
query
  ↓
Chroma child/table top-k
BM25 child/table top-k
  ↓
normalize dense/sparse rankings
  ↓
RRF sobre child/table ids
  ↓
raw fused results
  ↓
normalize_documents del grafo
  ↓
reranking si aplica
  ↓
expand child chunks to parents
  ↓
build context
```

La expansión debe ocurrir **después de RRF y después de reranking cuando esos pasos existan**, no antes. Primero se decide qué child/table evidence importa; luego se busca el parent solo para los child chunks finales.

## 5. Componentes afectados

### Archivos nuevos

```text
agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py
agents/consulta_normativa/tests/test_parent_document_retrieval.py
```

Responsabilidades:

| Archivo | Responsabilidad |
|---|---|
| `agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py` | Cargar parents, construir lookup `parent_id -> parent`, expandir child chunks recuperados y preservar tablas como evidencia directa. |
| `agents/consulta_normativa/tests/test_parent_document_retrieval.py` | Validar correspondencia `parent_id`, expansión, deduplicación, orden, trazabilidad y fallback por parent faltante. |

### Archivos a modificar

```text
agents/consulta_normativa/langchain_rag/config.py
agents/consulta_normativa/langchain_rag/core/state.py
agents/consulta_normativa/langchain_rag/graph.py
agents/consulta_normativa/langchain_rag/main.py
agents/consulta_normativa/tests/test_langchain_rag_graph.py
agents/consulta_normativa/tests/test_langchain_rag_main.py
```

Responsabilidades:

| Archivo | Cambio |
|---|---|
| `config.py` | Exponer path default de `parents.jsonl` si todavía no está disponible desde config compartida. |
| `core/state.py` | Agregar trazabilidad mínima de expansión si el grafo necesita inspeccionarla. |
| `graph.py` | Insertar nodo común entre `normalize_documents` y `record_retrieval_trace` / `build_context`. |
| `main.py` | Cargar parent lookup al construir runtime y pasarlo al grafo o al nodo de expansión. |
| `test_langchain_rag_graph.py` | Probar que el grafo usa parent text después del retrieval. |
| `test_langchain_rag_main.py` | Probar wiring runtime de parent lookup. |

### Archivos que no deben modificarse

```text
pipeline/chunking/
pipeline/vectorization/
pipeline/sparse_indexing/
agents/shared/chroma_retrieval.py
agents/shared/bm25_retrieval.py
```

Motivo: la técnica ya tiene corpus e índices base. Esta fase solo agrega expansión runtime.

## 6. Plan de implementación

### 1. Definir configuración del path de parents

**Acción**
Reutilizar `DEFAULT_PARENT_CHUNKS_PATH` desde `pipeline.chunking.core.config` o exponerlo en la config runtime si el import directo no es conveniente.

**Ubicación**
`agents/consulta_normativa/langchain_rag/config.py`

**Motivo**
El runtime necesita ubicar `data/processed/chunks/parents.jsonl` sin hardcodear rutas.

**Dependencias**
Ninguna.

### 2. Crear loader runtime de parents

**Acción**
Crear en `agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py` una función:

```python
load_parent_documents(parents_path: Path) -> dict[str, RetrievedDocument]
```

Debe:

- fallar con error claro si el archivo no existe;
- leer JSONL;
- usar `chunk_id` como clave del lookup;
- conservar el texto completo del parent;
- conservar metadata normativa útil para referencias/contexto.

**Ubicación**
`agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py`

**Motivo**
Separar I/O de parents del grafo y de los retrievers.

**Dependencias**
Paso 1.

### 3. Verificar correspondencia real entre children y parents

**Acción**
Agregar una verificación en tests que cargue registros reales o fixtures representativos y confirme que todo `parent_id` de child chunk existe como `chunk_id` en el lookup de parents.

La verificación debe reportar al menos:

```text
total_child_chunks
children_with_parent_id
children_with_missing_parent
missing_parent_ratio
```

Para fixtures controlados, `children_with_missing_parent` debe ser `0`. Para datos reales, cualquier mismatch debe revisarse antes de continuar con la integración.

**Ubicación**
`agents/consulta_normativa/tests/test_parent_document_retrieval.py`

**Motivo**
Evitar un fallo silencioso donde todos los children se conserven sin expandir porque el lookup usa una clave diferente a la metadata.

**Dependencias**
Paso 2.

### 4. Definir contrato de expansión

**Acción**  
Crear una función pura:

```python
expand_parent_documents(
    documents: list[RetrievedDocument],
    parent_lookup: dict[str, RetrievedDocument],
) -> list[RetrievedDocument]
```

Reglas:

- si `metadata["document_type"] == "child_chunk"` y existe `parent_id`, devolver el parent;
- si el documento es tabla, conservarlo sin expandir;
- si falta el parent, conservar el documento original y marcar el fallback en metadata;
- deduplicar parents por `parent_id`;
- preservar el orden del ranking original.

**Ubicación**  
`agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py`

**Motivo**  
La expansión debe ser común para Chroma, BM25 e Hybrid Retrieval.

**Dependencias**  
Paso 3.

### 5. Preservar trazabilidad del match original

**Acción**  
Cuando un child se expanda a parent, agregar metadata de trazabilidad al documento expandido:

```text
expanded_from_child_id
expanded_from_document_type
expanded_parent_id
parent_expansion_applied
```

Si varios children del mismo parent aparecen, conservar una lista compacta:

```text
expanded_from_child_ids
```

**Ubicación**  
`agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py`

**Motivo**  
Evitar pérdida de evidencia fina: el contexto usa parent, pero la auditoría debe saber qué child disparó la recuperación.

**Dependencias**  
Paso 4.

### 6. Aplicar límite B por deduplicación, no por hiperparámetro

**Acción**
No crear `MAX_EXPANDED_PARENTS` en esta fase. Expandir todos los child chunks finales recibidos por la función y deduplicar por `parent_id`.

Si varios children apuntan al mismo parent:

```text
parent aparece una sola vez
expanded_from_child_ids conserva todos los children que lo activaron
posición final = primera aparición en el ranking
```

**Ubicación**
`agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py`

**Motivo**
Evitar repetición de contexto sin agregar un límite adicional. Los retrievers/rerankers ya controlan cuántos documentos finales llegan a expansión.

**Dependencias**
Paso 5.

### 7. No implementar truncamiento de parents

**Acción**  
No cortar texto del parent por tokens en esta fase.

Solo deduplicar parents y conservar el orden por ranking.

**Ubicación**  
`agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py`

**Motivo**  
Los parents tienen tamaño acotado y se planea usar una ventana de contexto amplia. Truncar puede cortar justo la sección importante.

**Dependencias**  
Paso 6.

### 8. Insertar nodo común en LangGraph

**Acción**  
Agregar un nodo después de `normalize_documents` y después de reranking si el flujo activo lo usa:

```text
normalize_documents → reranking si aplica → expand_parent_documents → record_retrieval_trace
```

El nodo recibe `state["documents"]`, aplica expansión y reemplaza `state["documents"]` por documentos expandidos.

**Ubicación**  
`agents/consulta_normativa/langchain_rag/graph.py`

**Motivo**  
Un solo punto de integración sirve para retrieval denso, BM25 o Hybrid, siempre que todos entreguen documentos normalizados.

**Dependencias**  
Pasos 2-7.

### 9. Cablear parent lookup en runtime

**Acción**  
En `agents/consulta_normativa/langchain_rag/main.py`, cargar parents durante `build_runtime` y pasarlos al builder del grafo.

El builder del grafo puede recibir un parámetro opcional:

```python
parent_lookup: dict[str, RetrievedDocument] | None = None
```

Si `parent_lookup` es `None`, el grafo conserva comportamiento actual sin expansión.

**Ubicación**  
`agents/consulta_normativa/langchain_rag/main.py` y `agents/consulta_normativa/langchain_rag/graph.py`

**Motivo**  
Mantener compatibilidad con tests y usos que construyen el grafo sin parent expansion.

**Dependencias**  
Paso 8.

### 10. Agregar trazabilidad al estado solo si es necesaria

**Acción**  
Si los tests o debugging lo requieren, agregar a `RagGraphState` un campo opcional:

```python
parent_expansion_trace: dict[str, Any]
```

Debe contener solo conteos y fallbacks:

```text
input_document_count
expanded_parent_count
preserved_table_count
missing_parent_count
deduplicated_parent_count
```

**Ubicación**  
`agents/consulta_normativa/langchain_rag/core/state.py`

**Motivo**  
Observabilidad mínima sin inflar el estado con documentos duplicados.

**Dependencias**  
Paso 9.

### 11. Probar expansión aislada

**Acción**  
Crear tests unitarios para `expand_parent_documents`.

Casos mínimos:

- child con `parent_id` válido se reemplaza por parent;
- tabla se conserva intacta;
- dos children del mismo parent producen un solo parent;
- varios children del mismo parent preservan `expanded_from_child_ids`;
- parent faltante conserva child y marca fallback;
- orden sigue el ranking original;
- metadata de trazabilidad se conserva.

**Ubicación**  
`agents/consulta_normativa/tests/test_parent_document_retrieval.py`

**Motivo**  
Validar la lógica central sin depender de Chroma, BM25 ni LLM.

**Dependencias**  
Pasos 2-7.

### 12. Probar integración en grafo

**Acción**  
Actualizar tests del grafo para verificar:

- retrieval devuelve child;
- `normalize_documents` produce documento pequeño;
- nodo de expansión cambia el contexto final al texto parent;
- fallback sin evidencia sigue funcionando;
- tablas no se expanden.
- la expansión ocurre después del ranking final disponible.

**Ubicación**  
`agents/consulta_normativa/tests/test_langchain_rag_graph.py`

**Motivo**  
Asegurar que Small-to-Big afecta el contexto final sin romper el flujo RAG.

**Dependencias**  
Pasos 8-10.

### 13. Probar wiring runtime

**Acción**  
Actualizar tests de `main.py` para verificar que `build_runtime` carga:

- colección Chroma / retriever activo;
- parent lookup desde `parents.jsonl`;
- grafo con parent expansion habilitada.

**Ubicación**  
`agents/consulta_normativa/tests/test_langchain_rag_main.py`

**Motivo**  
Evitar que la expansión exista como helper pero no quede conectada al runtime real.

**Dependencias**  
Paso 9.

## 7. Cambios de estado o contratos

### Nuevo contrato de expansión

```python
expand_parent_documents(
    documents: list[RetrievedDocument],
    parent_lookup: dict[str, RetrievedDocument],
) -> list[RetrievedDocument]
```

### Nuevo lookup runtime

```text
parent_id -> RetrievedDocument(parent)
```

### Metadata de trazabilidad

```text
parent_expansion_applied
expanded_parent_id
expanded_from_child_id
expanded_from_child_ids
expanded_from_document_type
parent_expansion_fallback
```

### Estado LangGraph

Campo opcional solo si se necesita observabilidad:

```python
parent_expansion_trace: dict[str, Any]
```

No cambiar el contrato de los retrievers Chroma, BM25 o Hybrid.

## 8. Testing

### Unit tests

```bash
python -m unittest agents.consulta_normativa.tests.test_parent_document_retrieval
```

Debe cubrir:

- expansión child → parent;
- tablas preservadas;
- deduplicación por parent;
- parent faltante;
- orden de ranking;
- metadata de trazabilidad.

### Graph integration tests

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_graph
```

Debe cubrir:

- contexto final usa texto parent;
- fallback sin documentos sigue intacto;
- tabla recuperada sigue siendo tabla;
- el grafo funciona sin parent lookup cuando se construye en modo baseline/test.

### Runtime wiring tests

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_main
```

Debe cubrir carga de `parents.jsonl` y paso del lookup al grafo.

### Regression tests

```bash
python -m unittest \
  agents.consulta_normativa.tests.test_bm25_retrieval \
  agents.consulta_normativa.tests.test_hybrid_retrieval \
  agents.consulta_normativa.tests.test_langchain_rag_formatting \
  agents.consulta_normativa.tests.test_rag_base
```

### Compile check

```bash
python -m compileall pipeline/chunking agents/shared agents/consulta_normativa
```

## 9. Riesgos

### Alto — Perder evidencia fina

Si el child recuperado se reemplaza por parent sin trazabilidad, no se sabrá qué fragmento activó la recuperación.

Mitigación: guardar metadata `expanded_from_child_id(s)` y `expanded_parent_id`.

### Medio — Duplicar contexto

Varios children del mismo parent pueden generar el mismo parent repetido.

Mitigación: deduplicar por `parent_id` manteniendo la primera posición de ranking.

### Medio — Inflar contexto

Los parents pueden ser más largos que los children. Por ahora no se truncarán porque el tamaño actual no representa un problema real y se prevé usar DeepSeek con ventana de 1M tokens.

Mitigación inicial: expandir solo documentos finales y deduplicar por `parent_id`. Si las pruebas muestran problemas, agregar después ventana alrededor del child recuperado.

### Medio — Lost in the middle / context rot

Una ventana de contexto grande no garantiza que el modelo use igual de bien toda la información. Liu et al. muestran caída de rendimiento cuando la evidencia queda en medio del contexto, y Chroma reporta degradación con contextos largos en modelos recientes.

Mitigación inicial: mantener ranking original y no aumentar el número de evidencias; medir antes de introducir reordenamiento estratégico.

### Bajo — Tablas sin expansión

Las tablas no se expanden inicialmente. Esto es una decisión consciente porque suelen representar evidencia concreta y resolverlas a parent puede meter ruido.

### Bajo — Acoplar expansión a un retriever específico

La expansión debe operar sobre `RetrievedDocument`, no sobre respuestas crudas de Chroma o BM25.

Mitigación: ubicarla después de `recovered_documents()`.

## 10. Criterios de aceptación

- Existe `agents/consulta_normativa/langchain_rag/retrieval/parent_document_retrieval.py`.
- El runtime puede cargar `parents.jsonl` como lookup `parent_id -> parent`.
- Los child chunks recuperados se expanden a su parent completo.
- Las tablas recuperadas se conservan sin expansión.
- Varios children del mismo parent producen un solo parent en contexto.
- Varios children del mismo parent agregan trazabilidad en `expanded_from_child_ids`.
- El orden del contexto respeta el ranking original.
- La metadata conserva qué child originó cada parent expandido.
- No se implementa truncamiento de parents en esta fase.
- No se crea un hiperparámetro nuevo para limitar parents; se expanden los documentos finales y se deduplican parents repetidos.
- La expansión ocurre después de retrieval, RRF y reranking según el flujo activo.
- No se modifican los índices ni el chunking.
- Tests unitarios, integración de grafo y wiring runtime pasan.

## Fuentes internas

- `pipeline/chunking/core/config.py` — path de `parents.jsonl`.
- `pipeline/chunking/hierarchical_splitter/` — generación de parent/child chunks.
- `pipeline/vectorization/documents.py` — metadata `parent_id` en child chunks indexados.
- `agents/consulta_normativa/langchain_rag/formatting.py` — normalización a `RetrievedDocument` y construcción de contexto.
- `agents/consulta_normativa/langchain_rag/graph.py` — punto de integración post-retrieval.
- Liu et al., “Lost in the Middle: How Language Models Use Long Contexts” — riesgo de degradación posicional en contextos largos.
- Chroma, “Context Rot: How Increasing Input Tokens Impacts LLM Performance” — riesgo de degradación por longitud de contexto incluso en modelos recientes.
- LangChain Parent/MultiVector Retriever docs — patrón de recuperar chunks pequeños y devolver documentos padres.
