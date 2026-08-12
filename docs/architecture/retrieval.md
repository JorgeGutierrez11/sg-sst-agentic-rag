# Arquitectura de recuperación y RAG base

El RAG base de consulta normativa abre una colección ChromaDB ya indexada, recupera los documentos más similares a cada pregunta y construye una respuesta en español fundamentada únicamente en el contexto recuperado. Es una línea base interactiva y medible; todavía no implementa mejoras como multi-query, reranking, recuperación híbrida o contexto empresarial.

## Ruta rápida

Primero debe existir la colección vectorial:

```bash
python -m pipeline.vectorization.main --batch-size 8
```

Luego configura Groq y abre la CLI interactiva:

```bash
export GROQ_API_KEY="tu_api_key"
python -m agents.consulta_normativa.main
```

## Contrato de ejecución

| Aspecto | Comportamiento actual |
|---|---|
| Entrada de usuario | Prompt interactivo `Pregunta>`. Preguntas vacías se ignoran. |
| Salida | Imprime `Contexto recuperado:`, un separador y luego `Respuesta:`. No imprime una sección independiente de `Referencias:` en la CLI actual. |
| Salida de sesión | `exit` o `quit`, sin distinguir mayúsculas/minúsculas. |
| Variable requerida | `GROQ_API_KEY` en el entorno. No se lee desde archivos del proyecto. |
| Modelo Groq | `openai/gpt-oss-120b`. |
| Temperatura | `0`. |
| Top-k por defecto | `5`. |
| Código de error operacional | `2`, con mensaje controlado y sin traceback. |

## Apertura de Chroma para consulta

La consulta usa `open_existing_collection(...)`, no `open_or_create_collection(...)`.

Esta diferencia es deliberada:

| Función | Uso correcto | Motivo |
|---|---|---|
| `open_or_create_collection(...)` | Ingesta vectorial | Puede crear la ruta persistente y la colección. |
| `open_existing_collection(...)` | Consulta RAG | Debe fallar si la colección no existe para no crear un índice vacío accidentalmente. |

Si `data/processed/chroma` no existe o la colección `sg_sst_base_rag` no está disponible, la CLI falla durante la etapa `Chroma collection opening` con un error controlado. La acción correcta es ejecutar primero la vectorización.

## Recuperación top-k y contexto

`agents/consulta_normativa/rag_base.py` encapsula la recuperación con `chroma_retriever(collection)`. Internamente llama a `query_top_k(...)` en `agents/shared/chroma_retrieval.py` con esta forma:

```python
collection.query(
    query_texts=[question],
    n_results=top_k,
    include=["documents", "metadatas", "distances"],
)
```

El resultado de Chroma se normaliza a una lista de documentos recuperados. Para cada documento se conserva:

- texto recuperado;
- metadata plana;
- referencia compacta construida desde `source_stem` o `source_document_id`, jerarquía normativa cuando exista y tipo normativo real (`normative_document_type`) para child chunks;
- bloque de metadata estructurada generado por `metadata_context(...)`.

El contexto entregado al prompt usa índices visibles:

```text
[1] Decreto 1072 de 2015, artículo 2.2.4.6.1 (decreto)
Información general:
- Tipo de registro: child_chunk
- Fuente: Decreto 1072 de 2015
- Tipo normativo: decreto

Jerarquía normativa:
- Artículo: 2.2.4.6.1

Trazabilidad técnica:
- ID padre: parent-...
- Inicio: 237
- Fin: 903

Contenido:
<texto recuperado>

[2] Resolución 0312 de 2019, tabla 1, parte 1 de 3 (table)
Información general:
- Tipo de registro: table
- Fuente: Resolución 0312 de 2019

Tabla:
- Índice: 0
- Parte: 1 de 3
- Clave lógica: Resolución 0312 de 2019:0

Contenido:
<texto de tabla recuperado>
```

El contexto no imprime metadata cruda como JSON. Agrupa solo campos presentes en secciones legibles: `Información general`, `Jerarquía normativa`, `Tablas`, `Tabla` y `Trazabilidad técnica`. Los campos vacíos se omiten y los booleanos se expresan como `sí`/`no`.

`RagAnswer` conserva `references` como lista deduplicada en orden de aparición. Esa lista sirve para auditoría interna y para la respuesta determinística sin LLM; la CLI interactiva actual no la imprime como sección separada porque el contexto recuperado ya contiene la referencia compacta y la metadata estructurada de cada fragmento.

## Prompt y respuesta esperada

`agents/consulta_normativa/prompts.py` construye un prompt con reglas estrictas de grounding:

- responder únicamente con información literal del contexto recuperado;
- citar cada afirmación con el índice de fragmento `[n]`;
- declarar cuando el contexto solo responde parcialmente;
- señalar contradicciones si aparecen;
- responder en español;
- cerrar con una lista de fragmentos citados y referencia normativa completa cuando el contexto lo permita.

Esa última regla aplica al texto generado por el LLM dentro de `Respuesta:`. Es distinta de la lista `references` retornada por `RagAnswer` y de la renderización de la CLI.

El generador por defecto vive en `agents/consulta_normativa/main.py` mediante `build_default_generator()`. No hay un módulo `generator.py` separado en el estado actual; la construcción de `ChatGroq` está localizada en la CLI para mantener la línea base simple.

Si no se recuperan documentos, `answer_question(...)` no llama al LLM aunque exista generador. Devuelve la respuesta determinística:

```text
La evidencia recuperada es insuficiente para responder la pregunta.
```

Este comportamiento evita que el modelo complete vacíos con conocimiento externo.

## Manejo de errores operacionales

La CLI convierte fallos de dependencias, configuración, colección y ejecución por pregunta en mensajes controlados. Los errores principales son:

| Etapa | Ejemplos |
|---|---|
| `dependency loading` | Falta una dependencia runtime importada de forma perezosa. |
| `generator setup` | `GROQ_API_KEY` ausente, `langchain_groq` no instalado o fallo al construir `ChatGroq`. |
| `Chroma collection opening` | No existe el path persistente o la colección no está indexada. |
| `RAG execution` | Falla una consulta o generación de una pregunta específica. |

Durante la sesión interactiva, un fallo en una pregunta no cierra automáticamente la CLI; se reporta el error y el usuario puede intentar otra pregunta.

## Límites conocidos y próximos experimentos

Este RAG base existe para tener una línea de comparación clara antes de agregar técnicas más complejas. Actualmente no implementa:

- multi-query o reformulación automática de preguntas;
- expansión hacia parent chunks;
- reranking;
- recuperación híbrida lexical + vectorial;
- filtros por tipo de norma, año, artículo o `document_type`;
- memoria conversacional;
- contexto empresarial de la MiPyme;
- validación avanzada posterior a la generación;
- API REST o frontend.

Los experimentos futuros de recuperación, como multi-query, deben compararse contra esta línea base con métricas ARES sobre el conjunto de desarrollo definido por la metodología. No deberían reemplazar el flujo base sin evidencia de mejora en relevancia de contexto, fidelidad y relevancia de respuesta.
