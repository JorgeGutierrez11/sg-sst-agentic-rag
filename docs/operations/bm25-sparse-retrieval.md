# Guía operativa: recuperación sparse BM25

Esta guía cubre únicamente la operación del índice BM25 local para el corpus SG-SST. BM25 se construye desde los JSONL canónicos del pipeline y se consulta en runtime como un helper de solo lectura; no opera la integración híbrida ni modifica LangGraph.

## Ruta rápida

```bash
python -m pipeline.sparse_indexing.main
```

Salida esperada: índice BM25S persistido en `data/processed/bm25/`.

## Prerrequisitos

| Requisito | Detalle |
|---|---|
| Dependencias Python | Instalar `requirements.txt`; debe estar disponible el módulo `bm25s`. |
| Child chunks recomendados | Debe existir `data/processed/chunks/regex_constrained_semantic/chunks.jsonl`. |
| Documentos de tabla | Debe existir `data/processed/table_documents.jsonl`. |
| Ejecución desde raíz | Los comandos asumen rutas relativas del proyecto. |

Si faltan los JSONL canónicos, reconstruye primero el corpus con [`corpus-build.md`](corpus-build.md). BM25 no lee desde Chroma.

## Construir el índice

```bash
python -m pipeline.sparse_indexing.main
```

La CLI imprime el total de documentos indexados, el desglose por `child_chunk` y `table`, y el número de registros omitidos por venir inválidos o vacíos desde los JSONL fuente.

### Opciones de CLI

| Opción | Uso |
|---|---|
| `--chunks-path` | Ruta al JSONL de child chunks. Default: `data/processed/chunks/regex_constrained_semantic/chunks.jsonl`. |
| `--tables-path` | Ruta al JSONL de documentos de tabla. Default: `data/processed/table_documents.jsonl`. |
| `--persist-path` | Ruta de salida del índice BM25. Default: `data/processed/bm25/`. |

Ejemplo con rutas explícitas:

```bash
python -m pipeline.sparse_indexing.main \
  --chunks-path data/processed/chunks/regex_constrained_semantic/chunks.jsonl \
  --tables-path data/processed/table_documents.jsonl \
  --persist-path data/processed/bm25
```

## Reconstrucción limpia

Si necesitas evitar residuos de una versión anterior del índice, elimina o mueve `data/processed/bm25/` antes de reconstruir.

```bash
rm -rf data/processed/bm25
python -m pipeline.sparse_indexing.main
```

Para conservar el índice anterior:

```bash
mv data/processed/bm25 data/processed/bm25.backup
python -m pipeline.sparse_indexing.main
```

La reconstrucción limpia depende de los JSONL actuales. No hace sincronización contra Chroma ni elimina registros en Chroma.

## Uso runtime

El runtime vive en `agents/shared/bm25_retrieval.py`.

```python
from agents.shared.bm25_retrieval import open_existing_index, query_top_k

index = open_existing_index()
result = query_top_k(index, "¿Qué exige la Resolución 0312?", top_k=5)
```

`open_existing_index(...)` carga un índice BM25S ya persistido con `load_corpus=True`. Si la ruta no existe, falla con `ValueError` en lugar de crear un índice vacío.

`query_top_k(...)` devuelve una estructura compatible con Chroma:

```python
{
    "ids": [[...]],
    "documents": [[...]],
    "metadatas": [[...]],
    "scores": [[...]],
}
```

Los `scores` son puntajes BM25. Si `top_k` es mayor que el tamaño del corpus, se ajusta al número real de documentos disponibles.

## Verificación

Pruebas enfocadas de BM25:

```bash
python -m unittest pipeline.tests.test_sparse_indexing_bm25_store pipeline.tests.test_sparse_indexing_ingest agents.consulta_normativa.tests.test_bm25_retrieval
```

Regresiones útiles si el cambio toca entradas compartidas con vectorización o formato RAG:

```bash
python -m unittest pipeline.tests.test_vectorization_documents pipeline.tests.test_vectorization_chroma_store
python -m unittest agents.consulta_normativa.tests.test_rag_base agents.consulta_normativa.tests.test_langchain_rag_formatting
```

Chequeo de compilación:

```bash
python -m compileall pipeline/vectorization pipeline/sparse_indexing agents/shared agents/consulta_normativa
```

## Troubleshooting

| Síntoma | Causa probable | Acción |
|---|---|---|
| `No module named 'bm25s'` | Dependencia no instalada en el entorno activo. | Instalar `requirements.txt` y confirmar que `python -c "import bm25s"` funciona. |
| `Missing sparse indexing source JSONL file(s)` | Faltan `chunks.jsonl`, `table_documents.jsonl` o una ruta personalizada. | Reconstruir el corpus o corregir `--chunks-path` / `--tables-path`. |
| `BM25 persist path does not exist` | Se intentó consultar antes de construir el índice. | Ejecutar `python -m pipeline.sparse_indexing.main` o pasar el `persist_path` correcto a `open_existing_index(...)`. |
| `top_k` mayor que el corpus | La consulta pide más resultados que documentos indexados. | No requiere acción: `query_top_k(...)` reduce `top_k` al tamaño del corpus. |
| Prueba smoke real marcada como skipped | `bm25s` no está instalado; los unit tests con dobles aún pueden correr. | Instalar la dependencia si quieres validar con la librería real. |

## Fuera de alcance

Esta guía no documenta operación de recuperación híbrida, RRF, Multi-Query ni cambios en LangGraph. Esos pasos pertenecen a una fase posterior.
