# Docker Local Image

Objective: implement Phase 6 local Dockerization per `docs/plans/plan-fase-6-docker.md`. Branch: `dev`. Delivery: one commit per task, only after the user says to move to the next task (no push). Test runner: `python -m unittest` and `python -m compileall`; image checks with `docker`.

## Specs

S1-S10. Specs S1-S10 of `docs/plans/plan-fase-6-docker.md`, read in full through its `## Log`.

S11. Commit rule verbatim: "No hagas el commit, hazlo hasta que te digas pasa a la siguiente tarea."

## Tasks

| ID | Specs | Route | Status | Evidence |
|---|---|---|---|---|
| T1 | S2, S11 | inline (single unit, no writer trigger) | done, uncommitted (awaiting user) | RED 4 errors → GREEN 4/4; API suite 18 OK |
| T2 | S1, S3, S4, S6, S7 | inline | pending | — |
| T3 | S5, S8 | inline | pending | — |
| T4 | S1-S9 | inline + independent verifier (Risk item 5) | pending | — |
| T5 | S10 | inline | pending | — |

## Log

- L1 (2026-10-19, user): "sí, empieza con T1. No hagas el commit, hazlo hasta que te digas pasa a la siguiente tarea."
- L2 (2026-10-19): Pinned revisions resolve to full repo snapshots of 1207 MB (Qwen) and 608 MB (ALIA); no file filtering needed.
- L3 (2026-10-19): T1 implemented: `docker/download_models.py` (ast-parsed revisions, `snapshot_download` per model) and `agents/api/tests/test_docker_model_download.py` (isolated two-file layer, missing and non-string constants, download calls and exit code). RED: 4 errors (script missing); GREEN: 4/4; API suite 18 OK; compileall OK.
- L4 (2026-10-19): Offline run against the local cache fails with `OfflineModeIsEnabled` because `snapshot_download` lists the full repo tree and the local cache lacks non-model files (README, .gitattributes); expected, the build runs online. Real download proof deferred to T2 `docker build`.
- Next step: commit T1 when the user says to move on, then T2.
