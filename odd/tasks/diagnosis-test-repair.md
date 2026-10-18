# Diagnosis test suite repair

Objective: make `agents/diagnostico_cumplimiento/tests` pass against the current v2.1 catalogs, removing the unwired evaluation-rule engine.
Branch: `fix/diagnosis-tests`, fast-forwarded into `dev` on user request; further work uncommitted on `dev`. Delivery: ask-on-risk. Runner: `python -m pytest agents/diagnostico_cumplimiento/tests`.

## Specs

- S1: Delete the evaluation-rule engine and its tests — user: "Borralos y luego repara los test." Modules: `domain/evaluation_rule.py`, `rules/evaluation_operator.py`, `rules/evaluation_rule_validation.py`, `rules/rule_execution_gate.py`, `questionnaire/condition_evaluation_gate.py`; tests: `test_evaluation_rule.py`, `test_evaluation_operator.py`, `test_evaluation_operator_edge_cases.py`, `test_evaluation_rule_validation.py`, `test_rule_execution_gate.py`, `test_condition_evaluation_gate.py`. Acceptance: no remaining import of those modules; API-reachable modules unchanged.
- S2: Bare `pytest agents/diagnostico_cumplimiento/tests` must collect without `ModuleNotFoundError: No module named 'agents'` (add root `pytest.ini` with `pythonpath = .`).
- S3: Repair the remaining failing tests ("repara los test") so they exercise API-reachable code against the v2.1 catalog model, using a stable test fixture catalog instead of the never-committed `res0312_piloto_v1/v2/v6.json`.
- S4: Stop and report to the user before changing production code if a failure reveals a real production bug rather than stale test data.
- S5: Close with 0 failures in the diagnosis suite, no regressions in `pipeline/tests`, `agents/consulta_normativa/tests`, `agents/api/tests`, and `docs/testing.md` updated.

## Tasks

- T1 (S1, S2) inline — delete engine + tests, add `pytest.ini`. Status: done, commit `0f719f2`.
- T2 (S3) inline — v2.1 test fixture (`tests/fixtures/valid_catalog.json` frozen copy of general catalog) + `tests/conftest.py`. Status: done, ships in the T3 commit.
- T3 (S3, S4) delegated, 4 parallel writers (writer trigger: independent units, disjoint surfaces) — U1 catalog/applicability, U2 answer interpreters, U3 questionnaire/progress/snapshot, U4 preliminary diagnosis/reporting. Status: done (U1 41, U2 44, U3 27, U4 31 passed; parent re-ran each). Commit: see L7.
- T3b (S1-ext) inline — deleted `questionnaire/condition_answer_summary.py`, `questionnaire/condition_progress.py`, `domain/condition_evaluation.py`, `ConditionSnapshot`, `AmbiguousApplicabilityError` and their tests. Status: done, uncommitted (user permission required to commit).
- T3c (S1-ext) — legacy leaf models in `catalog/schemas.py` (+ their `test_catalog.py` tests); only remaining production user was unwired `evidence/rag_evidence.py`. Status: done, uncommitted — deleted legacy models, `evidence/rag_evidence.py` and 11 legacy tests; `ApplicabilityRule`/`NormativeSource` kept (used by `rules/decision_matrix.py`, `test_models.py`).
- T4 (S5) inline — full verification and `docs/testing.md`. Status: done, uncommitted.

## Log

- L1 (2026-10-17, user): "prefiero que arreglemos los test, primero miremos si son realmente requeridos, pues pueden ser test de cosas no implementadas, luego de ello muestrame un plan para arreglarlos." Then: "Borralos y luego repara los test."
- L2: Baseline `python -m pytest`: 37 files, 271 tests, 102 passed, 169 failed. Import closure from `agents.api.main` shows the evaluation-rule engine is unreachable; catalog schema has no `evaluation_rule` field; no dynamic imports.
- L3: `catalog/schemas.py` holds two model generations (old condition-based and v2.1 section-based). Explorer delegated (mapping trigger) to establish which one reachable code consumes before choosing the repair strategy.
- L4: Explorer: `AssessmentCatalog` (v2.1) is the only root model; API-executed modules all consume v2.1. `condition_answer_summary`/`condition_progress` are old-model only, imported but never called (parent spot-checked). Repair strategy: v2.1 fixture, not live catalogs.
- L5: After T1 + fixture: 131 failed, 96 passed. T1 verified: compileall ok, `agents/api/tests` OK.
- L6: Writers found no production bugs (S4 not triggered). Tests removed/replaced: U1 removed 2 `AmbiguousApplicabilityError` tests (class defined at `rules/applicability.py:21`, never raised); U3 replaced the pilot `CatalogCoverageError` test with profile-based catalog selection; U4 replaced the `catalog_profile_match` trigger test. Added routing tests for skipped dependents (U2, U3, U4). Notes: `QuestionnaireSnapshot.catalog_version` holds the schema version "2.1"; `PreliminaryDiagnosisResult.routing` is always empty in the live path; legacy-model tests in `test_catalog.py` still pass but pin dead models.
- L7: Seam check: diagnosis 220 passed, 10 failed (only `test_condition_answer_summary.py`, `test_condition_progress.py`, pending T3b); `agents/api/tests` OK; `agents/consulta_normativa/tests` 170 OK; `pipeline/tests` OK; compileall ok; no production file changed.
- L8 (2026-10-17, user): "Algo importante es que no hagas commits sin mi permiso, y solo crea ramas en cambios muy grandes o delicados y antes de hacerlo debes preguntarme" / "Borra el código legacy y sus tests asociados." / "Une esta rama nueva con la dev y yo subo los cambios manualmente." Engram writes blocked by a hook (host session ended); rule saved in local Claude memory instead.
- L9: `dev` fast-forwarded to `28df9b3`. T3b verified: diagnosis 208 passed / 0 failed (collected-test diff vs HEAD: only the 22 tests of the 3 deleted files), `agents/api/tests` OK, consulta 170 OK, pipeline OK, compileall ok.
- L10 (2026-10-17, user): "borralo y borra la rama que habias creado." Recommended deleting over adapting: live gap enrichment grounds normative content in the curated catalog by design; `rag_evidence.py` had no caller or tests. Verified: diagnosis 197 passed / 0 failed, api OK, consulta 170 OK, pipeline OK, compileall ok. Branch `fix/diagnosis-tests` deleted (merged into `dev`).
- L11: `docs/testing.md` updated (75 modules, diagnosis 28, `pytest.ini`, `conftest.py`, frozen v2.1 fixture, retired tests). Structural readback: no stale counts or removed test names remain; diagnosis 197 passed.
