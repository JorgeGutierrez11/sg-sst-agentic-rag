# Plan de implementación: RAG base de consulta normativa

Este plan define la primera versión funcional del agente de consulta normativa SG-SST. Su objetivo es construir una línea base simple y evaluable: recibir una pregunta, recuperar evidencia desde ChromaDB y generar una respuesta fundamentada en los documentos recuperados.

Referencia base de ChromaDB:

```txt
https://docs.trychroma.com/docs/overview/introduction
```

## Objetivo de la etapa

Implementar un RAG base que use los artefactos derivados del chunking actual como corpus de recuperación.

El sistema debe:

- indexar `child chunks` normativos;
- indexar documentos de tablas ya convertidos a texto o Markdown;
- recuperar los documentos más relevantes para una pregunta;
- construir una respuesta usando únicamente el contexto recuperado;
- incluir referencias básicas a la fuente normativa.

## Alcance

### Incluido

- Ingesta de JSONL de `child chunks`.
- Ingesta de JSONL de documentos de tablas vector-ready.
- Creación de una colección persistente en ChromaDB.
- Normalización de documentos y metadata para ChromaDB.
- Consulta semántica top-k sobre la colección.
- Prompt base para responder con evidencia recuperada.
- Respuesta con citas básicas desde metadata.

### Fuera de alcance

- Expansión jerárquica hacia parent chunks.
- Reescritura o clasificación de consultas.
- Memoria conversacional.
- Contexto empresarial.
- Validación avanzada de respuestas.
- Reranking o recuperación híbrida.
- Optimización de técnicas candidatas.

## Entradas

| Entrada | Uso |
|---|---|
| `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` | Corpus principal de chunks normativos. |
| JSONL de documentos de tablas vector-ready | Corpus de tablas indexables. |

Los parent chunks se conservan como artefacto de trazabilidad del pipeline, pero no se usan como contexto expandido en esta etapa.

## Arquitectura propuesta

```txt
pipeline/vectorization/
  __init__.py
  documents.py
  chroma_store.py
  ingest.py
  main.py

agents/consulta_normativa/
  __init__.py
  rag_base.py
  prompts.py
```

## Colección ChromaDB

Nombre inicial:

```txt
sg_sst_base_rag
```

La colección contiene dos tipos de documentos:

```txt
child_chunk
table
```

ChromaDB se usará en modo persistente local para esta etapa. La colección debe guardar:

- `ids`: identificadores estables de cada documento;
- `documents`: texto que se vectoriza;
- `metadatas`: campos planos para trazabilidad y filtros.

La búsqueda base será por similitud vectorial densa. Los filtros por metadata quedan disponibles para consultas acotadas por fuente, tipo de documento o artículo.

## Modelo de documento para indexación

Cada registro enviado a ChromaDB debe tener:

```json
{
  "id": "stable-document-id",
  "document": "texto a vectorizar",
  "metadata": {
    "document_type": "child_chunk"
  }
}
```

La metadata debe mantenerse plana para facilitar filtros y consultas. No se deben guardar objetos anidados como listas de tablas o jerarquías completas dentro de ChromaDB; esos datos deben convertirse a campos simples cuando sean necesarios.

### Metadata mínima para child chunks

```json
{
  "document_type": "child_chunk",
  "source_document_id": "...",
  "source_stem": "...",
  "parent_id": "...",
  "article": "...",
  "start_char": 0,
  "end_char": 0,
  "has_tables": false,
  "table_keys": ""
}
```

### Metadata mínima para tablas

```json
{
  "document_type": "table",
  "source_stem": "...",
  "table_index": 0,
  "table_key": "source_stem:0",
  "linked_placeholder": "<!-- TABLE_0 -->"
}
```

`table_key` permite relacionar una tabla con un chunk que tenga el mismo valor en `table_keys`, sin guardar rutas físicas dentro de la colección.

## Flujo de ingesta

1. Leer JSONL de child chunks.
2. Leer JSONL de documentos de tablas.
3. Convertir ambos a registros compatibles con ChromaDB.
4. Crear o abrir la colección persistente.
5. Insertar `ids`, `documents` y `metadatas`.
6. Reportar cantidad de documentos indexados por tipo.
7. Evitar insertar registros sin texto útil.

## Flujo de consulta

1. Recibir pregunta del usuario.
2. Consultar ChromaDB con `query_texts` y `n_results` configurado.
3. Recuperar documentos relevantes de tipo `child_chunk` y `table`.
4. Construir un contexto textual con los resultados recuperados.
5. Generar respuesta usando solo ese contexto.
6. Mostrar referencias básicas con documento fuente, artículo cuando exista y tipo de documento.

La consulta base no aplica recuperación híbrida, reranking ni expansión de contexto. Solo usa la recuperación vectorial inicial de ChromaDB para mantener una línea base clara.

## Criterios de aceptación

- [ ] La colección ChromaDB se crea de forma persistente.
- [ ] Los child chunks se indexan con ids estables y metadata útil.
- [ ] Las tablas vector-ready se indexan como documentos independientes.
- [ ] La metadata indexada en ChromaDB es plana y filtrable.
- [ ] Una consulta retorna resultados desde ChromaDB.
- [ ] El agente genera una respuesta basada solo en los documentos recuperados.
- [ ] La respuesta incluye referencias básicas a las fuentes usadas.
- [ ] El proceso de ingesta reporta conteos de documentos indexados.
- [ ] La implementación evita indexar registros vacíos o sin texto útil.

## Resultado esperado

Al finalizar esta etapa debe existir un agente RAG base funcional y evaluable, con una arquitectura mínima que permita medir el desempeño inicial antes de introducir mejoras posteriores.
