# OpenCode Instructions

This repo is a thesis RAG system for SG-SST normative assistance and compliance diagnosis for Colombian risk-I MiPymes.

## Source of truth

- If methodology docs conflict, trust `docs/EISI_2026-04-09_14-25-36_pg1409.pdf` over stale prose.
- Keep legal scope anchored to Decreto 1072/2015, Resolución 0312/2019, Resolución 2346/2007, Resolución 1401/2007, Ley 1562/2012, Resolución 2013/1986, Ley 1010/2006, and Decreto 768/2022.
- Current technical docs: `docs/architecture/`; operational runbooks: `docs/operations/`; experiment notes: `docs/experiments/`.

## Tooling and verification

- Root manifest is only `requirements.txt`; no pyproject, lockfile, Makefile/task runner, CI workflow, formatter, lint, typecheck, pre-commit, or repo-local OpenCode config is present.
- `chromadb` is imported lazily by vector/RAG code but is not listed in `requirements.txt`; install/verify it separately before real Chroma runs.
- Broad pipeline suite: `python -m unittest discover -s pipeline/tests`.
- Focused table tests: `python -m unittest pipeline.tests.test_tables_main pipeline.tests.test_table_references pipeline.tests.test_table_markdown pipeline.tests.test_table_documents`.
- Focused vector/RAG tests: `python -m unittest pipeline.tests.test_vectorization_documents pipeline.tests.test_vectorization_chroma_store agents.consulta_normativa.tests.test_cli agents.consulta_normativa.tests.test_rag_base agents.consulta_normativa.tests.test_langchain_rag_main agents.consulta_normativa.tests.test_langchain_rag_graph agents.consulta_normativa.tests.test_langchain_rag_query_rewrite agents.consulta_normativa.tests.test_langchain_rag_multi_query agents.consulta_normativa.tests.test_langchain_rag_fusion`.
- Compile check for vector/RAG work: `python -m compileall pipeline/tables pipeline/vectorization agents/consulta_normativa agents/shared`.
- If `.codegraph/` exists, use CodeGraph before broad filesystem searches for structural questions.

## Boundaries agents tend to cross

- `pipeline/` is offline corpus transformation only; keep runtime agent logic out of it.
- `agents/` is online LLM/RAG logic. `agents/shared/chroma_retrieval.py` owns query-only Chroma helpers; collection creation/upsert belongs in `pipeline/vectorization/`.
- `agents/consulta_normativa/` is Phase 4 Block A; represent the five consultation-agent stages with git tags, not duplicated `etapa_*` folders.
- `agents/diagnostico_cumplimiento/` is Phase 4 Block B; expected output is requirement-by-requirement compliance plus executive critical gaps and priority actions.
- `app/backend/` and `app/frontend/` are still placeholder `.gitkeep` scaffolds.
- `data/raw/`, `data/interim/`, and `data/processed/` are local/regenerable; do not assume source DOCX or generated corpus files are versioned.
- `evaluation/resultados_usuarios/` is confidential raw company data; anonymize identifiers and confirm consent before storing anything. Contents are ignored except README.
- `docs/decisiones/` contains planning/decision records; do not add files there unless explicitly requested.

## Methodology constraints to preserve

- Phase 2 corpus flow: DOCX ingestion → Markdown cleaning → parent chunks → child chunks → table documents → vector-ready artifacts.
- Phase 3 evaluation precedes agent development: Conjunto A calibrates ARES as expert gold standard; Conjunto B is for development optimization.
- Consultation-agent stages are base RAG, query understanding, retrieval improvement, business context, and response validation/control.
- Each consultation-agent stage should compare three candidate techniques using ARES context relevance, answer faithfulness, and answer relevance metrics with confidence intervals.
- Final system evaluation combines sessions from at least five risk-I companies, expert SST validation, and calibrated ARES evaluation.

## Design rules to preserve

- Apply YAGNI/KISS; do not add wrappers, DTOs, interfaces, or placeholders for hypothetical future phases.
- Prefer local cohesion and workflow/domain grouping over dogmatic layering.
- Preserve existing code comments, including informal Spanish notes, unless directly changing that code or explicitly asked to remove them.
- Metadata extraction is deterministic: optional manifest + regex over cleaned Markdown + pipeline-calculated offsets/token counts. Do not use an LLM as primary metadata extractor.
- Table references use logical metadata (`source_stem`, `table_index`, `table_key`); do not persist physical HTML/Markdown paths in chunks or Chroma metadata.

## Real entrypoints and gotchas

- DOCX ingestion: `python pipeline/ingestion/docx_to_markdown.py` reads `data/raw/*.docx`, writes `data/interim/*.md` plus extracted HTML tables, and requires system Pandoc plus `pypandoc`.
- Markdown cleaning: `python pipeline/cleaning/markdown_cleaner.py` reads `data/interim/*.md` and writes `data/processed/*.md`.
- Chunking: `python -m pipeline.chunking.main build-parents`, then `build-sliding-window` baseline, then recommended `build-regex-constrained-semantic`; avoid pure `semantic_chunking` as final SG-SST output.
- Tables: prefer `python -m pipeline.tables.main audit-table-references|build-table-markdown|build-table-documents`; `pipeline.chunking.main` exposes table commands only for compatibility.
- Vectorization: `python -m pipeline.vectorization.main --batch-size 8` indexes `regex_constrained_semantic/chunks.jsonl` and `table_documents.jsonl` into Chroma collection `sg_sst_base_rag` under `data/processed/chroma`.
- Vector ingestion uses upsert and does not delete stale Chroma records; remove/move `data/processed/chroma` for a clean rebuild.
- Current consultation CLI: set `DEEPSEEK_API_KEY`, ensure `data/processed/chroma` exists, then run `python -m agents.consulta_normativa.langchain_rag.main`; it opens an existing collection and must not create an empty one.
- `langchain_rag/main.py` currently wires the Multi-Query + RRF graph (`build_langgraph_rag_multiquery_rrf`), not the older base graph.
- The LangGraph CLI currently writes `data/images/base_rag_graph.png` during runtime setup; missing `data/images/` can fail initialization.
- Default embedding model is `Qwen/Qwen3-Embedding-0.6B`; default LangGraph generator is DeepSeek `deepseek-chat` via `https://api.deepseek.com` at temperature `0`.
- Optional table preview: `python -m pipeline.tables.table_jsonl_to_html`; the implemented output directory is intentionally `data/processed/tables_htlm`.
