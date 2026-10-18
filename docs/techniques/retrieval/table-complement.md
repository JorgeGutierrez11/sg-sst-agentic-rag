# Complemento de tablas enlazadas

> **Status:** `Current`
> **Audience:** contributor, academic-reviewer
> **Verified against:** `agents/consulta_normativa/langchain_rag/retrieval/table_complement.py`, `graph.py`, `main.py`
> **Last verified:** 2026-10-18
> **Replacement:** N/A

## Problema

Las normas SG-SST remiten a tablas (por ejemplo, los estándares mínimos de la Resolución 0312/2019) desde el texto de un artículo. Un chunk de texto relevante puede citar una tabla que la recuperación no trajo, y el LLM respondería sin los valores de esa tabla.

## Solución

Después del grading de relevancia, el nodo `complement_linked_tables` revisa la metadata `table_keys` de los documentos que sobrevivieron y agrega la **primera parte** (`table_part_index = 0`) de cada tabla enlazada que aún no esté en la evidencia.

```text
retrieval_relevance_grading -> complement_linked_tables -> evidence_route
```

## Comportamiento

| Aspecto | Regla |
|---|---|
| Fuente | `data/processed/table_documents.jsonl`, cargado una vez al arrancar con `load_first_table_parts` (lookup por `table_key`). |
| Orden | Las tablas se agregan al final, en el orden en que aparecen las claves en los documentos. |
| Deduplicación | No agrega una tabla si su id (`_document_id`, `document_id`, `id`, `chunk_id`) o su identidad (`table_key`, `table_part_index`) ya está en la evidencia. |
| Formato de claves | Acepta listas en memoria o cadenas separadas por comas (como las persiste Chroma). |
| Sin evidencia | Si el grading dejó cero documentos, no agrega nada y el grafo va a `fallback_answer`. |
| Registros inválidos | Se ignoran partes sin id, texto, `table_key`, `table_part_count`, `source_stem` o `table_index`. |

Solo se agrega la primera parte de cada tabla. Las tablas largas divididas en varias partes pueden necesitar que la recuperación traiga las demás.

## Relación con el pipeline

Las claves `table_key` y `table_keys` las genera el [procesamiento de tablas](../../architecture/tables.md). Ver también el [grafo vigente](../../architecture/retrieval-langgraph.md).
