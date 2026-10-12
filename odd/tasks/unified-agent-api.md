# Unified Agent API

## Objective

Implement the approved `docs/decisiones/api.md` plan by replacing the two independent FastAPI applications with one neutral composition root while preserving every functional consultation and diagnosis HTTP contract.

## Scope

- Add `agents.api.main` as the sole authoritative FastAPI composition root.
- Build the normative RAG runtime once per lifespan and expose `QueryService` as `app.state.query_service`.
- Build `DiagnosticService` once per lifespan and expose it as `app.state.diagnostic_service`.
- Centralize CORS and root `GET /health` in the neutral application.
- Include the existing consultation and diagnosis routers without changing their service, schema, domain, retrieval, LangGraph, or PDF behavior.
- Keep both former agent-specific application imports as thin compatibility re-exports.
- Add isolated unified API tests and update the backend execution guide.

## Stable Checklist

- [x] Create the neutral `agents/api` package and authoritative `create_app`.
- [x] Inject lightweight runtime and diagnostic service builders for composition tests.
- [x] Initialize both services exactly once in the shared lifespan using the existing app-state names.
- [x] Configure the existing localhost CORS policy exactly once.
- [x] Register root `GET /health` and both functional routers exactly once.
- [x] Remove health handlers from the domain routers.
- [x] Convert both agent-specific `api/main.py` modules to compatibility re-exports without independent construction.
- [x] Preserve consultation API service and route contract tests.
- [x] Add diagnosis HTTP contract coverage through controlled service doubles.
- [x] Add unified composition, route inventory, compatibility import, CORS, and startup-failure tests.
- [x] Update `GUIA_EJECUCION_BACKEND.md` for one process, one base URL, and the diagnosis session limitation.
- [x] Run all requested focused suites, agent suites, and compile checks.
- [x] Review the final diff and create exactly one isolated conventional work-unit commit if safe.

## Route Selection and Delegation Evidence

- Canonical entrypoint: `uvicorn agents.api.main:app`.
- Composition ownership: `agents/api/main.py` owns FastAPI construction, lifespan, CORS, and root health.
- Consultation delegation: `POST /api/v1/query` remains implemented by `agents.consulta_normativa.api.routes.router` and resolves `app.state.query_service` through the existing dependency.
- Diagnosis delegation: `/api/v1/diagnostics/*` remains implemented by `agents.diagnostico_cumplimiento.api.routes.router` and resolves `app.state.diagnostic_service` through the existing dependency.
- Removed non-functional duplicate: `GET /api/v1/diagnostics/health`.
- Compatibility imports: both former `api.main` modules must reference the exact unified `app` and `create_app` objects.
- Inspection evidence: CodeGraph confirmed both current roots independently configure CORS/lifespans and the routers currently own duplicate health endpoints.

## Acceptance Checks

- [x] Startup invokes each injected builder once and exposes both state attributes.
- [x] Startup failure from either builder propagates and does not expose a misleading healthy application.
- [x] OpenAPI/route inventory contains every functional endpoint exactly once, one root `/health`, and no namespaced health endpoint.
- [x] Root health returns `200` with `{"status":"ok"}`.
- [x] CORS allows `http://localhost:3000` with the existing credentials, methods, and headers behavior.
- [x] Query success, validation, conversation continuity, and sanitized `503` behavior remain unchanged.
- [x] Diagnosis creation, answer, completion, report, validation, and error mappings remain unchanged.
- [x] Compatibility imports do not create separate app instances or service lifespans.
- [x] Tests use fakes/builders and do not load real models, indexes, networks, or external services.
- [x] The guide documents a single worker and that diagnosis sessions are in-memory, restart-volatile, and not shared across workers.

## Expected Work Unit

One coherent work unit: introduce and verify the unified FastAPI composition boundary, including compatibility adapters, router health cleanup, isolated contract tests, and matching operations documentation. Rollback consists only of the files listed in this task; no domain data or generated index rollback is required.

## Observed Checks

- Focused unified and agent API command: 23 tests passed.
- Consultation discovery suite: 168 tests ran; 166 passed and two unrelated prompt-contract assertions failed in `test_langchain_rag_prompts`.
- Diagnosis discovery suite: 34 tests ran; seven passed and 27 pre-existing modules failed to import because undeclared `pytest` is absent from the project environment.
- Repository compile check completed successfully for `pipeline`, both agent packages, and `agents/api`.
- No real RAG runtime, external model, index construction, network request, or external service was used by the new API tests.

## Commit Evidence

- Intended isolated conventional commit: `feat(api): unify agent composition root`.
- The commit includes this tracker, implementation, tests, and operations guide as one rollback-safe work unit.
- The immutable commit hash is reported externally after creation because a commit cannot contain its own hash.
