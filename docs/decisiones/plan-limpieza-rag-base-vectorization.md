# Plan de implementación: limpieza del RAG base y vectorización

Este plan define una limpieza controlada de los dos pipelines del RAG base: `pipeline/vectorization` y `agents/consulta_normativa`. El objetivo es reducir código muerto, mejorar claridad, normalizar errores y fijar explícitamente el modelo de embeddings usado por ChromaDB.

## Decisiones confirmadas

| Área | Decisión |
|---|---|
| Organización del código | Mantener código organizado por bloques/secciones claras. |
| Docstrings | Actualizar docstrings para explicar qué hace cada función de forma concreta. |
| Comentarios | Conservar comentarios útiles; eliminar comentarios accidentales o que no expliquen intención. |
| Código muerto | Eliminar funciones sin uso real. |
| Errores de conversión | Normalizar errores esperados de conversión a `ValueError`. |
| Embeddings de Chroma | Usar explícitamente `Qwen/Qwen3-Embedding-0.6B`, el mismo modelo base usado en chunking semántico. |
| Idioma del agente | El prompt interno puede mantenerse en inglés, pero la interacción y salida del agente deben ser en español. |

## Fuera de alcance

- Agregar reranking, recuperación híbrida o expansión a parent chunks.
- Agregar memoria conversacional.
- Agregar control de tamaño de contexto.
- Crear API REST o frontend.
- Cambiar el esquema de metadata vectorial salvo que sea necesario para limpieza.
- Agregar pruebas donde este plan indique explícitamente que no se requieren.

## Fase 1 — Limpieza de `pipeline/vectorization/documents.py`

### Objetivo

Dejar solo la API realmente usada para normalizar child chunks y documentos de tablas hacia registros compatibles con ChromaDB.

### Cambios

- Eliminar funciones sin uso real:
  - `load_vector_records`
  - `load_child_chunk_records`
  - `load_table_document_records`
- Mantener los loaders batch porque preservan conteos de registros omitidos:
  - `load_vector_record_batch`
  - `load_child_chunk_record_batch`
  - `load_table_document_record_batch`
- Conservar comentarios útiles de sección.
- Eliminar comentarios que no explican intención, por ejemplo:
  - `# Super Important`
  - `# Important`
  - `# Impotant`
- Actualizar docstrings para que expliquen la responsabilidad real de cada función.
- Normalizar errores esperados de conversión a `ValueError`, especialmente:
  - `table_index` inválido;
  - metadata de tabla mal formada;
  - campos requeridos vacíos.

### Resultado esperado

`documents.py` queda como módulo compacto con tres responsabilidades claras:

```txt
lectura batch
normalización a ChromaRecord
validación/metadata helpers
```

## Fase 2 — Ajustes de `pipeline/vectorization/ingest.py`

### Objetivo

Hacer que la ingesta falle de forma clara cuando falten artefactos fuente y eliminar retornos que no aportan.

### Cambios

- Si los JSONL de entrada no existen, emitir error controlado antes de abrir ChromaDB.
- Revisar el retorno de `upsert_records(...)` en el flujo de ingesta:
  - si el conteo no aporta al resultado final, no depender de él;
  - no agregar lógica extra solo para conservarlo.

### Resultado esperado

La ingesta no debe crear una colección vacía cuando los artefactos JSONL esperados no existen.

## Fase 3 — Separación de apertura Chroma y embeddings explícitos

### Objetivo

Separar el modo ingesta del modo consulta y hacer reproducible la función de embeddings usada por ChromaDB.

### Cambios

- En `pipeline/vectorization/chroma_store.py`, separar:
  - `open_or_create_collection(...)` para ingesta;
  - `open_existing_collection(...)` para consulta.
- Mantener `get_or_create_collection(...)` solo donde se indexa.
- Usar `get_collection(...)` o validación equivalente para consulta, evitando crear colecciones vacías accidentalmente.
- Usar explícitamente `Qwen/Qwen3-Embedding-0.6B` como embedding model por defecto.
- Reutilizar la constante existente del chunking si es razonable:

```python
DEFAULT_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
```

- Implementar el embedding function de forma simple y localizada. No crear framework de proveedores.
- Mantener import lazy de dependencias opcionales para no romper tests que no usan Chroma.
- No priorizar validación de `top_k` en esta fase.
- Agregar test para `upsert_records(...)`.

### Resultado esperado

ChromaDB queda más reproducible y el CLI de consulta ya no puede crear silenciosamente una colección vacía.

## Fase 4 — Limpieza de `pipeline/vectorization/main.py`

### Objetivo

Simplificar la CLI de ingesta sin cambiar comportamiento externo relevante.

### Cambios

- Eliminar el `raise ValueError("Unsupported command...")` si queda inalcanzable por `argparse`.
- Mantener mensajes de ingesta claros.
- Asegurar que errores controlados sigan retornando código `2`.

### Resultado esperado

La CLI queda más directa y sin ramas defensivas innecesarias.

## Fase 5 — Limpieza de `agents/consulta_normativa/rag_base.py`

### Objetivo

Eliminar datos no usados y asegurar que la salida del agente sea en español.

### Cambios

- Eliminar campos o estructuras sin uso real, por ejemplo `RecoveredDocument.distance` si no participa en formato, decisión o depuración.
- Mantener fuera de alcance el control de tamaño de contexto.
- Ajustar fallback y referencias para que la salida visible al usuario sea en español.
- Mantener el flujo base sin nuevas capas.

### Resultado esperado

El flujo RAG sigue siendo pequeño y evaluable, pero sin campos muertos ni salida mixta innecesaria.

## Fase 6 — Ajustes de `agents/consulta_normativa/prompts.py`

### Objetivo

Mantener el prompt base eficiente, pero asegurar que instruya salida en español.

### Cambios

- Mantener el prompt en inglés para ahorrar tokens.
- Agregar instrucción explícita de responder en español.
- Limpiar indentación del prompt si mejora claridad sin cambiar intención.

### Resultado esperado

El prompt sigue siendo compacto, pero el comportamiento esperado del agente queda alineado con usuarios hispanohablantes.

## Fase 7 — Revisión final

### Objetivo

Confirmar que la limpieza no cambió el alcance del RAG base.

### Verificación mínima

```bash
python -m unittest pipeline.tests.test_vectorization_documents pipeline.tests.test_consulta_normativa_rag_base pipeline.tests.test_consulta_normativa_cli
python -m compileall pipeline/vectorization agents/consulta_normativa
```

Si se agregan tests de `upsert_records(...)`, incluirlos en el primer comando.

### Checklist

- [ ] No quedan wrappers `*_records` sin uso en `documents.py`.
- [ ] Los errores de conversión esperados se normalizan a `ValueError`.
- [ ] La ingesta alerta si faltan JSONL de entrada.
- [ ] Chroma separa apertura de ingesta y apertura de consulta.
- [ ] Chroma usa explícitamente `Qwen/Qwen3-Embedding-0.6B`.
- [ ] `upsert_records(...)` tiene test enfocado.
- [ ] La CLI de vectorización no conserva ramas inalcanzables innecesarias.
- [ ] `rag_base.py` no conserva campos muertos.
- [ ] La salida del agente queda en español.
- [ ] El prompt puede seguir en inglés, pero exige respuesta en español.

## Orden recomendado de implementación

1. `documents.py`
2. `chroma_store.py`
3. `ingest.py`
4. `pipeline/vectorization/main.py`
5. `agents/consulta_normativa/rag_base.py`
6. `agents/consulta_normativa/prompts.py`
7. verificación y revisión fresca

Este orden reduce riesgo porque primero limpia la normalización de documentos, luego estabiliza Chroma, y solo después ajusta la capa del agente.
