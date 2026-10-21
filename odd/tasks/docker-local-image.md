# Docker Local Image

Objective: implement Phase 6 local Dockerization per `docs/plans/plan-fase-6-docker.md`. Branch: `dev`. Delivery: one commit per task, only after the user says to move to the next task (no push). Test runner: `python -m unittest` and `python -m compileall`; image checks with `docker`.

## Specs

S1-S10. Specs S1-S10 of `docs/plans/plan-fase-6-docker.md`, read in full through its `## Log`.

S11. Commit rule verbatim: "No hagas el commit, hazlo hasta que te digas pasa a la siguiente tarea."

## Tasks

| ID | Specs | Route | Status | Evidence |
|---|---|---|---|---|
| T1 | S2, S11 | inline (single unit, no writer trigger) | done | `2a3b92a`; RED 4 errors → GREEN 4/4; API suite 18 OK |
| T2 | S1, S3, S4, S6, S7 | inline | done (chmod layer unverified) | smoke L8; commit below |
| T3 | S5, S8 | inline | done | `docker compose config` valid for base and dev overlay; commit `feat(docker): add compose deployment and development overlays` |
| T4 | S1-S9 | inline + independent verifier (Risk item 5) | pending | — |
| T5 | S10 | inline | pending | — |

## Log

- L1 (2026-10-19, user): "sí, empieza con T1. No hagas el commit, hazlo hasta que te digas pasa a la siguiente tarea."
- L2 (2026-10-19): Pinned revisions resolve to full repo snapshots of 1207 MB (Qwen) and 608 MB (ALIA); no file filtering needed.
- L3 (2026-10-19): T1 implemented: `docker/download_models.py` (ast-parsed revisions, `snapshot_download` per model) and `agents/api/tests/test_docker_model_download.py` (isolated two-file layer, missing and non-string constants, download calls and exit code). RED: 4 errors (script missing); GREEN: 4/4; API suite 18 OK; compileall OK.
- L4 (2026-10-19): Offline run against the local cache fails with `OfflineModeIsEnabled` because `snapshot_download` lists the full repo tree and the local cache lacks non-model files (README, .gitattributes); expected, the build runs online. Real download proof deferred to T2 `docker build`.
- Next step: commit T1 when the user says to move on, then T2.
- L5 (2026-10-19): First build OK (287 s); in-image checks pass (uid 10001, torch 2.14.1+cpu, 0 nvidia packages, no .env/data/evaluation/tests); layers ≈ 3.9 GB uncompressed.
- L6 (2026-10-19, user): "Ejecuta la prueba". Smoke run without corpus: the lifespan raises `Missing runtime artifact` and Uvicorn exits with code 3, so `/health` never answers. Plan S5 check ("returns 503") is wrong for current code and must be corrected; with `restart: unless-stopped` a missing corpus becomes a restart loop.
- L7 (2026-10-19): Rebuild after the user's Dockerfile edit failed with `OSError: [Errno 28] No space left on device`; host root filesystem at 100% (423 MB free). Awaiting user decision on freeing space.
- L8 (2026-10-19, user): "ya realice yo mismo las limpiesas, verifica que tenemos el espacio requerido y de ser asi haz el test". Free 10 GB; full rebuild OK (min free 1.78 GB, now 1.8 GB). Scenario without corpus: exit 3 with `Missing runtime artifact`. Scenario with `data/processed` read-only, `/tmp` tmpfs, `RAG_CHROMA_WORKING_DIR=/tmp/chroma-work`, `--env-file .env`: ready in 14 s, `/health` 200, `/health/ready` 200, Docker health `healthy`, uid 10001, corpus mount rejects writes (`Read-only file system`), Chroma copy created under `/tmp/chroma-work`, ~760 MiB RAM.
- L9 (2026-10-19): 20 warnings `Ignoring corrupted tree cache file ... Permission denied`: huggingface_hub writes `trees/*.json` as 0600 root. Added a separate `find ... chmod a+r` layer after the download; not yet verified (rebuild needs more free disk).
- L10 (2026-10-19, user): "dejemos por el momento estas pruebas hasta hay, pasemos a la siguiente tarea." T2 committed with the chmod layer unverified; its rebuild check moves to T4.
- L11 (2026-10-19): T3 written: `compose.yaml` (env_file required, read-only corpus bind with `create_host_path: false`, tmpfs `/tmp` 256 MB mode 1777, `RAG_CHROMA_WORKING_DIR=/tmp/chroma-work`, `127.0.0.1:8000`, `restart: on-failure:3`) and `compose.dev.yaml` (read-only source binds for `agents` and `pipeline`, `--reload` with both reload dirs, `restart: "no"`). `docker compose config` valid for both; merged dev keeps the corpus mount; missing `.env` rejected. Plan S5 check corrected (exit code 3, not 503). No runnable RED test applies to YAML; `compose up` deferred to T4 by the user's pause on tests.
- L12 (2026-10-20, user): "explicame el compose.yml, y como el dockerfile dividelo en secciones." Added six numbered section headers to `compose.yaml` (comments only); both configs still valid. User then said "Haz el commit"; T3 committed.
