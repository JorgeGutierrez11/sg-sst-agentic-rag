# OpenCode Instructions

This is not a git repo and no project-level dependency, test, lint, or typecheck manifest is currently present; do not invent commands.

## Project boundary

- The project is a thesis RAG system for SG-SST assistance and compliance diagnosis for Colombian MiPymes classified as risk level I.
- The plan of record is `docs/EISI_2026-04-09_14-25-36_pg1409.pdf`; use its methodology over stale prose when phases conflict.
- `README.md` references `docs/arquitectura.md`, but that file is currently missing.

## Methodology constraints

- Keep the scope anchored to official SG-SST sources listed in the plan: Decreto 1072/2015, Resolución 0312/2019, Resolución 2346/2007, Resolución 1401/2007, Ley 1562/2012, Resolución 2013/1986, Ley 1010/2006, and Decreto 768/2022.
- Phase 2 builds the normative corpus: structured segmentation by article/section, text cleaning/normalization, metadata enrichment, then vector-ready artifacts.
- Phase 3 evaluation comes before agent development: create expert-supported datasets, with Conjunto A as gold standard for ARES calibration and Conjunto B for optimization during development.
- The consultation agent is developed iteratively in five stages: base RAG, query understanding, retrieval improvement, business context, then response validation/control.
- Each consultation-agent stage should compare three candidate techniques and choose by ARES metrics on Conjunto B.
- Evaluate RAG on context relevance, answer faithfulness, and answer relevance; include confidence intervals when using ARES.
- Final system evaluation combines user sessions from at least five risk-I companies, expert SST validation, and calibrated ARES evaluation.

## Directory boundaries

- Put offline corpus transformation code in `pipeline/`; put runtime LLM agent logic in `agents/`; put user-facing API/UI code in `app/`; put evaluation definitions/results in `evaluation/`; put thesis docs and decisions in `docs/`.
- `data/raw/` holds original DOCX normative sources; `data/interim/` and `data/processed/` are derived pipeline artifacts.
- `.gitignore` ignores all `data/raw/`, `data/interim/`, and `data/processed/` except `.gitkeep`, so do not assume local DOCX or generated corpus files are versioned.
- `scripts/` is for one-off operational utilities or migrations; the two current processing scripts live under `pipeline/`, not `scripts/`.

## Design principles for this project

- Apply YAGNI: do not create abstractions, wrappers, interfaces, DTOs, or helper layers for hypothetical future needs. Build only what the current phase requires.
- Apply KISS: prefer the clearest linear implementation over academically elegant but fragmented code. If cohesive logic is readable in one module, do not split it across multiple files.
- Prefer local cohesion over absolute modular separation: keep tightly related functions together when splitting them would make debugging or traceability harder.
- Balance coupling and readability: do not apply Clean Code dogmatically. If decoupling requires redundant mappers, DTOs, or indirection that hides the flow, choose a compact locally coupled design.
- Prefer feature-driven structure over technical micro-packages. Group code by the workflow/domain relationship first, then by technical concern only when it clearly improves readability.

## Pipeline architecture decisions

- `pipeline/chunking/` uses a compact feature-driven layout:
  - `core/` for local infrastructure such as CLI, config, and JSONL persistence.
  - `structural_analysis/` for normative structure detection, legal regex patterns, boundaries, and metadata inference.
  - `hierarchical_splitter/` for parent/child chunk domain models, parent building, token counting, and future child splitting.
- Keep `pipeline/chunking/main.py` as the chunking entrypoint and orchestrator. Current Phase 1 behavior exposes `build-parents` only.
- Do not reintroduce a dedicated Markdown/legal pattern analysis module unless repeated automated analysis becomes necessary; inspect cleaned Markdown directly and keep regex simple and evidence-based.
- Metadata extraction is deterministic: optional source manifest for controlled document metadata, regex over cleaned Markdown for structural metadata, and pipeline-calculated offsets/token counts. Do not use an LLM as the primary metadata extractor.
- Child chunking strategies are future phases. Do not add strategy abstractions or placeholders until there is real behavior to implement.

## Current executable entrypoints

- `pipeline/ingestion/docx_to_markdown.py` reads DOCX files from `data/raw` and writes markdown plus extracted HTML tables to `data/interim`.
- `pipeline/cleaning/markdown_cleaner.py` has an outdated `__main__` input path (`../fase1_parsing/data/processed`); update or pass paths through code before using it in the new structure.
- `python -m pipeline.chunking.main build-parents` builds parent chunks from cleaned Markdown for the chunking Phase 1 pipeline.
- `pipeline/ingestion/docx_to_markdown.py` imports `pypandoc` and depends on Pandoc availability, but no dependency manifest is present.

## Agent implementation conventions

- `agents/shared/` is for common LLM clients, retrievers, prompts, adapters, and utilities reused by both agents.
- `agents/consulta_normativa/` is the Phase 4 Block A consultation agent; existing guidance says represent the five stages with git tags, not duplicated `etapa_*` folders.
- `agents/diagnostico_cumplimiento/` is the Phase 4 Block B diagnostic agent; it must produce a requirement-by-requirement compliance report and an executive summary of critical gaps and priority actions.
- `app/backend/` should expose both agents through a Python REST API; `app/frontend/` should provide the React prototype UI.

## Evaluation and privacy

- `evaluation/instruments/` stores expert rubrics, user surveys, protocols, consent, and sampling criteria; results do not belong there.
- `evaluation/results/` stores processed or anonymized evaluation outputs, including ARES runs, expert validation, user-study summaries, and integrated reports.
- `evaluation/resultados_usuarios/` is confidential raw user-interaction data; anonymize company-identifying data and confirm consent before storing anything there.
