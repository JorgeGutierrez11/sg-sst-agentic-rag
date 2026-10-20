# Liveness and Readiness Separation

## Objective

Separate process liveness from service readiness in the unified FastAPI application without changing any functional agent endpoint contract.

## Scope

- Preserve `GET /health` as a dependency-free liveness endpoint returning `200 {"status":"ok"}`.
- Add `GET /health/ready` for readiness of both `QueryService` and `DiagnosticService`.
- Track readiness explicitly across lifespan startup and shutdown.
- Return a sanitized `503` when readiness state or either service is unavailable.
- Add focused fake-based tests and update only the relevant operations guidance.
- Do not add `/health/live`, new schemas, or service/runtime dependency checks.

## Stable Checklist

- [x] Read the injected Python style and clean-code skills before implementation.
- [x] Inspect the unified API, focused tests, operations guide, and existing worktree changes.
- [x] Set readiness false at lifespan entry, true only after both services are assigned, and false during shutdown.
- [x] Preserve dependency-free `GET /health` behavior.
- [x] Add `GET /health/ready` with success and sanitized unavailable responses.
- [x] Update OpenAPI inventory and focused health/startup tests using fakes only.
- [x] Update the relevant operations guidance for liveness, readiness, and future probes.
- [x] Run the required unittest, compile, and diff checks.
- [x] Confirm no out-of-scope file was modified, staged, reverted, or committed.

## Delegated Implementation Route

- Route: direct implementation requested by the user; no SDD/OpenSpec workflow.
- Allowed edit surfaces: `agents/api/main.py`, `agents/api/tests/test_main.py`, `GUIA_EJECUCION_BACKEND.md`, and this tracker.
- Injected skills:
  - `/home/leo/.agents/skills/python-code-style/SKILL.md`
  - `/home/leo/.agents/skills/clean-code/SKILL.md`
- CodeGraph inspected the API composition and health boundary before source edits.
- Existing unrelated changes in `data/processed/chroma/` and `requirements.txt` are out of scope.
- No commit: explicit user approval is required before any commit.

## Acceptance Checks

- [ ] `GET /health` returns exactly `200 {"status":"ok"}` without inspecting dependencies.
- [ ] `GET /health/ready` returns exactly `200 {"status":"ready"}` only when readiness is true and both service attributes exist.
- [ ] False or missing readiness state and missing service attributes return a sanitized HTTP `503`.
- [x] Health requests are implemented without calls to DeepSeek, Chroma, BM25, runtime builders, or application services.
- [ ] A startup builder failure propagates and never leaves readiness true.
- [ ] Shutdown resets readiness to false.
- [x] OpenAPI source and inventory expectations contain `/health` and `/health/ready`, with no `/health/live` route.
- [x] Focused tests use only injected builders and fakes; they require no real RAG artifacts or external services.
- [x] Operations guidance states that readiness must never depend on DeepSeek.
- [x] Required verification commands pass, or exact environment blockers are recorded.

## Verification Results

Implementation is complete. Static AST contract checks passed for both health routes, the absence of `/health/live`, readiness state transitions, both required service guards, and focused test coverage.

`python -m compileall agents/api` and `git diff --check` passed. `python -m unittest agents.api.tests.test_main` could not collect tests because the active Python 3.14 environment lacks FastAPI: `ModuleNotFoundError: No module named 'fastapi'`. The unchecked runtime acceptance items remain pending execution in an environment with the declared dependencies installed.

No task file was staged or committed. Pre-existing modifications in `requirements.txt` and `data/processed/chroma/` remain untouched and outside this work unit.
