# Phase 7: Unified Offline Corpus Pipeline Implementation Plan

> **For implementation workers:** Read this entire document through `## Log` before editing. Implement task-by-task, preserve the existing per-stage CLIs, and report the covered specs.

**Status (2026-10-18):** Implemented. Tasks 1-8 are complete and verified with fake stage operations, temporary project roots, and an independent verifier (no blockers). The only pending item is the manual smoke test against the real corpus, which requires explicit authorization and a stopped API.

**Goal:** Replace the manual offline corpus rebuild sequence with two explicit commands that build and validate the offline ingestion pipeline while reusing existing stage implementations.

**Architecture:** Add a thin standard-library orchestration layer that invokes the existing path-driven pipeline APIs in an isolated staging workspace. It emits a typed result for every stage, validates the staged corpus before publishing it, and promotes only the managed canonical artifacts after every blocking check succeeds.

**Tech stack:** Python 3.14, standard-library `argparse`, existing Pandoc/pypandoc integration, ChromaDB, BM25S, `unittest`.

## Global Constraints

- Phase 6 of `docs/plans/plan-docker.md` remains deferred and is out of scope.
- Do not add dependencies, a task runner, a lockfile, CI configuration, formatters, or linters.
- Preserve existing individual pipeline CLIs, especially `pipeline/chunking/cli.py`; the unified CLI complements them.
- Reuse existing stage functions rather than reimplementing ingestion, cleaning, chunking, table processing, Chroma, or BM25 logic.
- New code comments must be one concise technical sentence of at most two lines; preserve existing comments unless behavior requires a change.
- Use Conventional Commits in English, never add AI attribution, and never push without explicit authorization.
- The initial promotion policy requires the unified API to be stopped; zero-downtime publication is a separate future release-pointer refactor.
- Run verification with the project environment (`.venv/bin/python`); the consultation suite is runnable there and must pass.

---

## Operator Contract

The module name makes the operational scope explicit: it rebuilds and validates the **offline corpus ingestion pipeline**, not the online RAG runtime.

```bash
# Rebuild and publish the complete offline ingestion corpus.
python -m pipeline.offline_corpus build

# Validate the currently published offline ingestion corpus without rebuilding it.
python -m pipeline.offline_corpus validate
```

Supported `build` options:

```bash
python -m pipeline.offline_corpus build --batch-size 8 --json --keep-workdir
```

| Option | Purpose |
|---|---|
| `--batch-size <positive-int>` | Chroma embedding batch size; defaults to the existing vectorization default. |
| `--json` | Emit one JSON event per lifecycle transition to standard output. |
| `--keep-workdir` | Preserve the isolated staging workspace after success or failure for diagnosis. |

### Human-readable stage output

The command must write progress to standard error. It must never require the operator to infer the active phase from third-party logs.

```text
Preflight started
Preflight completed
[1/10] DOCX ingestion started
[1/10] DOCX ingestion completed — 8 documents, 12 extracted tables
[2/10] Markdown cleanup completed — 8 documents
...
[9/10] BM25 indexing completed — 1,245 records
[10/10] Corpus validation completed — Chroma and BM25 agree
Publication started
Publication completed
Offline corpus build published successfully
```

Preflight (workspace preparation and the leftover-backup check) and publication are lifecycle phases, not build stages: they are rendered without a `[n/10]` counter.

Every failure must identify the failed stage, preserve its causal exception, and return a non-zero exit code. The failure is printed once, followed by the publication state.

```text
[6/10] Table Markdown conversion failed
Cause: Failed to convert table HTML to Markdown: .../table_3.html
The published corpus was not modified.
```

When publication fails and the rollback succeeds, the last line is `The previous published corpus was restored.`. When the rollback itself fails, the last line names the retained backup directory so the operator can restore it manually.

`validate` reports the verified counts on success:

```text
Offline corpus validation completed — 412 parents, 1,245 records; Chroma and BM25 agree
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Build published, or validation passed. |
| `1` | Unexpected error; the exception type and message are printed. |
| `2` | Expected failure: argument, preflight, stage, validation (`build` or `validate`), or publication. |

### Stage contract

| # | Stage name | Existing reusable operation | Blocking success condition |
|---|---|---|---|
| 1 | `docx_ingestion` | `convert_docx_directory_to_markdown()` | Every DOCX has no `parsing_errors`. |
| 2 | `markdown_cleanup` | `clean_markdown_directory()` | Cleaned Markdown exists for every ingested document. |
| 3 | `parent_chunking` | `write_parent_chunk_output()` | Non-empty `parents.jsonl`; table references exist. |
| 4 | `regex_child_chunking` | `write_regex_constrained_semantic_child_output()` | Non-empty canonical child JSONL. |
| 5 | `table_reference_audit` | `audit_table_references()` | No missing referenced table HTML. Orphaned tables are reported as warnings. |
| 6 | `table_markdown_conversion` | `convert_table_html_batch()` | Every extracted HTML table has a staged Markdown representation. |
| 7 | `table_document_build` | `write_table_documents()` | Staged `table_documents.jsonl` is present and valid. |
| 8 | `chroma_indexing` | `ingest_base_rag_documents()` | A new staged collection was built without skipped source records. |
| 9 | `bm25_indexing` | `ingest_sparse_bm25_documents()` | A new staged BM25 index was built without skipped source records. |
| 10 | `corpus_validation` | `pipeline/artifact_validation.py` | Parent-child, Chroma, and BM25 identities and counts agree. |

## Publication and Failure Policy

1. `build` creates `data/.pipeline-work/<run-id>/` outside the published artifact roots. `data/.pipeline-work/` and `data/.pipeline-backup/` are git-ignored.
2. Each stage receives staging `Path` values. No stage writes to published `data/interim/` or `data/processed/` locations during the build.
3. A stage failure stops later stages immediately. The command reports the named stage and leaves published artifacts untouched.
4. A successful staging build runs all validation gates before publication.
5. Promotion replaces **only the managed artifact set** below, entry by entry. It never moves or deletes the `data/interim/` or `data/processed/` roots, and every unmanaged entry stays in place.
6. Before promotion, each existing managed entry is moved to `data/.pipeline-backup/<run-id>/`, which is **outside** the staging workspace. Workspace cleanup must never delete a backup.
7. If promotion fails for any reason, including `KeyboardInterrupt` (`BaseException`), remove the partially promoted entries, restore the backup, then re-raise. Report `publication` as the failed lifecycle phase.
8. The backup is removed only after the complete promotion succeeds. If the restore fails, keep the backup, report its path, and exit `2`. A failure to remove the backup after a successful promotion is a warning, not a build failure.
9. A new `build` always starts from a clean workspace. Do not automatically retry Pandoc, model downloads, embeddings, or index writes.
10. `validate` only reads published artifacts and never changes them.

### Managed artifact set

| Root | Managed (replaced on publication) | Unmanaged (never touched) |
|---|---|---|
| `data/interim/` | Top-level `*.md` files, `tables/` | Everything else |
| `data/processed/` | Top-level `*.md` files, `chunks/parents.jsonl`, `chunks/regex_constrained_semantic/`, `tables_markdown/`, `table_documents.jsonl`, `chroma/`, `bm25/` | `chunks/sliding_window/`, `chunks/semantic_chunking/`, `chunks/comparison/`, `tables_htlm/`, `metadata/`, everything else |

Top-level `*.md` files are replaced as one set, so a removed source document does not leave stale interim or cleaned Markdown behind. `metadata/source_manifest.json` is an optional build input copied into staging; it is never promoted.

The promotion spans multiple entries and is not one filesystem-atomic operation. Operators must stop the API before `build` publishes. A versioned release root plus an atomic runtime pointer is explicitly deferred.

## Design Boundaries

| Component | Responsibility | Must not do |
|---|---|---|
| `pipeline/offline_corpus.py` | Parse commands, map domain failures to exit codes, render human/JSON progress. | Implement corpus transformations or inspect Chroma internals. |
| `pipeline/offline_orchestration.py` | Build staging paths, execute ordered stages, retain stage results, validate and promote. | Duplicate existing pipeline stage logic. |
| `pipeline/artifact_validation.py` | Validate artifact existence, parent-child linkage, source IDs, and Chroma/BM25 consistency. | Start the online RAG runtime or publish artifacts. |
| Existing stage modules | Transform input paths into output paths. | Know about orchestration state or published-artifact rollback. |

## Implementation Review (2026-10-18)

Review of the uncommitted working tree against this plan. Findings are referenced by the correction tasks.

| ID | Severity | Location | Finding |
|---|---|---|---|
| R1 | Critical | `offline_orchestration.py` `_promote` | Promotion moves the complete `data/interim/` and `data/processed/` roots. Unmanaged artifacts the build never regenerates (`chunks/sliding_window`, `chunks/semantic_chunking`, `chunks/comparison`, `tables_htlm`; 92 tracked files) would be deleted by a successful build. |
| R2 | Critical | `offline_orchestration.py` `_promote`, `build_offline_corpus` | The backup lives in `<workspace>/rollback`, and the `finally` block removes the workspace. A failed restore or a `KeyboardInterrupt` during promotion (not caught by `except Exception`) deletes the only copy of the published corpus. |
| R3 | High | `artifact_validation.py` `validate_index_consistency` | The extracted validator changed the runtime message from `Missing parent chunks: 1 of 2 child chunks reference…` to `Missing parent chunks: 1 child chunks reference…`. `agents/consulta_normativa/tests/test_langchain_rag_main.py` fails. |
| R4 | High | `offline_corpus.py` `main` | `validate` raises `ArtifactValidationError`, which reaches the generic handler and exits `1` instead of `2`. |
| R5 | Medium | `pipeline/tests/` | Missing plan tests: ten-stage order and staging paths with fakes, no production writes before validation, promotion success/restore/`--keep-workdir`, human messages for all stages, exit codes `1` and `2`, required subcommand and unknown options, count-only index mismatch. Publication (R1, R2) has no coverage. |
| R6 | Medium | `offline_corpus.py` | Publication renders as `[11/10]`; failures print the stage twice; the `The published corpus was not modified.` line is missing; `validate` prints no counts. |
| R7 | Medium | `docs/operations/corpus-build.md`, `docs/plans/plan-docker.md` | The runbook documents the R1 behavior ("publication replaces the complete … roots"); `plan-docker.md` marks Phase 7 as completed. |
| R8 | Low | `.gitignore` | `data/.pipeline-work/` is not ignored; `--keep-workdir` or a crash leaves untracked data in `git status`. |
| R9 | Low | `offline_orchestration.py` | A workspace-preparation error is reported as `publication`; a backup-removal error after a successful promotion is reported as a failed build. Unused `ArtifactValidationError` import. |
| R10 | Low | `docs/operations/*.md` | The edited runbooks were retitled and partially rewritten from Spanish into English, which is not a requested change. Restore the original Spanish wording and add only the new routine-operation sections, in Spanish. |

## Tasks

### Task 1: Define orchestration outcomes and stage progress

**Files:**
- Create: `pipeline/offline_orchestration.py`
- Create: `pipeline/tests/test_offline_orchestration.py`

**Interfaces:**
- Produces: `StageName`, `StageResult`, `BuildPaths`, `OfflineBuildError`, and an injectable stage-progress callback.
- Consumes: Explicit `Path` inputs and the existing public pipeline functions.

- [x] Write unit tests proving stage events are ordered, include stage names, and distinguish completed from failed outcomes.
- [x] Implement immutable stage and build-path value objects that map every input, staging, published, and rollback artifact path.
- [x] Implement a single stage runner that emits `started`, `completed`, or `failed` exactly once per executed stage and wraps failures in `OfflineBuildError(stage_name, cause)`.
- [x] Verify a failed stage stops the sequence and no later stage is called.
- [x] Committed in the L9 slices: `cde7323` (C1), `90546c1` (C2), `0cab2c4` (C3), and the C4 documentation commit.

### Task 2: Orchestrate the canonical build in staging

**Files:**
- Modify: `pipeline/offline_orchestration.py`
- Modify: `pipeline/tests/test_offline_orchestration.py`

**Interfaces:**
- Consumes: `BuildPaths`, stage runner, and the nine existing reusable stage functions named in the stage contract.
- Produces: `build_offline_corpus(raw_docx_dir, published_root, batch_size, keep_workdir, progress_callback)`.

- [x] Add failing tests with fakes for all existing stage functions; assert the exact ten-stage order and that every function receives staging paths.
- [x] Implement DOCX result inspection that treats any `ParsedDocument.parsing_errors` as a `docx_ingestion` failure before cleanup begins.
- [x] Invoke only the canonical parent and regex-constrained semantic child builders; do not run sliding-window or pure-semantic baselines.
- [x] Treat missing referenced tables, empty required artifacts, and skipped vector/sparse source records as blocking failures; emit orphaned table warnings without failing the build.
- [x] Run staging corpus validation before publication.
- [x] Verify no test or implementation path writes to production artifact directories before all stages and validation pass.
- [x] Committed in the L9 slices: `cde7323` (C1), `90546c1` (C2), `0cab2c4` (C3), and the C4 documentation commit.

### Task 3: Extract neutral corpus-artifact validation

**Files:**
- Create: `pipeline/artifact_validation.py`
- Create: `pipeline/tests/test_artifact_validation.py`
- Modify: `agents/consulta_normativa/langchain_rag/main.py`
- Modify: the existing consultation-runtime test module that covers startup artifact validation

**Interfaces:**
- Produces: `validate_corpus_artifacts(parents_path, children_path, table_documents_path, chroma_path, bm25_path)` and structured validation failures.
- Consumes: Canonical JSONL artifacts and existing Chroma/BM25 read APIs.

- [x] Write failing tests for a missing required artifact, unresolved child `parent_id`, mismatched source ID sets, and mismatched record counts.
- [x] Move only pure artifact-consistency logic from the online runtime into the new pipeline-neutral module.
- [x] Keep online runtime error behavior compatible by delegating its existing startup check to the extracted validator.
- [x] Verify the new validator does not initialize an LLM, build an online graph, or mutate either index.
- [x] Committed in the L9 slices: `cde7323` (C1), `90546c1` (C2), `0cab2c4` (C3), and the C4 documentation commit.

### Task 4: Add the explicit offline corpus CLI

**Files:**
- Create: `pipeline/offline_corpus.py`
- Create: `pipeline/tests/test_offline_corpus.py`

**Interfaces:**
- Consumes: `build_offline_corpus()` and `validate_corpus_artifacts()`.
- Produces: `python -m pipeline.offline_corpus build` and `python -m pipeline.offline_corpus validate`.

- [x] Write parser tests that require `build` or `validate`, reject unknown options, and reject non-positive `--batch-size` before loading models.
- [x] Write output tests for all ten successful stage messages, a named failure message with its cause, JSON lifecycle events, and exit codes `0`, `1`, and `2`.
- [x] Implement `argparse` subcommands with the exact operator contract shown above.
- [x] Render human progress to standard error and newline-delimited JSON event objects to standard output only when `--json` is selected.
- [x] Map expected preflight, stage, validation, and publication failures to exit code `2`; map unexpected errors to `1` without hiding the exception context.
- [x] Verify `validate` invokes no staging, transformation, embedding, index-writing, or publication function.
- [x] Committed in the L9 slices: `cde7323` (C1), `90546c1` (C2), `0cab2c4` (C3), and the C4 documentation commit.

### Task 5: Publish safely and document the operating procedure

**Files:**
- Modify: `pipeline/offline_orchestration.py`
- Modify: `pipeline/tests/test_offline_orchestration.py`
- Modify: `docs/operations/corpus-build.md`
- Modify: `docs/operations/vectorization.md`
- Modify: `docs/operations/bm25-sparse-retrieval.md`
- Modify: `docs/plans/plan-docker.md`

**Interfaces:**
- Consumes: A fully validated staging workspace.
- Produces: A rollback-capable publication operation and the operator documentation for the two commands.

- [x] Write tests covering successful promotion, no promotion after validation failure, restoration after promotion failure, and `--keep-workdir` retention.
- [x] Implement backup-and-restore publication for the complete set of offline artifacts: interim Markdown/tables and processed Markdown/chunks/table documents/Chroma/BM25.
- [x] Document that operators stop the API before `build`, use `validate` after promotion or diagnosis, and retain individual commands only for stage-level debugging.
- [x] Update vectorization and BM25 runbooks to make in-place rebuilds an advanced debugging path rather than the routine operating procedure.
- [x] Update `plan-docker.md` only to record Phase 7 completion/status; do not introduce Docker assets or implement Phase 6.
- [x] Committed in the L9 slices: `cde7323` (C1), `90546c1` (C2), `0cab2c4` (C3), and the C4 documentation commit.

### Task 6: Correct publication safety and contract regressions

**Findings:** R1, R2, R3, R4, R8, R9.

**Files:**
- Modify: `pipeline/offline_orchestration.py`
- Modify: `pipeline/offline_corpus.py`
- Modify: `pipeline/artifact_validation.py`
- Modify: `pipeline/tests/test_offline_orchestration.py`
- Modify: `pipeline/tests/test_offline_corpus.py`
- Modify: `.gitignore`

**Risk:** item 1 (published corpus data). Commit this task alone so native review can take it by itself.

- [x] RED: add a publication test over a temporary project root with unmanaged entries (`chunks/sliding_window/x.jsonl`, `tables_htlm/x.html`, `metadata/source_manifest.json`) and a stale top-level `*.md`; assert that after a successful build the unmanaged entries are byte-identical, the stale Markdown is gone, and every managed entry holds the staged content.
- [x] RED: add a test where the second managed move fails; assert the published tree is byte-identical to the pre-build tree and the backup directory is removed after a successful restore.
- [x] RED: add a test where promotion raises `KeyboardInterrupt`; assert the published tree is restored and the exception propagates.
- [x] RED: add a test where the restore also fails; assert `data/.pipeline-backup/<run-id>/` still exists after workspace cleanup and the error names that path.
- [x] Replace the root-level `targets` in `_promote` with the managed artifact set from the policy above, moved entry by entry.
- [x] Move `BuildPaths.rollback_root` to `project_root / "data" / ".pipeline-backup" / <run-id>`; workspace cleanup must not reach it.
- [x] Catch `BaseException` during promotion to restore, then re-raise; keep the backup when the restore fails; downgrade a failure to remove the backup after a successful promotion to a warning event.
- [x] Wrap workspace preparation failures as a `preflight` failure instead of `publication`, and remove the unused `ArtifactValidationError` import.
- [x] Restore the runtime message `Missing parent chunks: {missing} of {with_parent_id} child chunks reference a parent not found in parent chunks` in `validate_index_consistency`; `agents/consulta_normativa/tests/test_langchain_rag_main.py` must pass unchanged.
- [x] Map `ArtifactValidationError` raised by `validate` to exit code `2`; add RED tests for `validate` exit `2` and for an unexpected error exiting `1` with its type in the message.
- [x] Add `data/.pipeline-work/` and `data/.pipeline-backup/` to `.gitignore`.
- [x] Committed in the L9 slices: `cde7323` (C1), `90546c1` (C2), `0cab2c4` (C3), and the C4 documentation commit.

### Task 7: Complete the missing test coverage and operator output

**Findings:** R5, R6.

**Files:**
- Modify: `pipeline/offline_corpus.py`
- Modify: `pipeline/tests/test_offline_orchestration.py`
- Modify: `pipeline/tests/test_offline_corpus.py`
- Modify: `pipeline/tests/test_artifact_validation.py`

- [x] Add a fake-operations build test asserting the exact ten-stage order, that every operation receives paths under the staging workspace, and that no published path is written before `corpus_validation` completes.
- [x] Add build tests for a missing referenced table, an empty required artifact, and skipped Chroma or BM25 records failing their named stage; add one test proving orphaned tables only produce a warning.
- [x] Add a validation test for matching ID sets with a differing BM25 record count (duplicate IDs) and one for a count-only Chroma mismatch.
- [x] Add parser tests for a missing subcommand and an unknown option (exit `2`).
- [x] Render publication without the `[n/10]` counter; print each failure once followed by `The published corpus was not modified.` or the restore/backup line from the operator contract.
- [x] Print the verified parent and record counts on a successful `validate`.
- [x] Add output tests for all ten stage messages, the failure message with its cause, and the publication lines.
- [x] Committed in the L9 slices: `cde7323` (C1), `90546c1` (C2), `0cab2c4` (C3), and the C4 documentation commit.

### Task 8: Reconcile operator documentation

**Findings:** R7, R10.

**Files:**
- Modify: `docs/operations/corpus-build.md`
- Modify: `docs/operations/vectorization.md`
- Modify: `docs/operations/bm25-sparse-retrieval.md`
- Modify: `docs/plans/plan-docker.md`

- [x] Restore the original Spanish titles and existing sections; keep the new routine-operation and debugging sections, written in Spanish.
- [x] Document the managed artifact set, that unmanaged baselines and previews are preserved, the backup location, and the manual recovery step when the restore fails.
- [x] Set the Phase 7 status in `plan-docker.md` to completed only after Tasks 6-7 pass and the manual smoke test succeeds; until then record it as in progress. *(Recorded as in progress.)*
- [x] Committed in the L9 slices: `cde7323` (C1), `90546c1` (C2), `0cab2c4` (C3), and the C4 documentation commit.

## Verification

Run every command with `.venv/bin/python`. Run the focused tests first:

```bash
python -m unittest \
  pipeline.tests.test_offline_orchestration \
  pipeline.tests.test_artifact_validation \
  pipeline.tests.test_offline_corpus
```

Then run affected existing contracts:

```bash
python -m unittest \
  pipeline.tests.test_tables_main \
  pipeline.tests.test_table_references \
  pipeline.tests.test_table_markdown \
  pipeline.tests.test_table_documents \
  pipeline.tests.test_vectorization_documents \
  pipeline.tests.test_vectorization_chroma_store \
  pipeline.tests.test_sparse_indexing_ingest \
  pipeline.tests.test_sparse_indexing_bm25_store

python -m unittest discover -s agents/consulta_normativa/tests
python -m compileall pipeline agents
```

The consultation suite must pass; on 2026-10-18 it failed one test (`test_langchain_rag_main`, R3).

Manual smoke test, only with a deliberately authorized corpus rebuild, the API stopped, and after Task 6:

```bash
git status --short data/   # record the baseline
python -m pipeline.offline_corpus build --batch-size 8
python -m pipeline.offline_corpus validate
git status --short data/   # unmanaged entries must not appear as deleted
```

Expected result: all ten named stages report success, the build reports publication success, `validate` confirms the published artifact identities and counts, and no unmanaged artifact is deleted.

## Acceptance Checklist

- [x] Operators use no more than the two documented unified commands for routine offline corpus work.
- [x] Every pipeline phase visibly reports start, completion, or named failure.
- [x] A failed build never publishes partial or mixed-generation artifacts.
- [x] An interrupted or failed publication never loses the previous published corpus.
- [x] A successful build never deletes artifacts outside the managed artifact set.
- [x] Removed source documents cannot remain as stale Chroma records or stale Markdown after a successful rebuild.
- [x] The canonical regex-constrained semantic corpus remains the only production child-chunk output.
- [x] Existing individual stage CLIs remain available for debugging.
- [x] The online runtime startup validation messages are unchanged.
- [x] Phase 6 Docker work has not been changed.

## Log

- L1 (2026-10-18): The user requested analysis and a refactoring plan to reduce manual offline corpus processing to one or two unified commands, preferably by executing existing scripts.
- L2 (2026-10-18): The user deferred Phase 6 of `docs/plans/plan-docker.md` to prioritize this Phase 7 operational simplification.
- L3 (2026-10-18): The user required command names that explicitly communicate offline ingestion and validation, plus per-phase completion/failure feedback.
- L4 (2026-10-18): Tasks 1-5 were implemented without commits, as the user requested ("Implementalo sin hacer commits aun.").
- L5 (2026-10-18): Implementation review found R1-R10 (see `## Implementation Review`). The user requested: "Edita el plan existente, en base a lo que hay, las mejoras y correcciones requeridas." Task checkboxes now reflect observed state; Tasks 6-8 hold the corrections. Next step: Task 6.
- L6 (2026-10-18): The user confirmed no test rebuilds the corpus and requested: "ya con eso claro, implementa el plan". Added safeguard: `build_offline_corpus` requires `project_root` and `operations` (no defaults); only the CLI passes the real values. `StageOperations` also injects `validate_corpus`.
- L7 (2026-10-18): Tasks 6-8 implemented inline. Additional decisions: a leftover non-empty `data/.pipeline-backup/` blocks a new build in `preflight`; the unused runtime `describe_ids` was removed; `docs/testing.md` and `AGENTS.md` list the new modules and commands. Evidence: 33 focused, 163 pipeline, 196 consultation, and 14 API tests pass with `.venv/bin/python`; `compileall` passes; `git status data/` is clean; mutants for whole-root promotion, in-workspace backup, and `Exception`-only restore each fail their test.
- L8 (2026-10-18): Independent verifier (scratch copies, fake stages): no blockers. Advisories accepted: BM25 records without `id` now raise a validation error instead of `KeyError`; an interrupt during a failed restore exits `2` with the backup retained; cross-device partial moves are theoretical because staging and backup live under `data/`.
- L9 (2026-10-18): Commits slice the uncommitted work into C1 validation refactor, C2 staged orchestration (risk item 1, alone), C3 CLI, and C4 documentation, replacing the per-task commit lines above.
