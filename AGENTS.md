# OpenCode Instructions

This repository is a thesis RAG system for SG-SST normative assistance and compliance diagnosis for Colombian risk-I MiPymes. Run developer commands from the repository root.

## Sources and setup

- Treat `docs/EISI_2026-04-09_14-25-36_pg1409.pdf` as the methodology source of truth. Use `docs/architecture/` for intended technical contracts and `docs/operations/` for runbooks, but verify current runtime wiring against executable code because some retrieval documentation lags the implementation.
- The legal corpus is limited to Decreto 1072/2015, Resolución 0312/2019, Resolución 2346/2007, Resolución 1401/2007, Ley 1562/2012, Resolución 2013/1986, Ley 1010/2006, and the risk classification in Decreto 768/2022.
- `requirements.txt` is the only manifest. There is no lockfile, task runner, CI, pre-commit, formatter, lint, typecheck, codegen, or repository OpenCode configuration; do not invent project commands for them.
- Install `requirements.txt` in the active environment. `chromadb` is required by vectorization and runtime retrieval but is not declared there, so verify/install it separately before real Chroma runs.
- DOCX ingestion and table conversion require the Pandoc system binary in `PATH`; `pypandoc` alone is insufficient.

## Verification commands

```bash
# Broad suites
python -m unittest discover -s pipeline/tests
python -m unittest discover -s agents/consulta_normativa/tests

# Tables
python -m unittest pipeline.tests.test_tables_main pipeline.tests.test_table_references pipeline.tests.test_table_markdown pipeline.tests.test_table_documents

# Syntax/import-independent compile check
python -m compileall pipeline agents/consulta_normativa
```

Install the declared dependencies before treating import failures as regressions. The suites use `unittest`, not pytest.

## Package boundaries and data safety

- `pipeline/` is offline corpus transformation and index construction; keep online agent behavior out of it.
- `agents/consulta_normativa/langchain_rag/` is the current online implementation. Its `retrieval/` package owns query-only Chroma/BM25 helpers; collection creation/upsert belongs in `pipeline/vectorization/`, and BM25 construction belongs in `pipeline/sparse_indexing/`.
- `agents/consulta_normativa/api/` is the FastAPI adapter for the current runtime. `app/backend/`, `app/frontend/`, and `agents/diagnostico_cumplimiento/` remain `.gitkeep` scaffolds; do not add speculative layers there.
- `agents/consulta_normativa/manual_implementation/` is a frozen comparison baseline.
- `data/interim/` and `data/processed/` contain regenerable but potentially tracked outputs. Pipeline, Chroma, and BM25 commands can dirty them; inspect `git status` and never overwrite or revert unrelated generated-data changes.
- `evaluation/resultados_usuarios/` holds confidential raw company interactions. Anonymize identifiers and confirm consent covers storage before adding data; only its README is intentionally versioned by default.
- Do not add records under `docs/decisiones/` unless explicitly requested. Preserve existing comments, including informal Spanish comments, unless the edited behavior requires changing them.
- If `.codegraph/` exists, use CodeGraph before broad filesystem searches for architecture, call-flow, or impact questions.

## Corpus and index entrypoints

```bash
python pipeline/ingestion/docx_to_markdown.py
python pipeline/cleaning/markdown_cleaner.py
python -m pipeline.chunking.main build-parents
python -m pipeline.chunking.main build-sliding-window
python -m pipeline.chunking.main build-regex-constrained-semantic
python -m pipeline.tables.main audit-table-references
python -m pipeline.tables.main build-table-markdown
python -m pipeline.tables.main build-table-documents
python -m pipeline.vectorization.main --batch-size 8
python -m pipeline.sparse_indexing.main
```

- The canonical flow is `data/raw/*.docx` → cleaned Markdown → parent chunks → regex-constrained semantic child chunks → table documents → Chroma and BM25. Sliding window is a baseline; do not substitute pure semantic chunking for the canonical SG-SST child output.
- Chunking subcommands use code-defined paths and do not accept operational path flags. Prefer `pipeline.tables.main` for table commands even though `pipeline.chunking.main` exposes compatibility aliases.
- Vectorization reads `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` and `data/processed/table_documents.jsonl`, then upserts collection `sg_sst_base_rag` under `data/processed/chroma`; upsert does not delete stale records, so move/remove the existing index for a deliberate clean rebuild.
- BM25 indexes the same JSONL inputs under `data/processed/bm25`. Optional table preview is `python -m pipeline.tables.table_jsonl_to_html`; its implemented output name is intentionally `data/processed/tables_htlm`.
- Metadata extraction must remain deterministic (optional manifest, regex over cleaned Markdown, and pipeline-calculated offsets/token counts). Table references use `source_stem`, `table_index`, and `table_key`; never persist physical HTML/Markdown paths in chunks or index metadata.

## Current consultation runtime

```bash
export DEEPSEEK_API_KEY="..."
python -m agents.consulta_normativa.langchain_rag.main
# Or answer once:
python -m agents.consulta_normativa.langchain_rag.main "<question>"
```

- Runtime requires existing `data/processed/chroma`, `data/processed/bm25`, `data/processed/chunks/parents.jsonl`, and writable `data/images/`; direct CLI startup writes `data/images/base_rag_graph.png` and must not create empty retrieval indexes.
- The FastAPI adapter's default lifespan calls `build_runtime(write_graph_image=False)`, so API startup builds the runtime without writing the CLI graph image.
- The wired graph currently performs business-profile and retrieval-based conversation memory, query expansion, hybrid Chroma+BM25 RRF retrieval, cross-encoder reranking, parent expansion, LLM relevance grading, evidence branching, generation, and memory updates. Do not infer wiring from unused experimental modules.
- Defaults are Qwen `Qwen/Qwen3-Embedding-0.6B`, reranker `BAAI/bge-reranker-v2-m3`, and DeepSeek `deepseek-chat` via `https://api.deepseek.com` at temperature `0`.

## Methodology constraints

- Phase 3 precedes agent development: Conjunto A is expert-annotated gold data for ARES calibration; Conjunto B is for development optimization.
- Represent the five consultation stages with git tags, not duplicated `etapa_*` folders. At each stage compare three candidate techniques using ARES context relevance, answer faithfulness, and answer relevance with confidence intervals.
- The future diagnosis agent must report compliance per normative requirement plus an executive summary of critical gaps and priority actions.
- Final evaluation combines sessions from at least five risk-I companies, expert SST validation, and calibrated ARES evaluation.
