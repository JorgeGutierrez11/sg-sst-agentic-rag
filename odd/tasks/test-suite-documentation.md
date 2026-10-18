# Test-Suite Documentation Task

## Scope

- Create `docs/testing.md` as a comprehensive, evidence-based inventory of the repository test suites.
- Cover execution commands, module purposes, test doubles and fixtures, coverage boundaries, prompt contracts, and extension guidance.
- Edit only this tracker and `docs/testing.md`.

## Delegated Route

- Route: documentation-only implementation.
- Skills: `cognitive-doc-design` and `python-code-style` loaded from the user-provided paths.
- Evidence: use the completed test-suite mapping as the primary source; inspect exact repository files only where needed to resolve ambiguity.

## Checklist

- [x] Create the ODD tracker before the main documentation.
- [x] Write `docs/testing.md` in English using the required section structure.
- [x] Include all 84 test modules, grouped by subsystem and purpose.
- [x] Document prerequisites and supported execution commands without claiming a green build.
- [x] Describe fixtures, fakes, optional BM25 skipping, and untested boundaries.
- [x] Explain the current inline-reference prompt contract.
- [x] Validate Markdown structure and required content.
- [x] Run `git diff --check`.
- [x] Update this tracker and its Engram mirror with validation results.

## Acceptance Checks

- `docs/testing.md` exists at the exact requested path.
- The document contains every required section and accounts for 13 pipeline, 33 consultation/RAG, 1 unified API, and 37 diagnosis test modules.
- Commands distinguish documented `unittest` usage from the inferred, not-yet-documented diagnosis `pytest` command.
- The status disclaimer says the document is an inventory, not a current green-build certificate.
- Only the two allowed Markdown files are changed by this task.
- `git diff --check` succeeds.

## No-Commit Policy

Do not create, amend, or push a commit for this task.

## Validation Status

- Markdown structure/content check: passed; 12 required headings present.
- Inventory count check: passed; pipeline 13, consultation/RAG 33, unified API 1, diagnosis 37 (84 total).
- Required disclaimer, diagnosis-command qualification, BM25 skip behavior, and prompt-reference contract: present.
- `git diff --check`: passed.
- Full test suites: not run, by policy.
- Commit: not created, by policy.
