# Diagnosis test suite repair

Objective: make `agents/diagnostico_cumplimiento/tests` pass against the current v2.1 catalogs, removing the unwired evaluation-rule engine.
Branch: `fix/diagnosis-tests` (from `dev`). Delivery: ask-on-risk. Runner: `python -m pytest agents/diagnostico_cumplimiento/tests`.

## Specs

- S1: Delete the evaluation-rule engine and its tests — user: "Borralos y luego repara los test." Modules: `domain/evaluation_rule.py`, `rules/evaluation_operator.py`, `rules/evaluation_rule_validation.py`, `rules/rule_execution_gate.py`, `questionnaire/condition_evaluation_gate.py`; tests: `test_evaluation_rule.py`, `test_evaluation_operator.py`, `test_evaluation_operator_edge_cases.py`, `test_evaluation_rule_validation.py`, `test_rule_execution_gate.py`, `test_condition_evaluation_gate.py`. Acceptance: no remaining import of those modules; API-reachable modules unchanged.
- S2: Bare `pytest agents/diagnostico_cumplimiento/tests` must collect without `ModuleNotFoundError: No module named 'agents'` (add root `pytest.ini` with `pythonpath = .`).
- S3: Repair the remaining failing tests ("repara los test") so they exercise API-reachable code against the v2.1 catalog model, using a stable test fixture catalog instead of the never-committed `res0312_piloto_v1/v2/v6.json`.
- S4: Stop and report to the user before changing production code if a failure reveals a real production bug rather than stale test data.
- S5: Close with 0 failures in the diagnosis suite, no regressions in `pipeline/tests`, `agents/consulta_normativa/tests`, `agents/api/tests`, and `docs/testing.md` updated.

## Tasks

- T1 (S1, S2) inline — delete engine + tests, add `pytest.ini`. Status: in progress.
- T2 (S3) — repair strategy decided from catalog-model mapping. Status: pending explorer handoff.
- T3 (S3, S4) — repair failing test blocks. Status: pending.
- T4 (S5) — full verification and `docs/testing.md`. Status: pending.

## Log

- L1 (2026-10-17, user): "prefiero que arreglemos los test, primero miremos si son realmente requeridos, pues pueden ser test de cosas no implementadas, luego de ello muestrame un plan para arreglarlos." Then: "Borralos y luego repara los test."
- L2: Baseline `python -m pytest`: 37 files, 271 tests, 102 passed, 169 failed. Import closure from `agents.api.main` shows the evaluation-rule engine is unreachable; catalog schema has no `evaluation_rule` field; no dynamic imports.
- L3: `catalog/schemas.py` holds two model generations (old condition-based and v2.1 section-based). Explorer delegated (mapping trigger) to establish which one reachable code consumes before choosing the repair strategy.
