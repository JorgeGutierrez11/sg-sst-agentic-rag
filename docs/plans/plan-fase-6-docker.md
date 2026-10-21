# Phase 6: Local Dockerization Implementation Plan

> **For implementation workers:** Read this entire document through `## Log` before editing. Implement task by task and report the covered specs.

**Status (2026-10-19):** Planned. Prerequisites are met: Phases 1-5 and 7 are complete, all suites are green (pipeline 163, consultation 196, API 14, diagnosis 205), `.env.example` exists, and `dev` is synchronized with `main` (merge-base `b6ce5bc`).

**Goal:** Build one reproducible, non-root, CPU-only backend image that starts offline with pinned models, consumes the published corpus read-only, and runs through `docker compose` in a production-like default and an explicit development variant.

**Architecture:** A multi-stage `Dockerfile` installs CPU PyTorch and `requirements.txt`, downloads the two pinned Hugging Face models in a cache-stable layer, and copies only runtime code. `compose.yaml` is the production-like default; `compose.dev.yaml` is an explicit opt-in overlay for live reload. The image never contains secrets, corpus data, or evaluation data.

**Tech stack:** Docker 29 / Compose v5, `python:3.14-slim`, PyTorch `2.14.1+cpu`, `huggingface_hub`, Uvicorn, `unittest`.

## Global Constraints

- One image serves every environment; environments differ only by compose files and environment variables, never by branch-specific Docker files.
- Develop on `dev` and promote to `main` through a pull request with a merge commit (or merge `main` back into `dev` after a squash) so the merge-base stays current.
- Do not change `requirements.txt`; CPU PyTorch is selected only inside the image build.
- Do not change runtime behavior, index formats, or `RERANKER_DEVICE`.
- GitHub Actions (Phase 8) and production hardening (Phase 9) are out of scope.
- New code comments must be one concise technical sentence of at most two lines.
- Conventional Commits in English, no AI attribution, never push without explicit authorization.

---

## Specs

**S1 — CPU-only image.** User: "Usaremos cpu por esta implentacion." Install PyTorch from `https://download.pytorch.org/whl/cpu` before `requirements.txt`, exposed as build argument `TORCH_INDEX_URL` so a later GPU variant changes only that argument. The final image must contain no `nvidia-*` packages.
- Check: `docker run --rm <image> python -c "import torch; print(torch.__version__)"` prints a `+cpu` version; `pip list` inside the image shows no `nvidia-` entries.

**S2 — Models downloaded at build time.** User: "Creo que es mejor \"descargarla en el build\"" (confirmed). A build step downloads exactly `Qwen/Qwen3-Embedding-0.6B` at `DEFAULT_EMBEDDING_MODEL_REVISION` and `SINAI/ALIA-MrBERT-es-legal-administrative-reranker` at `RERANKER_MODEL_REVISION` into `HF_HOME=/opt/hf-cache`. The revisions are read from `pipeline/chunking/config.py` and `agents/consulta_normativa/langchain_rag/config.py` (no duplicated literals). The runtime sets `HF_HUB_OFFLINE=1`.
- The model layer copies only those two config files, so code changes do not re-download the ~1.8 GB of models.
- Check: a unit test proves the extracted revisions equal the imported constants; the container reaches readiness with networking to `huggingface.co` unavailable.

**S3 — Single worker, no reload in the default.** User: "Si manejemos un solo worker." Command: `uvicorn agents.api.main:app --host 0.0.0.0 --port 8000 --workers 1`. Sessions are in memory (`InMemorySaver`, `DiagnosticService._sessions`), so more workers would split sessions.

**S4 — Non-root runtime.** The final stage runs as a dedicated user with fixed UID/GID `10001` and owns no writable application files.
- Check: `docker run --rm <image> id -u` prints `10001`.

**S5 — Read-only corpus volume.** Confirmed option A: the image contains no `data/`. `compose.yaml` mounts `./data/processed:/app/data/processed:ro`. `RAG_CHROMA_WORKING_DIR=/tmp/chroma-work` points to a `tmpfs` mount, because Chroma rewrites its files even on query.
- Check: readiness succeeds with the read-only mount. Without the corpus the lifespan re-raises `Missing runtime artifact` and Uvicorn exits with code `3` (the API never serves `503`); compose uses `restart: on-failure:3` so this does not loop forever. A missing host `./data/processed` fails at `up` because the bind uses `create_host_path: false`.

**S6 — No secrets or private data in the image.** A whitelist `.dockerignore` (`*` then `!` entries) admits only `requirements.txt`, `agents/`, `pipeline/`, and `docker/`, and excludes `**/tests/` and `**/__pycache__/`. Secrets reach the container only through `env_file: .env` at run time; no `ARG`/`ENV` holds a secret.
- Check: `docker run --rm <image> sh -c 'test ! -e /app/.env && test ! -e /app/data && test ! -e /app/evaluation'` exits `0`; `docker history --no-trunc <image>` shows no `DEEPSEEK_API_KEY` value.

**S7 — Readiness healthcheck.** `HEALTHCHECK` calls `http://127.0.0.1:8000/health/ready` with Python `urllib` (the slim image has no `curl`), with `start_period` of 120 s to cover model loading (~14 s locally).
- Check: `docker compose ps` reports `healthy`.

**S8 — Development and deployment environments.** User: "mi intencion es tener un entorno de desarrollo y uno de despliegue pues la ides es implementar github actions". `compose.yaml` is production-like and is what `docker compose up` runs. `compose.dev.yaml` is an explicit overlay (`docker compose -f compose.yaml -f compose.dev.yaml up`) that bind-mounts `./agents` and `./pipeline` and runs Uvicorn with `--reload`. An explicit file is chosen over the auto-loaded `compose.override.yaml` so a forgotten flag yields production settings, not development ones.
- Ports bind to `127.0.0.1:8000` in both variants.

**S9 — End-to-end acceptance.** With `docker compose up`, the backend serves `GET /health`, `GET /health/ready`, `POST /api/v1/query`, the diagnosis flow, and `GET /api/v1/diagnostics/{diagnosis_id}/report` (PDF).
- The query and diagnosis checks call DeepSeek with the real key and run only with explicit user authorization.

**S10 — Documentation.** Add `docs/operations/docker.md` (build, run, dev overlay, corpus rebuild sequence: stop the container, run `python -m pipeline.offline_corpus build` on the host, start the container; troubleshooting). Update `docs/testing.md` with the new test, `docs/getting-started.md` with a pointer, and `docs/plans/plan-docker.md` Phase 6 status.

## Tasks

| ID | Specs | Route | Status | Commit |
|---|---|---|---|---|
| T1 | S2 | inline | pending | — |
| T2 | S1, S3, S4, S6, S7 | inline | pending | — |
| T3 | S5, S8 | inline | pending | — |
| T4 | S1-S9 checks | inline + independent verifier | pending | — |
| T5 | S10 | inline | pending | — |

### T1 — Model download script

- [ ] RED: `agents/api/tests/test_docker_model_download.py` asserts that the revisions extracted by `docker/download_models.py` equal `DEFAULT_EMBEDDING_MODEL_REVISION` and `RERANKER_MODEL_REVISION`, and that a missing constant raises a named error.
- [ ] Implement `docker/download_models.py`: parse both config files with `ast` (no imports of project modules), then call `huggingface_hub.snapshot_download(repo_id, revision=...)` for each model.
- [ ] Commit: `feat(docker): add pinned model download script`.

### T2 — Image

- [ ] Write the whitelist `.dockerignore`.
- [ ] Write the multi-stage `Dockerfile`: `deps` stage (venv, CPU torch, `requirements.txt`), `models` stage (two config files + script, `HF_HOME=/opt/hf-cache`), final stage (copy venv, cache, `agents/`, `pipeline/`; `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`, `HF_HUB_OFFLINE=1`; user `10001`; `HEALTHCHECK`; `CMD` from S3).
- [ ] Commit: `feat(docker): add CPU backend image`.

### T3 — Compose files

- [x] Write `compose.yaml`: build, `env_file: .env`, read-only corpus mount, `tmpfs` for `/tmp`, `RAG_CHROMA_WORKING_DIR`, port `127.0.0.1:8000:8000`, `restart: on-failure:3`.
- [x] Write `compose.dev.yaml`: source bind mounts and `--reload` command.
- [x] Commit: `feat(docker): add compose deployment and development overlays`.

### T4 — Verification

- [ ] Run every check in S1-S8 and record results in `## Log`.
- [ ] Run the four suites and `compileall` (unchanged runtime must stay green).
- [ ] Run S9 after explicit authorization for DeepSeek calls.
- [ ] Independent verifier (Risk item 5: delivery/environment and dependencies).

### T5 — Documentation

- [ ] Write the docs in S10.
- [ ] Commit: `docs(docker): document container build and operation`.

## Deferred (not in this plan)

- **Embedding revision guard.** Chroma does not store the Qwen revision and `pipeline/artifact_validation.py` does not compare it, so a mounted index built with another revision would load silently. Fix: store the revision in collection metadata during vectorization and compare it at startup. This changes a persisted format (high risk, item 1) and needs its own plan.
- **Read-only root filesystem** (`read_only: true`): requires proving that Hugging Face and Chroma write nothing outside `/tmp` in offline mode; belongs to Phase 9.
- **GPU image variant:** `TORCH_INDEX_URL` plus a configurable `RERANKER_DEVICE`.
- **Session persistence** across container restarts (Phase 9).

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R1 | Hugging Face download fails or is rate-limited during build | Retry the build; the model layer is cached once it succeeds |
| R2 | Host corpus files unreadable by UID `10001` | Files are created `0644` by the pipeline; document `chmod -R a+rX data/processed` in troubleshooting |
| R3 | Image size exceeds expectations | Target ~3.5-4 GB; record the measured size in `## Log` |
| R4 | `compose.yaml` started without `.env` | Compose fails fast on a missing `env_file` (verified); `.env.example` documents the variables |
| R5 | Non-root user cannot read `huggingface_hub` `trees/*.json` (0600) | Separate `chmod a+r` layer after the download; verify on the next rebuild (T4) |

## Log

- **L1 (2026-10-19, user):** "Actúa como un Principal Software Engineer & Lead DevOps Specialist [...] Tu objetivo es guiarme en la siguiente etapa del plan de preparación del entorno para despliegue: la contenedorización del sistema mediante Docker."
- **L2 (2026-10-19, user):** "Inicialmente arregla los test para dejar todo en verde. La prueba manual de build sobre el corpus real ya se realizo y todo salio bien. Puntos pendientes: Usaremos cpu por esta implentacion. Creemos el .env.example. Creo que es mejor \"descargarla en el build\", confirma si estoy en lo correcto. Si manejemos un solo worker."
- **L3 (2026-10-19):** Fixed the API route inventory test (`d08a593`) and added `.env.example` (`04c02a8`); all suites green. Verified `torch 2.14.1+cpu` wheels exist for Python 3.14 and `python:3.14-slim` is published.
- **L4 (2026-10-19, user):** "mi intencion es tener un entorno de desarrollo y uno de despliegue pues la ides es implementar github actions [...] los docker files, los docker compose deberían ir en la rama main [...] o continuaríamos en la rama dev?" Decision: same files on both branches, developed on `dev`, promoted by PR.
- **L5 (2026-10-19, user):** "sí, sincroniza dev con main y crea el plan". `main` was a squash merge (`b6ce5bc`); merged `main` into `dev` (`5448b38`, no content change); merge-base is now `b6ce5bc`. Index option A (read-only mount) confirmed.
- **Next step:** T1.
