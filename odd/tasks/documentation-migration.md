# Documentation Migration

Objective: implement and correct `docs/documentation-migration-plan.md`, leaving root `README.md` as the canonical entry and every doc classified. Branch: `dev` (no commits: user memory requires explicit permission). Delivery: single working-tree change. Test runner: N/A (documentation); checks are a scratch link checker and `git diff --check`.

## Specs

- S1: "Implementar el plan y organizar toda la docuementacion."
- S2: "Si vez huecos o fallas en el plan, arreglalo y luego implementalo."
- S3: "Salida: Resumen general de los cambios implementado."
- S4 (prior session policy): only `AGENTS.md` and `README.md` remain as root Markdown; root `README.md` is the main entry; no `docs/README.md`.

## Tasks

| ID | Specs | Route | Status |
|---|---|---|---|
| T1 | S2 | inline | done |
| T2 | S1 | delegated explore x3 (mapping trigger: ~35 docs, ~9k lines vs code) | done |
| T3 | S1,S4 | inline: `git mv` relocations + inbound link updates | done |
| T4 | S1 | inline: metadata header on every doc | done |
| T5 | S1 | inline: reconcile Current docs with explorer findings; new `docs/reference/api.md` | done |
| T6 | S1,S4 | inline: rewrite root `README.md`, `docs/guia-carpetas.md`, `docs/mapa-fases-tesis.md`, `agents/README.md` | done |
| T7 | S1 | inline: link check + `git diff --check` | done |

## Log

- L1 (2026-10-18, user): "Ahora necesito que analices este plan para mejorar y organizar la docuemacion @docs/documentation-migration-plan.md . Tarea: * Implementar el plan y organizar toda la docuementacion. * Si vez huecos o fallas en el plan, arreglalo y luego implementalo. Salida: * Resumen general de los cambios implementado."
- L2: The request to implement is taken as the explicit approval the plan required for every relocation batch listed in its updated inventory.
- L3: Explorer findings: `agents/shared/` and `pipeline/chunking/core/` do not exist; reranker is `SINAI/ALIA-MrBERT-es-legal-administrative-reranker` (also stale in AGENTS.md); graph wires profile, long-term memory, query expansion, hybrid RRF (60/source → 16), rerank (→ 8), parents, grading, table complement; fallback calls the LLM. Unwired: rewrite, multi-query, self-refine, sufficient-context gate, summarization and full-conversation memory.
- L4: Verification: scratch link checker over 48 maintained Markdown files → broken=0; `git diff --check` clean; every `docs/**/*.md` carries a Status block; root holds only `AGENTS.md` and `README.md`; no `docs/README.md`. All relocations via `git mv` (rename detection confirmed). No commits (user memory rule).
