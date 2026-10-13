# Local Environment Configuration

## Objective

Make the repository-local `.env` file supply the DeepSeek API key and browser origin without requiring manual shell exports, while preserving precedence for explicitly exported environment variables.

## Scope

- Keep sensitive values only in the ignored local `.env` file.
- Add the minimal dotenv dependency to `requirements.txt`.
- Load `.env` once at the runtime/application boundary before environment-backed configuration is consumed.
- Configure the existing CORS allowlist from `IP_ADDRESS` as an origin string.
- Add focused tests that avoid real RAG runtime and index construction.
- Do not touch unrelated generated data or decision-document changes.

## Stable Checklist

- [x] Inspect environment access, API entrypoints, CORS setup, tests, requirements, and ignore rules.
- [x] Confirm `.env` is ignored by Git.
- [x] Write the supplied sensitive values to the local `.env` without exposing them.
- [x] Declare the minimal dotenv dependency.
- [x] Load `.env` once before environment-backed configuration is consumed.
- [x] Read the CORS browser origin from `IP_ADDRESS` without host/port conversion.
- [x] Add focused dotenv precedence/load-location and configurable-CORS tests.
- [x] Run focused tests for changed modules.
- [x] Run `python -m compileall agents/consulta_normativa agents/api`.
- [x] Confirm `.env` is absent from `git status --short`.
- [x] Isolate test collection from the repository-local `.env` using controlled environment data and a mocked dotenv loader.

## Delegated Route Evidence

- Executor route: focused local-environment implementation with explicit allowed edit surfaces.
- Injected skills read before implementation:
  - `/home/leo/.agents/skills/python-code-style/SKILL.md`
  - `/home/leo/.agents/skills/clean-code/SKILL.md`
- CodeGraph inspected the environment access and API/CORS call paths before edits.
- Existing unrelated worktree changes were recorded and remain out of scope.
- The supplied local values are stored only in the ignored `.env` file.
- no commit: user requires explicit approval

## Acceptance Checks

- Starting the supported runtime/API from the repository loads `.env` before DeepSeek configuration is read.
- A real exported variable overrides the corresponding `.env` value.
- CORS accepts the origin supplied through `IP_ADDRESS`.
- Tests never read, print, or assert the real secret value.
- No real RAG runtime, Chroma collection, BM25 index, or model is constructed by focused tests.
- `.env` remains ignored and absent from Git status.
- No files outside the allowed edit surfaces are changed.

## Results

Implementation is complete. `python-dotenv` loads the repository-local `.env`
with `override=False`, and the API builds its sole CORS origin from
`IP_ADDRESS`.

Focused tests were invoked but could not be collected because the active
Python 3.14 environment does not have `fastapi` installed. A direct import
check also confirmed that the newly declared `python-dotenv` dependency is not
installed in this environment. These are environment dependency blockers, not
test assertion failures.

`python -m compileall agents/consulta_normativa agents/api` and
`git diff --check` passed. Git confirmed `.env` is ignored by the rule at
`.gitignore:10` and absent from `git status --short -- .env`.

The follow-up test-isolation fix now mocks dotenv loading before application
modules are imported and supplies a controlled `IP_ADDRESS` during collection.
Production still loads the repository-local `.env` once with `override=False`,
while focused tests use only temporary dotenv content or mocks.

Follow-up verification passed `python -m compileall agents/consulta_normativa
agents/api`, `git diff --check`, and static AST checks for the guarded imports,
single production load, and `override=False`. Focused unittest collection remains
blocked only because FastAPI is not installed in the active environment.
