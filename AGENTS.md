# OpenCode Instructions

This repo is a thesis RAG system for SG-SST normative assistance and compliance diagnosis for Colombian risk-I MiPymes.

## Source of truth

- When methodology conflicts, trust `docs/EISI_2026-04-09_14-25-36_pg1409.pdf` over stale prose.
- Keep scope anchored to the official SG-SST sources named in the plan: Decreto 1072/2015, Resolución 0312/2019, Resolución 2346/2007, Resolución 1401/2007, Ley 1562/2012, Resolución 2013/1986, Ley 1010/2006, and Decreto 768/2022.
- `docs/arquitectura.md` is referenced by docs but is currently absent; do not assume it exists.

## Tooling and verification

- Root dependency manifest is only `requirements.txt`; there is no pyproject, lockfile, Makefile/task runner, CI workflow, formatter, lint, typecheck, pre-commit, or repo-local OpenCode config discovered.
- Use `python -m unittest discover -s pipeline/tests` for the current Python test suite when dependencies are installed.
- Focused table pipeline tests: `python -m unittest pipeline.tests.test_table_references pipeline.tests.test_table_markdown pipeline.tests.test_table_documents`.
- Focused vector/RAG tests: `python -m unittest pipeline.tests.test_table_documents pipeline.tests.test_vectorization_documents pipeline.tests.test_vectorization_chroma_store pipeline.tests.test_consulta_normativa_cli pipeline.tests.test_consulta_normativa_rag_base`.
- Compile check for vector/RAG work: `python -m compileall pipeline/tables pipeline/vectorization agents/consulta_normativa`.
- If `.codegraph/` exists locally, use CodeGraph first for structural/codebase questions, then fall back to direct file reads only when needed.

## Directory boundaries

- `pipeline/`: offline corpus transformation only; keep runtime agent logic out of it.
- `agents/`: online LLM agent logic. `agents/consulta_normativa/` is Phase 4 Block A; represent the five consultation-agent stages with git tags, not duplicated `etapa_*` folders.
- `agents/shared/`: shared LLM clients, retrievers, prompts, adapters, and utilities reused by both agents.
- `agents/diagnostico_cumplimiento/`: Phase 4 Block B diagnostic agent; output requirement-by-requirement compliance plus executive summary of critical gaps and priority actions.
- `app/backend/` and `app/frontend/`: user-facing API/UI; currently only placeholder `.gitkeep` files exist.
- `evaluation/instruments/`: rubrics, surveys, protocols, consent, and sampling definitions; results do not belong here.
- `evaluation/results/`: processed/anonymized evaluation outputs, including ARES runs, expert validation, user-study summaries, and integrated reports.
- `evaluation/resultados_usuarios/`: confidential raw company interactions; anonymize identifiers and confirm consent before storing anything. Its contents are ignored except README.
- `data/raw/`, `data/interim/`, and `data/processed/` are local/regenerable data areas; do not assume source DOCX or generated corpus files are versioned.

## Methodology constraints

- Phase 2 builds the normative corpus: structured article/section segmentation, cleaning/normalization, metadata enrichment, then vector-ready artifacts.
- Phase 3 evaluation comes before agent development: Conjunto A is the expert gold standard for ARES calibration; Conjunto B is for development optimization.
- Consultation-agent stages are: base RAG, query understanding, retrieval improvement, business context, response validation/control.
- Each consultation-agent stage should compare three candidate techniques and choose using ARES metrics on Conjunto B.
- Evaluate RAG on context relevance, answer faithfulness, and answer relevance; include confidence intervals with ARES.
- Final system evaluation combines sessions from at least five risk-I companies, expert SST validation, and calibrated ARES evaluation.

## Design rules to preserve

- Apply YAGNI and KISS: do not add abstractions, wrappers, DTOs, helpers, interfaces, or placeholders for hypothetical future phases.
- Prefer local cohesion and readable pragmatic coupling over dogmatic layering.
- Group by workflow/domain first; split by technical concern only when it clearly improves traceability.
- Metadata extraction is deterministic: optional manifest + regex over cleaned Markdown + pipeline-calculated offsets/token counts. Do not use an LLM as the primary metadata extractor.

## Real entrypoints and gotchas

- DOCX ingestion: `python pipeline/ingestion/docx_to_markdown.py` reads `data/raw/*.docx`, writes Markdown and extracted HTML tables under `data/interim/`, and requires Pandoc plus `pypandoc`.
- Markdown cleaning: `python pipeline/cleaning/markdown_cleaner.py` reads `data/interim/*.md` and writes `data/processed/*.md`.
- Chunking CLI: `python -m pipeline.chunking.main --help`.
- Recommended chunking path: `build-parents`, `build-sliding-window`, `build-regex-constrained-semantic`, `audit-table-references`, `build-table-markdown`, `build-table-documents`.
- `build-regex-constrained-semantic` is the current recommended child-chunk strategy for SG-SST because it preserves exact offsets and legal traceability; keep `build-sliding-window` as a baseline and avoid pure `semantic_chunking` as final output.
- Table references use logical metadata such as `source_stem` + `table_index`; do not persist physical HTML paths in chunks or Chroma metadata.
- Vectorization: `python -m pipeline.vectorization.main --batch-size 8` indexes `data/processed/chunks/regex_constrained_semantic/chunks.jsonl` and `data/processed/table_documents.jsonl` into Chroma collection `sg_sst_base_rag` under `data/processed/chroma`.
- Vector ingestion uses upsert and does not delete stale Chroma records; remove/move `data/processed/chroma` for a clean rebuild.
- Base consultation CLI: set `GROQ_API_KEY` in the environment, then run `python -m agents.consulta_normativa.main`; it opens an existing Chroma collection and must not create an empty one during consultation.
- Default embedding model is `Qwen/Qwen3-Embedding-0.6B`; default Groq generation model is `openai/gpt-oss-120b` at temperature `0`.
- Optional table preview: `python -m pipeline.tables.table_jsonl_to_html`; the current output directory name is intentionally misspelled as `data/processed/tables_htlm`.
