# Metadata Enrichment for Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the text seen by the Cross-Encoder reranker and the BM25 sparse index with compact normative metadata, without adding trace/debug metadata or changing public retrieval result documents.

**Architecture:** Add minimal metadata-to-text formatting at the two scoring boundaries only: reranking input text and BM25 indexed text. Keep Chroma retrieval filters, post-retrieval boosts, query rewriting, and graph changes out of scope for this iteration. Preserve original document text in returned records; enriched text is only a scoring aid.

**Tech Stack:** Python, `sentence-transformers` `CrossEncoder.predict([(query, passage), ...])`, `bm25s.tokenize(corpus_texts, stopwords="es")`, `unittest`.

## Global Constraints

- Do not modify Chroma ingestion or Chroma metadata filters in this iteration.
- Do not add metadata-aware boosting in this iteration.
- Do not include trace/debug metadata in enriched text.
- Do not include physical file paths in enriched text.
- Preserve original `RetrievedDocument.document` and BM25 corpus `record["document"]` as the raw normative content.
- Use only compact legal/normative locator metadata.
- Keep implementation KISS/YAGNI; no new DTO layer, no configurable registry, no LLM-based metadata extraction.
- Use `python -m unittest`, not pytest.

---

## External references checked

- Sentence Transformers CrossEncoder documentation: `CrossEncoder.predict` accepts text pairs like `[(query, passage), ...]` and returns scores. Therefore metadata can be prepended to the candidate passage string without changing the CrossEncoder API.
- BM25S documentation: BM25 indexes tokenized corpus strings via `bm25s.tokenize(corpus, stopwords="...")`; saving can preserve an attached corpus. Therefore BM25 can index enriched text while still saving/returning the original corpus record.
- Chroma documentation: metadata filters exist through `where`/`where_document`, but filters are explicitly out of scope for this plan.

## Metadata policy

### Include only these fields

Use this exact order and omit empty values:

| Metadata key | Label in enriched text | Why it matters |
|---|---|---|
| `source_stem` | `Fuente` | Matches normative source names such as Decreto 1072 or Resolución 0312. |
| `normative_document_type` | `Tipo normativo` | Helps distinguish decree, resolution, law, etc. |
| `year` | `Año` | Helps exact legal-year queries. |
| `title` | `Título` | Adds compact subject context when available. |
| `chapter` | `Capítulo` | Helps locate legal section context. |
| `article` | `Artículo` | Critical for article-specific questions. |
| `paragraph` | `Parágrafo` | Critical for legal substructure. |
| `numeral` | `Numeral` | Critical for legal substructure. |
| `literal` | `Literal` | Critical for legal substructure. |
| `document_type` | `Tipo de fragmento` | Distinguishes `child_chunk`, `parent_chunk`, and `table`. |
| `table_key` | `Tabla` | Helps table-specific retrieval. |
| `table_keys` | `Tablas relacionadas` | Helps chunks that reference logical tables. |

### Exclude these fields

Never include:

- keys starting with `_`, for example `_chroma_id`, `_document_id`, `_retrieval_sources`;
- identity/control fields: `document_id`, `parent_id`, `chunk_id`, `table_id`;
- parent-expansion trace fields: `parent_expansion_applied`, `expanded_from_child_ids`, `expanded_from_child_retrieval_sources`;
- offsets/counts: `start_char`, `end_char`, `token_count`, `char_count`, `chunk_index`, `table_part_index`, `table_part_count`;
- physical paths or generated file paths;
- scores, distances, retrieval sources, debug flags, or CLI/runtime traces.

### Enriched text format

Use one compact block before content:

```text
Metadata normativa:
Fuente: resolucion_0312_2019
Tipo normativo: resolucion
Año: 2019
Artículo: 16
Tipo de fragmento: table
Tabla: resolucion_0312_2019_table_1

Contenido:
<document text>
```

If no included metadata exists, return the original document text unchanged.

---

## Task 1: Add Cross-Encoder metadata enrichment

**Files:**
- Modify: `agents/consulta_normativa/langchain_rag/retrieval/reranking.py`
- Test: `agents/consulta_normativa/tests/test_langchain_rag_reranking.py`

**Interfaces:**
- Consumes: `RetrievedDocument(document: str, metadata: dict[str, Any])`.
- Produces: `document_text_for_reranking(document: RetrievedDocument) -> str` returning enriched candidate text for CrossEncoder only.

- [ ] **Step 1: Write failing tests for included metadata**

Add tests equivalent to:

```python
def test_document_text_for_reranking_adds_compact_normative_metadata(self) -> None:
    document = RetrievedDocument(
        "El empleador debe identificar peligros y valorar riesgos.",
        {
            "source_stem": "decreto_1072_2015",
            "normative_document_type": "decreto",
            "year": 2015,
            "article": "2.2.4.6.15",
            "document_type": "child_chunk",
        },
    )

    text = document_text_for_reranking(document)

    self.assertIn("Metadata normativa:", text)
    self.assertIn("Fuente: decreto_1072_2015", text)
    self.assertIn("Tipo normativo: decreto", text)
    self.assertIn("Año: 2015", text)
    self.assertIn("Artículo: 2.2.4.6.15", text)
    self.assertIn("Tipo de fragmento: child_chunk", text)
    self.assertIn("Contenido:\nEl empleador debe identificar peligros", text)
```

- [ ] **Step 2: Write failing tests excluding trace metadata**

Add tests equivalent to:

```python
def test_document_text_for_reranking_excludes_trace_metadata(self) -> None:
    document = RetrievedDocument(
        "Contenido normativo.",
        {
            "source_stem": "resolucion_0312_2019",
            "_chroma_id": "abc",
            "_document_id": "doc-1",
            "_retrieval_sources": ["dense", "sparse"],
            "document_id": "doc-1",
            "parent_id": "parent-1",
            "expanded_from_child_ids": ["child-1"],
            "start_char": 10,
            "end_char": 50,
            "token_count": 20,
        },
    )

    text = document_text_for_reranking(document)

    self.assertIn("Fuente: resolucion_0312_2019", text)
    self.assertNotIn("_chroma_id", text)
    self.assertNotIn("abc", text)
    self.assertNotIn("_retrieval_sources", text)
    self.assertNotIn("dense", text)
    self.assertNotIn("document_id", text)
    self.assertNotIn("parent-1", text)
    self.assertNotIn("expanded_from_child_ids", text)
    self.assertNotIn("start_char", text)
    self.assertNotIn("token_count", text)
```

- [ ] **Step 3: Write failing test preserving raw text when metadata is empty**

```python
def test_document_text_for_reranking_returns_document_when_metadata_empty(self) -> None:
    document = RetrievedDocument("Solo contenido.", {})

    self.assertEqual(document_text_for_reranking(document), "Solo contenido.")
```

- [ ] **Step 4: Implement minimal enrichment helper in `reranking.py`**

Add constants and helpers near `document_text_for_reranking`:

```python
RERANKING_METADATA_FIELDS = (
    ("Fuente", "source_stem"),
    ("Tipo normativo", "normative_document_type"),
    ("Año", "year"),
    ("Título", "title"),
    ("Capítulo", "chapter"),
    ("Artículo", "article"),
    ("Parágrafo", "paragraph"),
    ("Numeral", "numeral"),
    ("Literal", "literal"),
    ("Tipo de fragmento", "document_type"),
    ("Tabla", "table_key"),
    ("Tablas relacionadas", "table_keys"),
)


def document_text_for_reranking(document: RetrievedDocument) -> str:
    """Return compact metadata plus text sent to the reranker for one candidate."""

    metadata_text = compact_normative_metadata_text(document.metadata, RERANKING_METADATA_FIELDS)
    if not metadata_text:
        return document.document
    return f"Metadata normativa:\n{metadata_text}\n\nContenido:\n{document.document}"


def compact_normative_metadata_text(
    metadata: dict[str, Any],
    fields: tuple[tuple[str, str], ...],
) -> str:
    """Return only compact legal locator metadata; never trace/debug metadata."""

    lines: list[str] = []
    for label, key in fields:
        value = metadata.get(key)
        formatted = format_metadata_value(value)
        if formatted:
            lines.append(f"{label}: {formatted}")
    return "\n".join(lines)


def format_metadata_value(value: object) -> str:
    """Format scalar or list metadata values for retrieval scoring text."""

    if value in (None, ""):
        return ""
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(items)
    return str(value).strip()
```

- [ ] **Step 5: Run reranking tests**

Run:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_reranking
```

Expected: PASS.

---

## Task 2: Add BM25 metadata enrichment without changing returned corpus text

**Files:**
- Modify: `pipeline/sparse_indexing/bm25_store.py`
- Test: `pipeline/tests/test_sparse_indexing_bm25_store.py`

**Interfaces:**
- Consumes: `records: list[ChromaRecord]`.
- Produces: `bm25_text_for_indexing(record: ChromaRecord) -> str` used only for tokenization/indexing.
- Preserves: `bm25_corpus(records)` must continue returning original `document` and original `metadata`.

- [ ] **Step 1: Write failing test that BM25 tokenizes enriched text**

Patch the fake `bm25s.tokenize` boundary and assert the corpus text passed to tokenization includes metadata plus content.

Example expectation:

```python
expected_text = (
    "Metadata normativa:\n"
    "Fuente: resolucion_0312_2019\n"
    "Tipo normativo: resolucion\n"
    "Año: 2019\n"
    "Tipo de fragmento: table\n"
    "Tabla: resolucion_0312_2019_table_1\n\n"
    "Contenido:\n"
    "Tabla de estándares mínimos."
)
```

The test must assert that `build_bm25_index(records)` calls `bm25s.tokenize([expected_text], stopwords="es")`.

- [ ] **Step 2: Write failing test that BM25 corpus remains raw**

```python
def test_bm25_corpus_preserves_original_document_and_metadata(self) -> None:
    record = ChromaRecord(
        id="table-1",
        document="Tabla de estándares mínimos.",
        metadata={"source_stem": "resolucion_0312_2019", "table_key": "table_1"},
    )

    corpus = bm25_corpus([record])

    self.assertEqual(corpus[0]["document"], "Tabla de estándares mínimos.")
    self.assertEqual(corpus[0]["metadata"], record.metadata)
```

- [ ] **Step 3: Write failing test excluding trace metadata from BM25 indexed text**

```python
def test_bm25_text_for_indexing_excludes_trace_metadata(self) -> None:
    record = ChromaRecord(
        id="chunk-1",
        document="Contenido normativo.",
        metadata={
            "source_stem": "decreto_1072_2015",
            "_retrieval_sources": ["dense", "sparse"],
            "_chroma_id": "abc",
            "document_id": "doc-1",
            "parent_id": "parent-1",
            "start_char": 10,
            "token_count": 20,
        },
    )

    text = bm25_text_for_indexing(record)

    self.assertIn("Fuente: decreto_1072_2015", text)
    self.assertIn("Contenido:\nContenido normativo.", text)
    self.assertNotIn("_retrieval_sources", text)
    self.assertNotIn("dense", text)
    self.assertNotIn("_chroma_id", text)
    self.assertNotIn("abc", text)
    self.assertNotIn("document_id", text)
    self.assertNotIn("parent-1", text)
    self.assertNotIn("start_char", text)
    self.assertNotIn("token_count", text)
```

- [ ] **Step 4: Implement `bm25_text_for_indexing` in `bm25_store.py`**

Add constants/helpers in `pipeline/sparse_indexing/bm25_store.py`.

Use the same whitelist and format as reranking, but keep it local to this module to avoid coupling offline pipeline code with online agent runtime code.

```python
BM25_METADATA_FIELDS = (
    ("Fuente", "source_stem"),
    ("Tipo normativo", "normative_document_type"),
    ("Año", "year"),
    ("Título", "title"),
    ("Capítulo", "chapter"),
    ("Artículo", "article"),
    ("Parágrafo", "paragraph"),
    ("Numeral", "numeral"),
    ("Literal", "literal"),
    ("Tipo de fragmento", "document_type"),
    ("Tabla", "table_key"),
    ("Tablas relacionadas", "table_keys"),
)


def bm25_text_for_indexing(record: ChromaRecord) -> str:
    """Return compact metadata plus document text used only for BM25 indexing."""

    metadata_text = compact_normative_metadata_text(record.metadata, BM25_METADATA_FIELDS)
    if not metadata_text:
        return record.document
    return f"Metadata normativa:\n{metadata_text}\n\nContenido:\n{record.document}"
```

Also add local `compact_normative_metadata_text(...)` and `format_metadata_value(...)` equivalent to Task 1.

- [ ] **Step 5: Change BM25 indexing text only**

Modify `build_bm25_index`:

```python
texts = [bm25_text_for_indexing(record) for record in records]
```

Keep this unchanged:

```python
corpus = bm25_corpus(records)
```

Do not save enriched text in the corpus unless a future plan explicitly requires it.

- [ ] **Step 6: Run sparse indexing tests**

Run:

```bash
python -m unittest pipeline.tests.test_sparse_indexing_bm25_store pipeline.tests.test_sparse_indexing_ingest
```

Expected: PASS.

---

## Task 3: Add a focused regression test for runtime behavior

**Files:**
- Modify: `agents/consulta_normativa/tests/test_langchain_rag_reranking.py`
- Modify: `pipeline/tests/test_sparse_indexing_bm25_store.py`

**Interfaces:**
- Confirms enriched text affects only scorer input.
- Confirms returned document content remains raw.

- [ ] **Step 1: Assert CrossEncoder receives enriched text but selected docs remain raw**

In the reranking test fake, inspect `reranker.predict` input pairs:

```python
self.assertEqual(candidate_pairs[0][0], "¿Qué exige la Resolución 0312?")
self.assertIn("Fuente: resolucion_0312_2019", candidate_pairs[0][1])
self.assertIn("Contenido:\nTexto normativo original", candidate_pairs[0][1])
self.assertEqual(selected_documents[0].document, "Texto normativo original")
```

- [ ] **Step 2: Assert BM25 retrieval returns raw corpus document**

If existing BM25 retrieval tests load a saved fake corpus, keep the expected runtime output as:

```python
"documents": [["Texto normativo original"]]
```

Do not update runtime retrieval to return enriched text.

---

## Task 4: Verification commands

Run the focused suite:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_reranking
python -m unittest pipeline.tests.test_sparse_indexing_bm25_store pipeline.tests.test_sparse_indexing_ingest
python -m compileall pipeline/sparse_indexing agents/consulta_normativa/langchain_rag/retrieval
```

If changes touch shared retrieval behavior, run:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_graph agents.consulta_normativa.tests.test_langchain_rag_reranking agents.consulta_normativa.tests.test_langchain_rag_fusion
```

## Acceptance criteria

- CrossEncoder candidate pairs include compact normative metadata plus original document content.
- CrossEncoder candidate pairs do not include trace/debug metadata.
- BM25 tokenization indexes compact normative metadata plus original document content.
- BM25 saved corpus still preserves raw document text and original metadata.
- Runtime retrieval/reranking outputs still expose raw document text to downstream context formatting.
- No Chroma filter, metadata boost, graph change, or LLM metadata extraction is introduced.
- All focused `unittest` commands pass.

## Risks to watch during evaluation

- Metadata can over-bias reranking toward the right source but wrong fragment.
- BM25 enrichment can improve exact legal locator matches but may increase false positives when a source name appears in many chunks.
- Long metadata blocks can dilute content; keep the whitelist compact and omit empty fields.
- Improvements must be measured against baseline using context relevance, answer faithfulness, answer relevance, recall, and latency.
