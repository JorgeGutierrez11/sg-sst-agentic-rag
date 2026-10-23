# Phase 8: Continuous Integration with GitHub Actions — Implementation Plan

> **For implementation workers:** Read this entire document through `## Log` before editing. Implement task by task and report the covered specs.

**Status (2026-10-20):** Planned. Prerequisites are met: Phase 6 is complete (`ec5290c`), all suites are green locally, the image builds and passes its smoke test, and the repository is public.

**Goal:** Every push to `dev` or `main` and every pull request into `main` runs the test suites automatically; pull requests into `main` also build the Docker image and prove it starts. A branch ruleset blocks merging into `main` while any check fails.

**Architecture:** Two workflow files live in this repository under `.github/workflows/` and are versioned like any other code. GitHub discovers them when they are pushed. `tests.yml` runs the four suites on a GitHub-hosted Ubuntu runner. `image.yml` builds the image through the real `compose.yaml`, starts it with a generated dummy `.env`, and checks readiness and image hygiene. Settings that cannot live in files (Actions permissions, the branch ruleset) are configured once by the user in the GitHub web UI.

**Tech stack:** GitHub Actions (`ubuntu-latest`), `actions/checkout`, `actions/setup-python`, `actions/cache`, Docker Compose v2 on the runner, Python 3.14, CPU PyTorch `2.14.1`.

## Global Constraints

- Workflow files are created in this repository and reach GitHub only through a normal commit and push; nothing is uploaded through the web UI.
- Public repository: workflows and logs are public. No step prints secrets, `.env` contents, or company data. Phase 8 uses no repository secrets at all.
- Never use `pull_request_target`, and never check out fork code with write permissions.
- Every workflow declares `permissions: contents: read` at the top level.
- Third-party actions are pinned to a full commit SHA with the version tag in a trailing comment; SHAs are resolved at implementation time, never invented.
- Do not change runtime behavior, `requirements.txt`, the `Dockerfile`, or the compose files, unless a task explicitly requires it.
- Develop on `dev`; promote to `main` through a pull request.
- New code comments must be one concise technical sentence of at most two lines.
- Conventional Commits in English, no AI attribution, never push without explicit authorization.

## Where Things Live

| Item | Location | Who creates it |
|---|---|---|
| `tests.yml`, `image.yml` | `.github/workflows/` in this repository | Agent, as committed files |
| Optional `dependabot.yml` | `.github/` in this repository | Agent, if S9 is accepted |
| Actions permissions | GitHub → Settings → Actions → General | User, in the web UI |
| Branch ruleset for `main` | GitHub → Settings → Rules → Rulesets | User, in the web UI |
| Run history and logs | GitHub → Actions tab | GitHub, automatically |

## Specs

**S1 — Location and triggers.** `tests.yml` triggers on `push` to `dev` and `main` and on `pull_request` targeting `main`. `image.yml` triggers on `pull_request` targeting `main` and on `push` to `main`. Both also accept `workflow_dispatch` for manual reruns. Each workflow uses `concurrency` keyed on workflow and ref with `cancel-in-progress: true`, and each job sets `timeout-minutes`.
- Check: a push to `dev` starts only `tests`; a pull request from `dev` into `main` starts both.

**S2 — Security baseline.** Top-level `permissions: contents: read`; actions pinned by SHA; no `pull_request_target`; no secrets referenced; `actions/checkout` with `persist-credentials: false`.
- Check: `grep -rn "pull_request_target\|secrets\." .github/workflows` is empty; every `uses:` line has a 40-character SHA.

**S3 — Tests job.** Set up Python from `.python-version` with pip caching keyed on `requirements.txt`. Install `torch==2.14.1` from `https://download.pytorch.org/whl/cpu`, then `requirements.txt`. Run:

```bash
python -m unittest discover -s pipeline/tests
python -m unittest discover -s agents/consulta_normativa/tests
python -m unittest discover -s agents/api/tests
python -m pytest agents/diagnostico_cumplimiento/tests
python -m compileall -q pipeline agents
```

- Check: the job log shows pipeline 163, consultation 196, API 18, diagnosis 205 passed, and `pip list` shows no `nvidia-` packages.

**S4 — Hugging Face cache for the tests job.** `pipeline/tests/test_chunking_phase2_sliding_window.py` loads the real `Qwen/Qwen3-Embedding-0.6B` tokenizer; verified 2026-10-20: with an empty cache and no network, 3 failures and 1 error. The job caches `~/.cache/huggingface` with `actions/cache`, keyed on the hash of `pipeline/chunking/config.py`, which holds the pinned revision.
- Check: the second run on the same key reports a cache hit and the suite stays green.

**S5 — Image build.** `image.yml` builds with `docker compose build`, so it exercises the real `compose.yaml`. It reports free disk before and after the build (`df -h /`); if the first run fails for lack of space, add a cleanup step that removes preinstalled runner toolchains.
- Check: the build succeeds and the log records the image size.

**S6 — Container smoke test.** Before `up`, the job writes a `.env` in the runner workspace with `DEEPSEEK_API_KEY=ci-dummy-key` and `CORS_ALLOWED_ORIGINS=http://localhost:3000`; this file is never committed. It runs `docker compose up -d --wait --wait-timeout 300`, then requires HTTP 200 from `GET /health` and `GET /health/ready`. On failure it prints `docker compose logs backend`. It always runs `docker compose down`. Verified 2026-10-20: a dummy key reaches `healthy` in about 27 s and readiness returns 200.
- Check: the job passes; a deliberately broken readiness, such as an empty corpus mount in a scratch branch, makes it fail.

**S7 — Image hygiene.** The same job checks: `torch.__version__` ends in `+cpu`; `pip list` has 0 `nvidia-` entries; `id -u` is `10001`; `/app/.env`, `/app/data`, and `/app/evaluation` are absent; `docker history --no-trunc` has 0 matches for `DEEPSEEK`.
- Check: each check fails the job when its condition is false.

**S8 — Platform configuration (user, web UI).** The repository has these settings:
1. Settings → Actions → General → Actions permissions: allow GitHub-authored actions plus the listed ones used by the workflows.
2. Same page → Workflow permissions: "Read repository contents and packages permissions".
3. Same page → Fork pull request workflows: require approval for first-time contributors.
4. Settings → Rules → Rulesets → New branch ruleset, target `main`, enforcement Active, with these rules: require a pull request before merging; require status checks `tests` and `image` to pass; block force pushes; restrict deletions.
- Check: a pull request into `main` with a failing check shows the merge button blocked.
- Note: status checks appear in the ruleset picker only after they have run once, so S8.4 happens after the first successful pull request run.

**S9 — Optional: keep pinned actions current.** `.github/dependabot.yml` with the `github-actions` ecosystem and a weekly schedule opens pull requests that update SHA pins. This is subject to user approval.

**S10 — Documentation.** Add `docs/operations/ci.md` with what each workflow does, when it runs, how to read a failure, how to rerun, the platform settings from S8, and troubleshooting. Update `AGENTS.md`, whose line 9 currently says there is no CI. Update `docs/testing.md` (section 9 CI recommendations, now implemented), add a pointer in `README.md`, and update the Phase 8 status in `docs/plans/plan-docker.md`.

**S11 — Acceptance.** A pull request from `dev` into `main` shows `tests` and `image` green, and the ruleset blocks merging while a check is red.

---

## Tasks

| ID | Specs | Route | Status | Commit |
|---|---|---|---|---|
| T0 | — | inline | done | Phase 8 section of `plan-docker.md` corrected and this plan created |
| T1 | S1-S4 | inline | pending | — |
| T2 | S1, S2, S5-S7 | inline | pending | — |
| T3 | S10 (and S9 if accepted) | inline | pending | — |
| T4 | S8, S11 | user (push, web UI) + agent (log review) | pending | — |

### T1 — `tests.yml`

- [ ] Resolve the commit SHAs for the action tags in use.
- [ ] Write `.github/workflows/tests.yml` (S1-S4).
- [ ] Validate the syntax locally, for example with `actionlint` if it is available; otherwise do a structural YAML parse.
- [ ] Commit: `ci: add test suite workflow`.

### T2 — `image.yml`

- [ ] Write `.github/workflows/image.yml` (S1, S2, S5-S7).
- [ ] Reproduce the smoke and hygiene steps locally against the existing image.
- [ ] Commit: `ci: add image build and smoke workflow`.

### T3 — Documentation

- [ ] Write the docs in S10.
- [ ] Commit: `docs(ci): document workflows and repository settings`.

### T4 — First run and platform settings

- [ ] User pushes `dev`. The push needs credentials allowed to modify workflows; see R4.
- [ ] Confirm that `tests` runs on the push to `dev`.
- [ ] User opens a pull request from `dev` into `main`; confirm that `tests` and `image` both pass.
- [ ] User applies S8.1-S8.3, then S8.4 once the check names exist.
- [ ] Record each run's results and measured durations in `## Log`.

## Deferred (not in this plan)

- **Image publishing to `ghcr.io`:** implemented in `image.yml` on 2026-10-22 as part of the deployment phase; see `docs/operations/docker.md` ("Imagen publicada en GHCR").
- **Build layer caching (`type=gha`):** decide after measuring the uncached build time in T4. The roughly 6 GB of layers compete with the 10 GB per-repository cache.
- **Mocking the Qwen tokenizer** in `test_chunking_phase2_sliding_window.py` to remove the network dependency of S4.
- **Vulnerability scanning** of dependencies and the image: Phase 9.
- **End-to-end tests that call DeepSeek:** they require a repository secret and incur cost; out of scope.

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R1 | Runner disk too small for the ~6 GB image plus build layers | S5 records `df -h`; add a cleanup step if the first build fails |
| R2 | Hugging Face rate limiting or outage during the tests job or the image build | S4 cache for tests; rerun the image job; the model layer is fixed by revision |
| R3 | `torch` version drift between the workflow and `Dockerfile` (`ARG TORCH_VERSION`) | T1 uses the same `2.14.1`; S10 documents that both must change together |
| R4 | The push is rejected with "refusing to allow a Personal Access Token to create or update workflow ... without `workflow` scope" | Push over SSH, or with a token that has the `workflow` scope |
| R5 | `ubuntu-latest` changes its image version | Acceptable; pin `ubuntu-24.04` if a change breaks the build |

## Log

- **L1 (2026-10-20, user):** "Lo siguiente quiero saber si es crear flujo en github actions." Then: "listo, empieza corregiendo el plan. Ahora crea un plan de cómo se va a implementar y donde dicho yml, quiero saber si se crean dentro de este mismo proyecto o se tienen que cargar directamente en github. Que configuraciones o pasos se hacen dentro de la plataforma, etc..."
- **L2 (2026-10-20, user):** "Me confundi el repo es publico" — the repository is public; the earlier private assumption is void.
- **L3 (2026-10-20):** Premises verified locally. The runtime corpus is tracked in git. The container reaches `healthy` in about 27 s with a dummy `DEEPSEEK_API_KEY`. With an empty Hugging Face cache, the consultation (196), API (18), and diagnosis (205) suites pass, while the pipeline suite has 3 failures and 1 error from the real Qwen tokenizer (S4). `.env` is gitignored and absent from history.
- **Next step:** T1.
