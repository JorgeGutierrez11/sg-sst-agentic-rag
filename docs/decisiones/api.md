# Unified Agent API Migration Plan

> **Status:** `Historical`
> **Audience:** maintainer
> **Verified against:** `agents/api/main.py` (plan ejecutado)
> **Last verified:** 2026-10-18
> **Replacement:** [reference/api.md](../reference/api.md)

## Decision

Consolidate the normative consultation and compliance diagnosis APIs behind one FastAPI application. The neutral composition root will be `agents/api/main.py`; it will own the single application instance, CORS configuration, and lifespan, initialize both services once, and include the existing domain routers.

Expose one process and one base URL. Preserve the functional endpoint paths, methods, request schemas, response schemas, status codes, and error behavior. Retain only `GET /health` as the application-level health endpoint.

## Goal and non-goals

**Goal:** replace the two independently started FastAPI applications with one composition root while keeping both agents' functional HTTP contracts stable.

**Non-goals:**

- Do not merge the agents' domain or service layers.
- Do not change the consultation LangGraph, retrieval pipeline, or conversation behavior.
- Do not change diagnosis rules, session behavior, PDF generation, or schemas.
- Do not add persistence, distributed session storage, queues, proxies, deployment platforms, or new libraries.
- Do not redesign endpoint namespaces or introduce a broader API versioning change.
- Do not remove compatibility entrypoints until their consumers have been verified.

## Current state

- `agents/consulta_normativa/api/main.py` creates a FastAPI application, configures CORS, builds the heavy LangGraph RAG once during lifespan, stores `QueryService` in `app.state.query_service`, and includes routes for `GET /health` and `POST /api/v1/query`.
- `agents/diagnostico_cumplimiento/api/main.py` independently creates another FastAPI application, duplicates the CORS setup, creates `DiagnosticService` during lifespan, stores it in `app.state.diagnostic_service`, and includes a router under `/api/v1/diagnostics`.
- The diagnosis router currently includes its own namespaced health endpoint in addition to the diagnostic workflow endpoints.
- `GUIA_EJECUCION_BACKEND.md` instructs operators to run two Uvicorn processes on ports 8000 and 8001.
- Consultation API coverage exists in `agents/consulta_normativa/tests/test_api.py`. Diagnosis domain tests exist, but the diagnosis API composition currently has no equivalent integration coverage.

## Target architecture

`agents/api/main.py` becomes the only authoritative composition root:

1. Build the consultation runtime once and wrap it in `QueryService`.
2. Create one `DiagnosticService` instance.
3. Store both services on the shared FastAPI application's state using their existing state attribute names, so current dependency functions continue to work.
4. Configure CORS once with the currently allowed frontend origin and existing middleware behavior.
5. Register one root `GET /health`, the consultation router, and the namespaced diagnosis router.
6. Export the application used by `uvicorn agents.api.main:app`.

The neutral composition root depends on each agent's public API adapter components; neither agent depends on the neutral root except through temporary compatibility modules. Router, dependency, service, schema, LangGraph, retrieval, and PDF responsibilities remain in their existing packages.

The existing agent-specific `api/main.py` modules may temporarily re-export or adapt the unified `app` and application factory. This preserves import and launch compatibility during consumer verification without creating additional authoritative application configurations. Deprecation and eventual removal are separate, later actions.

## Endpoint compatibility table

| Method | Path | Migration result | Contract requirement |
|---|---|---|---|
| `GET` | `/health` | Retained as the only health endpoint | Keep `200` and `{"status":"ok"}`. It is owned by the unified application. |
| `POST` | `/api/v1/query` | Unchanged | Preserve request/response schemas, generated or supplied conversation IDs, `200`, validation behavior, and sanitized `503` responses. |
| `GET` | `/api/v1/diagnostics/health` | Removed | Replaced by the root application health endpoint; this is not a diagnosis workflow contract. |
| `POST` | `/api/v1/diagnostics` | Unchanged | Preserve request/response schemas, `201`, validation, catalog-selection behavior, and current error mapping. |
| `POST` | `/api/v1/diagnostics/{diagnosis_id}/answers` | Unchanged | Preserve session lookup, answer validation, response schema, `200`, `404`, `409`, and `503` behavior. |
| `POST` | `/api/v1/diagnostics/{diagnosis_id}/complete` | Unchanged | Preserve completion rules, response schema, `200`, `404`, `409`, and `503` behavior. |
| `GET` | `/api/v1/diagnostics/{diagnosis_id}/report` | Unchanged | Preserve PDF bytes, media type, response headers, session cleanup behavior, `200`, `404`, `409`, and `503` behavior. |

## File-level change list

| File | Planned change |
|---|---|
| `agents/api/__init__.py` | Create the neutral API package without domain logic. |
| `agents/api/main.py` | Create the authoritative application factory, shared lifespan, root health endpoint, one CORS setup, service initialization, and router registration. Keep builders injectable only where needed for isolated startup tests. |
| `agents/api/tests/test_main.py` | Add unified composition tests for one-time service construction, shared app state, CORS, root health, route registration, duplicate-path prevention, and startup failure behavior. |
| `agents/consulta_normativa/api/routes.py` | Remove the router-owned health endpoint; leave the query endpoint unchanged. |
| `agents/diagnostico_cumplimiento/api/routes.py` | Remove the namespaced health endpoint; leave all diagnosis workflow endpoints unchanged. |
| `agents/consulta_normativa/api/main.py` | Replace independent application construction with a temporary compatibility re-export or adapter to the unified composition root. |
| `agents/diagnostico_cumplimiento/api/main.py` | Replace independent application construction with a temporary compatibility re-export or adapter to the unified composition root. |
| `agents/consulta_normativa/tests/test_api.py` | Keep service and query contract tests; move application-level health and lifespan expectations to unified composition tests and update imports accordingly. |
| `GUIA_EJECUCION_BACKEND.md` | Replace the two-process, two-port instructions with the single `agents.api.main:app` Uvicorn command, one base URL, root health check, and both endpoint families. Document the diagnosis session limitation. |

No domain, retrieval, LangGraph, diagnosis engine, PDF, or schema files should change.

## Ordered migration phases with acceptance criteria and rollback points

### Phase 1 — Lock compatibility with tests

1. Add unified-app tests that use lightweight injected builders or patched constructors; tests must not load real retrieval indexes or models.
2. Assert that startup constructs each service exactly once and exposes both expected state attributes.
3. Assert the complete endpoint inventory and the absence of duplicate health endpoints.
4. Preserve the existing consultation route/service tests and add HTTP-level diagnosis route coverage through the shared app with a controlled service double.

**Acceptance criteria**

- Tests encode every row in the endpoint compatibility table.
- The tests fail against the pre-consolidation structure for the expected reasons.
- Test startup performs no external model, index, network, or filesystem-heavy initialization.

**Rollback point:** test-only changes can be removed with no runtime impact.

### Phase 2 — Introduce the neutral composition root

1. Add `agents/api/main.py` with one FastAPI instance, one lifespan, and one CORS configuration.
2. Initialize the consultation runtime before assigning `QueryService`, initialize `DiagnosticService`, and expose both through their existing `app.state` names.
3. Define root health at the composition level and include both existing routers.
4. Remove the two router-level health handlers so only `/health` remains.

**Acceptance criteria**

- `uvicorn agents.api.main:app` starts one application when required local data and environment configuration are available.
- Both services are constructed once per application lifespan, not per request.
- OpenAPI contains all functional routes exactly once, contains `/health`, and does not contain `/api/v1/diagnostics/health`.
- Existing request, response, status, error, and PDF contracts remain unchanged.
- CORS behavior remains equivalent for `http://localhost:3000`.

**Rollback point:** revert the neutral root and router health changes; the two original application modules remain available until Phase 3.

### Phase 3 — Add compatibility entrypoints and verify consumers

1. Convert both agent-specific `api/main.py` modules into temporary compatibility re-exports or thin adapters backed by the unified application.
2. Verify repository scripts, frontend configuration, local commands, and deployment configuration use either the new canonical import or a functioning compatibility import.
3. Mark old imports as deprecated in documentation only after verification; do not remove them in this migration.

**Acceptance criteria**

- `agents.api.main:app` is the documented and authoritative entrypoint.
- Imports of both previous `app` locations still resolve during the compatibility window.
- Compatibility entrypoints do not create separate FastAPI applications, lifespans, service instances, or CORS configurations.
- Verified consumers use one backend base URL and require no functional endpoint changes.

**Rollback point:** restore either original `main.py` composition root and its launch command while retaining the neutral root for further correction.

### Phase 4 — Update operations documentation

1. Rewrite `GUIA_EJECUCION_BACKEND.md` around one terminal, one Uvicorn process, and one port.
2. Update health, consultation, diagnosis, restart, troubleshooting, and shutdown examples.
3. State that diagnosis sessions are process-local and are lost on restart or when a request reaches another worker.

**Acceptance criteria**

- The guide contains no instruction requiring simultaneous backend ports 8000 and 8001.
- Every documented URL matches the endpoint compatibility table.
- The canonical launch command is `uvicorn agents.api.main:app` with the project's chosen host, port, and development reload options.
- The guide does not imply durable or multi-worker diagnosis sessions.

**Rollback point:** restore the previous two-process guide if runtime consolidation is rolled back; do not leave mixed operating instructions.

### Phase 5 — Final regression and cutover

1. Run the focused unified API tests and both existing agent test suites.
2. Run the repository compile check.
3. Start the unified application against the real local artifacts and perform smoke requests for root health, normative query, diagnosis creation, answer submission, completion, and PDF retrieval.
4. Switch verified consumers to the unified base URL while keeping compatibility imports for the agreed observation period.

**Acceptance criteria**

- All automated suites and compile checks pass.
- One running process serves both endpoint families.
- Smoke responses conform to the compatibility table, including PDF headers and content type.
- A restart is explicitly verified to invalidate an in-progress diagnosis, confirming the documented limitation rather than masking it.

**Rollback point:** point consumers back to the previous two-process launch commands and restore the original application modules. No data migration or schema rollback is required because this change introduces no persisted state.

## Test strategy

Use the repository's existing `unittest` tooling.

**Focused checks**

```bash
python -m unittest agents.api.tests.test_main agents.consulta_normativa.tests.test_api
```

Cover:

- one invocation of each service builder per lifespan;
- `app.state.query_service` and `app.state.diagnostic_service` availability;
- one CORS middleware configuration with the existing allowed origin;
- root health success and removal of namespaced diagnosis health;
- unchanged query success, validation, conversation continuity, and sanitized failure behavior;
- unchanged diagnosis creation, answer, completion, report, and error behavior;
- the exact route/method inventory, preventing accidental duplicate registration;
- compatibility imports resolving to the unified application;
- deterministic startup failure when either required service cannot initialize.

**Regression checks**

```bash
python -m unittest discover -s pipeline/tests
python -m unittest discover -s agents/consulta_normativa/tests
python -m unittest discover -s agents/diagnostico_cumplimiento/tests
python -m compileall pipeline agents/consulta_normativa agents/diagnostico_cumplimiento agents/api
```

**Manual smoke checks**

- Start only `agents.api.main:app`.
- Call `/health` and confirm the former namespaced health path returns `404`.
- Exercise one consultation conversation using a stable `conversation_id`.
- Complete one diagnosis in the same process and retrieve its PDF.
- Confirm browser requests from `http://localhost:3000` retain the current CORS behavior.

## Operational constraints

- The consultation runtime is heavy and must be constructed once per process during lifespan. Unified startup now depends on all consultation indexes, models, configuration, and API credentials being available.
- The shared lifespan couples readiness: if either required service fails to initialize, the unified application must fail startup rather than serve a misleading healthy state.
- `DiagnosticService` stores sessions in process-local memory. Sessions do not survive process restart and are not shared across multiple Uvicorn workers.
- Run a single Uvicorn worker while diagnosis sessions remain in memory. Durable or multi-worker sessions require a separate design and are explicitly outside this migration.
- Development reload restarts the process and therefore clears active diagnosis sessions.
- PDF generation remains in memory and retains its current successful-generation cleanup behavior.
- This migration changes composition and deployment topology only; it does not migrate user or diagnostic data.

## Risks

| Risk | Mitigation |
|---|---|
| Unified startup increases failure coupling between agents. | Fail startup clearly, test both failure paths, and keep the rollback entrypoints until cutover is verified. |
| Duplicate routes or health handlers produce ambiguous OpenAPI behavior. | Move health ownership to the neutral root and assert the exact route/method inventory. |
| Compatibility modules accidentally instantiate extra applications or heavy runtimes. | Make them thin re-exports/adapters and test application identity and one-time construction. |
| Consumers still target port 8001 or the namespaced health path. | Inventory consumers before deprecation, update the execution guide, and retain temporary import compatibility. |
| Multiple workers or reloads silently lose diagnosis sessions. | Document and test the process-local limitation; operate with one worker until persistence is designed separately. |
| Integration tests trigger expensive RAG initialization. | Inject or patch builders in composition tests and reserve real initialization for the final smoke check. |
| Consolidation drifts into domain refactoring. | Limit changes to composition, health ownership, compatibility modules, tests, and operating documentation. |

## Definition of done

- [ ] `agents/api/main.py` is the sole authoritative FastAPI composition root.
- [ ] One lifespan creates one `QueryService` and one `DiagnosticService` per process.
- [ ] CORS is configured once and preserves current frontend access.
- [ ] All functional endpoint contracts in the compatibility table are unchanged.
- [ ] Only `GET /health` remains as a health endpoint.
- [ ] Agent-specific `api/main.py` imports remain compatible until consumer verification is complete.
- [ ] Unified composition, route contracts, failure behavior, and compatibility imports have automated coverage.
- [ ] Both agent suites and the compile check pass.
- [ ] A real single-process smoke test serves consultation and diagnosis successfully.
- [ ] `GUIA_EJECUCION_BACKEND.md` documents one Uvicorn process and one base URL.
- [ ] The process-local, restart-volatile, single-worker diagnosis limitation is explicit.
- [ ] No domain, service behavior, LangGraph, retrieval, PDF, schema, persistence, or infrastructure redesign is included.
