# Análisis de calidad: RAG base de consulta normativa

Este documento analiza la implementación actual del RAG base de consulta normativa SG-SST y su pipeline de vectorización. El objetivo es identificar problemas reales, código simplificable y candidatos de limpieza antes de seguir construyendo nuevas capas sobre esta base.

## Resumen ejecutivo

La implementación actual es funcional como primera línea base: puede normalizar artefactos JSONL, indexarlos en ChromaDB y ejecutar una consulta desde terminal usando el flujo `answer_question`. Sin embargo, todavía hay deuda pequeña pero importante en limpieza, manejo de errores y separación entre modo ingesta y modo consulta.

Prioridad inmediata:

1. eliminar wrappers no usados en `pipeline/vectorization/documents.py`;
2. limpiar comentarios accidentales o poco informativos;
3. mover el import de `ChatGroq` dentro del generador para que el fallo por dependencia sea realmente controlado;
4. endurecer validación de metadata inválida en tablas;
5. agregar pruebas faltantes de ingesta y Chroma boundary.

## Flujo actual

### Ingesta vectorial

```txt
data/processed/chunks/regex_constrained_semantic/chunks.jsonl
data/processed/table_documents.jsonl
  → pipeline.vectorization.main ingest
  → ingest_base_rag_documents(...)
  → load_vector_record_batch(...)
  → open_collection(...)
  → upsert_records(...)
  → data/processed/chroma
```

### Consulta CLI

```txt
python -m agents.consulta_normativa.main
  → open_collection(DEFAULT_CHROMA_PATH, DEFAULT_COLLECTION_NAME)
  → chroma_retriever(collection)
  → prompt interactivo
  → answer_question(question, retriever, generator, top_k=5)
  → query_top_k(...)
  → recovered_documents(...)
  → build_context(...)
  → build_base_prompt(...)
  → generator(prompt) si hay evidencia
  → print_answer(...)
```

## Hallazgos por archivo

### `pipeline/vectorization/documents.py`

| Problema | Impacto | Acción recomendada |
|---|---|---|
| `load_vector_records`, `load_child_chunk_records` y `load_table_document_records` no se usan. | Duplican API y pierden conteos de omitidos. | Eliminarlos cuando se haga limpieza. |
| Comentarios como `# Super Important`, `# Important`, `# Impotant`. | No explican intención y reducen profesionalismo del código. | Reemplazar por secciones útiles o eliminarlos. |
| Comentarios inline mixtos en español en metadata. | Inconsistencia con docstrings/artefactos técnicos en inglés. | Convertir a docstring/sección clara o eliminar si es obvio. |
| `valid_chroma_records(...)` solo captura `ValueError`. | Algunos valores inválidos pueden tumbar la ingesta. | Normalizar errores de conversión a `ValueError` o capturar errores esperados. |
| `table_document_to_chroma(...)` convierte `table_index` con `int(...)` sin validación explícita. | Metadata corrupta puede producir errores poco claros. | Agregar helper pequeño para `required_int`. |
| La omisión de registros inválidos no reporta razones. | La CLI muestra conteos, pero no permite diagnosticar qué falló. | Mantener simple por ahora; considerar reporte de razones solo si se vuelve necesario. |

### Confirmación sobre funciones `*_records`

| Función | Uso encontrado | Estado | Recomendación |
|---|---:|---|---|
| `load_vector_records` | Solo definición. | No usada. | Candidata a eliminación. |
| `load_child_chunk_records` | Solo definición. | No usada. | Candidata a eliminación. |
| `load_table_document_records` | Solo definición. | No usada. | Candidata a eliminación. |
| `valid_chroma_records` | Usada por loaders batch. | Sí usada. | Mantener y endurecer manejo de errores. |

Conclusión: tu sospecha es correcta. Los wrappers que terminan en `_records` y devuelven solo `list[ChromaRecord]` son peores que los `*_record_batch`, porque descartan los conteos de registros omitidos.

### `pipeline/vectorization/ingest.py`

| Problema | Impacto | Acción recomendada |
|---|---|---|
| `upsert_records(...)` devuelve conteo pero `ingest_base_rag_documents(...)` lo ignora. | Pequeña inconsistencia en trazabilidad de ingesta. | Usar el conteo o eliminar el retorno si no aporta. |
| Si los JSONL no existen, `read_jsonl(...)` devuelve `[]`. | La ingesta puede terminar con 0 documentos sin alertar claramente que faltan artefactos. | Fallar si ambos corpus están vacíos o si las rutas de entrada no existen. |
| Falta prueba directa de `ingest_base_rag_documents(...)`. | Riesgo de romper integración con Chroma boundary sin que tests lo detecten. | Agregar prueba con colección falsa. |

### `pipeline/vectorization/chroma_store.py`

| Problema | Impacto | Acción recomendada |
|---|---|---|
| `open_collection(...)` usa `get_or_create_collection(...)` para todo. | En consulta puede crear una colección vacía y ocultar que no se indexó nada. | Separar `open_or_create_collection` para ingesta y `open_existing_collection` para consulta, o validar vacío en CLI. |
| `query_top_k(...)` no valida `top_k`. | Valores inválidos podrían llegar hasta Chroma con errores menos claros. | Validar `top_k > 0`. |
| Falta prueba directa de `upsert_records(...)`. | No se verifica forma exacta enviada a Chroma. | Agregar test con colección fake. |
| No se fija embedding function explícita. | Reproducibilidad depende del default de Chroma. | Documentar o configurar cuando se defina estrategia final de embeddings. |

### `pipeline/vectorization/main.py`

| Problema | Impacto | Acción recomendada |
|---|---|---|
| No hay tests directos de CLI `ingest`. | Puede romperse parser/salida sin alerta. | Agregar tests enfocados de `main(["ingest", ...])`. |
| Captura `ImportError` y `ValueError`, pero no errores de metadata inválida que podrían ser `TypeError`. | Algunos errores saldrían con traceback. | Normalizar validaciones aguas abajo a `ValueError`. |
| `raise ValueError("Unsupported command...")` es casi inalcanzable por `argparse`. | Ruido menor. | Mantener o eliminar si se limpia CLI. |

### `agents/consulta_normativa/main.py`

| Problema | Impacto | Acción recomendada |
|---|---|---|
| `from langchain_groq import ChatGroq` está en top-level. | Si falta `langchain_groq`, importar el módulo falla antes de mostrar error controlado. | Mover el import dentro de `build_default_generator()`. |
| `build_lazy_default_generator()` existe para inicializar Groq solo si se necesita, pero el import top-level rompe parcialmente esa intención. | El caso sin evidencia o tests sin Groq siguen expuestos al import temprano. | Corregir junto con el punto anterior. |
| Comentario `# Se usa para errores operativos en el CLI - Como funciona???`. | Ruido y señal de duda dentro de código productivo. | Eliminar o reemplazar por comentario claro si realmente aporta. |
| `RagDependencies` usa `Callable[..., Any]`. | Flexible para tests, pero contrato borroso. | Aceptable por ahora; no expandir. |
| `except Exception` en `ask(...)` usa mensaje genérico. | Evita fugas, pero dificulta depuración. | Mantener para CLI; si hace falta, agregar logging controlado más adelante. |

### `agents/consulta_normativa/rag_base.py`

| Problema | Impacto | Acción recomendada |
|---|---|---|
| `RecoveredDocument.distance` se conserva pero no se usa. | Campo muerto por ahora. | Eliminar hasta que se muestre o se use para ranking/debug. |
| No hay control de tamaño del contexto. | Con tablas largas, el prompt puede crecer demasiado. | Agregar límite simple de caracteres/tokens cuando aparezca el primer caso real. |
| `answer_question(...)` concentra recuperación, contexto, prompt y generación. | Crecerá rápido en etapas futuras. | Mantener por ahora; dividir solo cuando se implemente la siguiente etapa. |
| Referencias usan formato inglés: `article`. | Salida puede sentirse inconsistente para usuario hispanohablante. | Decidir idioma de salida del agente. |

### `agents/consulta_normativa/prompts.py`

| Problema | Impacto | Acción recomendada |
|---|---|---|
| Prompt base en inglés. | Puede condicionar respuestas en inglés aunque el dominio sea español. | Definir si la respuesta debe seguir el idioma de la pregunta o ser siempre español. |
| Indentación del f-string puede meter espacios innecesarios. | Prompt menos limpio, aunque funcional. | Usar `textwrap.dedent(...).strip()`. |

## Backlog de simplificación

### Alta prioridad

- [ ] Eliminar `load_vector_records`, `load_child_chunk_records` y `load_table_document_records`.
- [ ] Limpiar comentarios basura o accidentales en `documents.py` y `agents/consulta_normativa/main.py`.
- [ ] Mover `ChatGroq` a import lazy dentro de `build_default_generator()`.
- [ ] Agregar validación explícita de `table_index` y otros enteros requeridos.
- [ ] Añadir tests para metadata inválida en documentos de tabla.

### Media prioridad

- [ ] Separar apertura Chroma para ingesta y consulta, o validar explícitamente colección vacía en el CLI interactivo.
- [ ] Agregar tests de `ingest_base_rag_documents(...)` con colección fake.
- [ ] Agregar tests de `upsert_records(...)`.
- [ ] Agregar tests del CLI `pipeline.vectorization.main ingest`.
- [ ] Decidir idioma de prompt, fallback y referencias.

### Baja prioridad

- [ ] Evaluar si `RecoveredDocument.distance` debe eliminarse hasta que exista uso real.
- [ ] Simplificar `SourceReference` si empieza a sentirse más pesado que útil.
- [ ] Limpiar indentación de `build_base_prompt(...)` con `textwrap.dedent`.
- [ ] Renombrar `load_vector_record_batch` a un nombre más explícito si se elimina el wrapper viejo.

## Criterio para futuras limpiezas

Antes de agregar nuevas capacidades al agente de consulta normativa, conviene limpiar primero los puntos de alta prioridad. Si no, la siguiente etapa va a construirse encima de una base con APIs duplicadas, imports opcionales mal ubicados y validaciones incompletas.

Regla KISS/YAGNI para esta etapa:

```txt
mantener batch loaders con conteos
eliminar wrappers que pierden información
validar lo mínimo que puede romper ingesta
no agregar nuevas capas hasta que haya comportamiento nuevo real
```
