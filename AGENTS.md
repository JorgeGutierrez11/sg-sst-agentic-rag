# OpenCode Instructions

This repository is a thesis RAG system for SG-SST normative assistance and compliance diagnosis for Colombian risk-I MiPymes.

## Sources of truth

- For methodology and scope, prefer `docs/EISI_2026-04-09_14-25-36_pg1409.pdf`; implementation behavior comes from executable source and tests when prose lags.
- The legal corpus is limited to Decreto 1072/2015, Resolución 0312/2019, Resolución 2346/2007, Resolución 1401/2007, Ley 1562/2012, Resolución 2013/1986, Ley 1010/2006, and the risk classification in Decreto 768/2022.
- Architecture decisions live in `docs/architecture/`, operating procedures in `docs/operations/`, and experiment records in `docs/experiments/` and `evaluation/experiments/`.

## Repository boundaries

- `pipeline/` transforms the offline corpus; collection creation/upsert belongs in `pipeline/vectorization/`, and BM25 construction belongs in `pipeline/sparse_indexing/`.
- Runtime retrieval helpers are under `agents/consulta_normativa/langchain_rag/retrieval/`; they open existing Chroma and BM25 indexes rather than creating empty ones.
- `agents/consulta_normativa/` is Phase 4 Block A. Preserve the five-stage progression with git tags, not duplicated `etapa_*` directories.
- `agents/diagnostico_cumplimiento/` is Phase 4 Block B; its required outputs are requirement-level compliance and an executive summary of critical gaps and priority actions.
- The implemented FastAPI service is in `agents/consulta_normativa/api/`; `app/backend/` and `app/frontend/` remain `.gitkeep` scaffolds.
- Generated data are not uniformly ignored: tracked files exist under `data/raw/`, `data/interim/`, and `data/processed/`, and Chroma runs mutate files under `data/processed/chroma/`. Inspect status before running pipelines.
- `evaluation/resultados_usuarios/` contains confidential company interactions. Anonymize identifiers and confirm consent covers storage; `.gitignore` excludes everything there except its README.
- `docs/decisiones/` is reserved for requested planning/decision records; do not add files there implicitly.

## Methodology contracts

- Phase 2 flows from official DOCX sources through cleaned Markdown, legal parent chunks, experimental child strategies, table documents, and vector/sparse indexes.
- Metadata extraction is deterministic: optional manifest, regex over cleaned Markdown, and pipeline-calculated offsets/token counts. Do not use an LLM as the primary extractor.
- The production child artifact is `data/processed/chunks/regex_constrained_semantic/chunks.jsonl`; pure semantic chunking is an experimental baseline because it can lose exact source offsets.
- Table links use logical metadata (`source_stem`, `table_index`, `table_key`); do not persist physical HTML/Markdown table paths in chunks or index metadata.
- Phase 3 precedes agent development: Conjunto A is expert-annotated gold data used only to calibrate ARES; Conjunto B drives development optimization.
- Each of the five consultation-agent stages evaluates three candidate techniques with ARES context relevance, answer faithfulness, and answer relevance, including confidence intervals.
- Final evaluation combines interactions from at least five risk-I companies, expert SST validation, and calibrated ARES evaluation.

## Toolchain and verification

- `requirements.txt` is the only root manifest. There is no lockfile, pyproject/setup config, task runner, CI workflow, pre-commit, formatter, lint, typecheck, codegen, or repo-local OpenCode config.
- `chromadb` is imported lazily but absent from `requirements.txt`; install or verify it separately before real Chroma operations.
- Run pipeline tests with `python -m unittest discover -s pipeline/tests` and consultation-agent tests with `python -m unittest discover -s agents/consulta_normativa/tests`.
- Focus table regressions with `python -m unittest pipeline.tests.test_tables_main pipeline.tests.test_table_references pipeline.tests.test_table_markdown pipeline.tests.test_table_documents`.
- Focus retrieval/index regressions with `python -m unittest pipeline.tests.test_vectorization_documents pipeline.tests.test_vectorization_chroma_store pipeline.tests.test_sparse_indexing_bm25_store pipeline.tests.test_sparse_indexing_ingest agents.consulta_normativa.tests.test_chroma_retrieval agents.consulta_normativa.tests.test_bm25_retrieval agents.consulta_normativa.tests.test_hybrid_retrieval agents.consulta_normativa.tests.test_parent_document_retrieval agents.consulta_normativa.tests.test_langchain_rag_graph agents.consulta_normativa.tests.test_langchain_rag_main`.
- Use the existing `.codegraph/` index before broad filesystem searches for code structure or call flow.

## Executable workflow and gotchas

- Run all commands from the repository root; CLIs use project-relative defaults.
- Ingest DOCX with `python pipeline/ingestion/docx_to_markdown.py`; it requires both `pypandoc` and system Pandoc, reads `data/raw/*.docx`, and writes Markdown plus extracted HTML tables under `data/interim/`.
- Clean with `python pipeline/cleaning/markdown_cleaner.py`, then build `build-parents`, the `build-sliding-window` baseline, and `build-regex-constrained-semantic` through `python -m pipeline.chunking.main <command>`. These chunking subcommands expose no path flags.
- Process tables with `python -m pipeline.tables.main audit-table-references`, then `build-table-markdown`, then `build-table-documents`; duplicate table commands in `pipeline.chunking.main` exist only for compatibility.
- Build dense and sparse indexes from the same child/table JSONL inputs: `python -m pipeline.vectorization.main --batch-size 8` writes Chroma collection `sg_sst_base_rag`, and `python -m pipeline.sparse_indexing.main` writes `data/processed/bm25/`.
- Chroma ingestion uses upsert and does not remove records deleted from source JSONL; a clean rebuild requires deliberately removing or moving the existing index first.
- The consultation runtime needs `DEEPSEEK_API_KEY`, existing Chroma and BM25 indexes, and `data/processed/chunks/parents.jsonl`; run it with `python -m agents.consulta_normativa.langchain_rag.main ["question"]`.
- The current graph performs hybrid Chroma+BM25 RRF retrieval, parent expansion, a sufficient-context gate, generation, and self-refinement. Experimental query-rewrite, multi-query, and reranking modules are not the wired runtime.
- The CLI writes `data/images/base_rag_graph.png` during startup and can fail if `data/images/` is absent; the FastAPI lifespan disables this write.
- Defaults are `Qwen/Qwen3-Embedding-0.6B` for embeddings and DeepSeek `deepseek-chat` at `https://api.deepseek.com`, temperature `0`, for generation.
- `python -m pipeline.tables.table_jsonl_to_html` is an optional preview tool whose default output is the intentionally misspelled `data/processed/tables_htlm/`.
