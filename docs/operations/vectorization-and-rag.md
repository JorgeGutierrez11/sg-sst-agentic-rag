# Guía operativa: vectorización y consulta RAG base

Esta guía indexa los child chunks recomendados y los documentos de tabla ya generados en ChromaDB, y luego abre la consulta normativa interactiva. La consulta requiere una colección existente; no debe crear un índice vacío durante la atención de preguntas.

## Ruta rápida

```bash
python -m pipeline.vectorization.main --batch-size 8
export GROQ_API_KEY="tu_api_key"
python -m agents.consulta_normativa.main
```

## Prerrequisitos

| Requisito | Detalle |
|---|---|
| Child chunks recomendados | `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` debe existir. |
| Documentos de tabla | `data/processed/table_documents.jsonl` debe existir. Para regenerarlo, consulta [`table-processing.md`](table-processing.md). |
| Dependencias Python | `requirements.txt` incluye splitters, embeddings, Groq, Pandoc wrapper, Sentence Transformers y tokenización. |
| Descarga/caché de modelo | Chroma usa `Qwen/Qwen3-Embedding-0.6B`; el entorno debe poder cargarlo. |
| Groq | `GROQ_API_KEY` debe estar en variables de entorno antes de consultar. |

## Secuencia operativa

### 1. Vectorizar en ChromaDB

```bash
python -m pipeline.vectorization.main --batch-size 8
```

Entradas y salida:

| Entrada | Salida |
|---|---|
| `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` | `data/processed/chroma` |
| `data/processed/table_documents.jsonl` | Colección `sg_sst_base_rag` |

La ingesta usa `open_or_create_collection(...)` y `upsert`. Esto permite crear o actualizar la colección, pero no elimina documentos obsoletos que ya no existan en los JSONL fuente.

### 2. Reconstrucción limpia de Chroma

Si cambiaste chunks, documentos de tabla o embeddings y necesitas evitar registros obsoletos, elimina o mueve el índice antes de vectorizar.

Antes de una reconstrucción limpia, confirma que existen los chunks actuales y `data/processed/table_documents.jsonl` actualizado. Si los documentos de tabla no están vigentes, regenéralos con [`table-processing.md`](table-processing.md) antes de indexar.

```bash
rm -rf data/processed/chroma
python -m pipeline.vectorization.main --batch-size 8
```

Si necesitas conservar el índice anterior para comparación, muévelo en lugar de borrarlo.

```bash
mv data/processed/chroma data/processed/chroma.backup
python -m pipeline.vectorization.main --batch-size 8
```

### 3. Configurar Groq

```bash
export GROQ_API_KEY="tu_api_key"
```

No guardes esta clave en archivos del repositorio.

### 4. Abrir consulta normativa interactiva

```bash
python -m agents.consulta_normativa.main
```

Comportamiento esperado:

```txt
RAG normativo listo. Escribe 'exit' o 'quit' para salir.
Pregunta> ¿Qué debe incluir el plan anual de trabajo del SG-SST?
```

Escribe una pregunta por turno. Usa `exit` o `quit` para cerrar.

## Contratos importantes

| Área | Contrato operativo |
|---|---|
| Entrada principal del RAG | `regex_constrained_semantic/chunks.jsonl`, no `semantic_chunking/chunks.jsonl`. |
| Tablas | Se indexan como documentos independientes desde `table_documents.jsonl`; su regeneración se documenta en [`table-processing.md`](table-processing.md). |
| Metadatos | Chroma recibe metadata plana y lógica; no rutas físicas de tablas. |
| Modelo de embeddings | `Qwen/Qwen3-Embedding-0.6B`. |
| Colección | `sg_sst_base_rag`. |
| Persistencia | `data/processed/chroma`. |
| Consulta | Usa `open_existing_collection(...)`; si no existe la colección, debe fallar de forma controlada. |
| LLM | Groq `openai/gpt-oss-120b` con temperatura `0`. |
