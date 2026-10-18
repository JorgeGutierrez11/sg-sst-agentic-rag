# Python 3.12 Runtime Declaration

## Objective

Declare Python 3.12 as the project-level runtime and ensure the backend setup guide creates its virtual environment with that interpreter.

## Scope

- Add `.python-version` with the exact project runtime `3.12`.
- Update only the virtual-environment creation command in `GUIA_EJECUCION_BACKEND.md`.
- Do not add packaging metadata, Docker or CI configuration, lockfiles, dependencies, or application-level version checks.
- Do not modify historical task or decision documents.
- Preserve all pre-existing unrelated worktree changes.

## Delegated Route

- Route: focused implementation with explicit allowed edit surfaces.
- Skill loaded before implementation: `/home/leo/.agents/skills/python-code-style/SKILL.md`.
- Skill resolution: `paths-injected`.

## Checklist

- [x] Create `.python-version` containing exactly `3.12` with a trailing newline.
- [x] Change `python3 -m venv .venv-rag` to `python3.12 -m venv .venv-rag` in the backend execution guide.
- [x] Verify the exact contents and constrained documentation change.
- [x] Probe `python3.12 --version` without changing the environment.
- [x] Run `git diff --check`.
- [x] Confirm no files outside the allowed edit surfaces were changed by this task.

## Acceptance Checks

- `.python-version` contains exactly `3.12` followed by one newline.
- The backend guide uses `python3.12 -m venv .venv-rag` and preserves unrelated content.
- No prohibited project configuration or metadata is created.
- Validation records whether the Python 3.12 executable is available locally.
- `git diff --check` passes.

## No-Commit Policy

Do not stage or commit any changes. The user requires explicit approval before any commit.

## Results

Implementation is complete. Exact-content checks passed for `.python-version`,
the backend guide contains the single required command replacement, and
`git diff --check` passed.

The read-only `python3.12 --version` probe reported `command not found`. This is
an environment blocker for running Python 3.12 locally, not a reason to change
the requested project declaration.

Only the three allowed edit surfaces were changed by this task. Pre-existing
unrelated changes remain untouched. Nothing was staged or committed.
