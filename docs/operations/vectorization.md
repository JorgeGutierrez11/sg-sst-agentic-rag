# Guía operativa: vectorización en ChromaDB


## Ruta rápida

```bash
python -m pipeline.vectorization.main --batch-size 8
```

## Prerrequisitos

| Requisito | Detalle |
|---|---|
| Child chunks recomendados | `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` debe existir. |
| Documentos de tabla | `data/processed/table_documents.jsonl` debe existir. Para regenerarlo, consulta [`table-processing.md`](table-processing.md). |
| Dependencias Python | `requirements.txt` incluye las dependencias de embeddings y Chroma usadas por la ingesta. |
| Modelo de embeddings | El entorno debe poder cargar `Qwen/Qwen3-Embedding-0.6B`. |

## Entradas y salida

| Entrada | Salida |
|---|---|
| `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` | `data/processed/chroma` |
| `data/processed/table_documents.jsonl` | Colección `sg_sst_base_rag` |

La ingesta indexa child chunks y documentos de tabla. No ejecuta generación, no requiere Groq y no abre una CLI de consulta.

## Vectorizar

```bash
python -m pipeline.vectorization.main --batch-size 8
```

La ingesta usa `open_or_create_collection(...)` y `upsert`. Esto permite crear o actualizar la colección, pero no elimina registros obsoletos que ya no existan en los JSONL fuente.

## Reconstrucción limpia

Si cambiaste chunks, documentos de tabla o embeddings y necesitas evitar registros obsoletos, elimina o mueve el índice antes de vectorizar.

Antes de reconstruir, confirma que existen los chunks actuales y `data/processed/table_documents.jsonl` actualizado. Si los documentos de tabla no están vigentes, regenéralos con [`table-processing.md`](table-processing.md).

```bash
rm -rf data/processed/chroma
python -m pipeline.vectorization.main --batch-size 8
```

Si necesitas conservar el índice anterior para comparación, muévelo en lugar de borrarlo.

```bash
mv data/processed/chroma data/processed/chroma.backup
python -m pipeline.vectorization.main --batch-size 8
```

## Contratos importantes

| Área | Contrato operativo |
|---|---|
| Entrada principal | `regex_constrained_semantic/chunks.jsonl`, no `semantic_chunking/chunks.jsonl`. |
| Tablas | Se indexan como documentos independientes desde `table_documents.jsonl`. |
| Metadatos | Chroma recibe metadata plana y lógica; no rutas físicas de tablas. |
| Modelo de embeddings | `Qwen/Qwen3-Embedding-0.6B`. |
| Colección | `sg_sst_base_rag`. |
| Persistencia | `data/processed/chroma`. |
| Política de escritura | `upsert`: inserta o actualiza, pero no elimina documentos obsoletos. |

## Siguiente paso: consulta RAG

Después de vectorizar, usa el runbook correspondiente a la implementación que vas a operar:

- Implementación actual LangChain/LangGraph: [`rag-langgraph.md`](rag-langgraph.md).
- Línea base manual congelada: [`rag-manual.md`](rag-manual.md).

Este runbook solo cubre vectorización; los pasos de ejecución RAG viven en las guías anteriores para no mezclar responsabilidades.
