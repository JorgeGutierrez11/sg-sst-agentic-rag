# CI GitHub Actions

Objective: implement Phase 8 continuous integration per `docs/plans/plan-fase-8-ci.md`. Branch: `dev`. Delivery: one commit per task, only when the user says so (no push). Test runner: structural YAML checks locally; real runs on GitHub in T4.

## Specs

S1-S11. Specs S1-S11 of `docs/plans/plan-fase-8-ci.md`, read in full through its `## Log`.

## Tasks

| ID | Specs | Route | Status | Evidence |
|---|---|---|---|---|
| T0 | — | inline | done | `b7ec024` |
| T1 | S1-S4 | inline (single file, no writer trigger) | done | structural checks + actionlint 1.7.12 clean; commit `ci: add test suite workflow` |
| T2 | S1, S2, S5-S7 | inline | done | local reproduction + negative probes; verifier no blockers; commit `ci: add image build and smoke workflow` |
| T3 | S10 (S9 if accepted) | inline | pending | — |
| T4 | S8, S11 | user + agent log review | pending | — |

## Log

- L1 (2026-10-20, user): "sí, haz el commit y empieza con T1"
- L2 (2026-10-20): Plan and app/ cleanup committed as `b7ec024`. Resolved pins from tags: `actions/checkout` v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1`, `actions/setup-python` v7.0.0 `5fda3b95a4ea91299a34e894583c3862153e4b97`, `actions/cache` v6.1.0 `55cc8345863c7cc4c66a329aec7e433d2d1c52a9`; inputs checked in each `action.yml` (all node24).
- L3 (2026-10-20): T1 written: `.github/workflows/tests.yml` (push dev/main, PR main, dispatch; `contents: read`; concurrency; 30 min timeout; SHA-pinned checkout/setup-python/cache; pip cache on `requirements.txt`; HF cache keyed on `pipeline/chunking/config.py`; CPU torch `2.14.1` before requirements; CPU/nvidia assertion; 4 suites + compileall). Local checks: YAML structure vs S1-S2, `bash -n` on every run block, actionlint 1.7.12 exit 0. Real run deferred to T4 (needs push). Scratch: action clones under the session scratchpad; `rhysd/actionlint:latest` image (103 MB) pulled locally.
- L4 (2026-10-20, user): "haz el commit y implementa el paso 2". T1 committed; T2 started.
- L5 (2026-10-21): T2 written: `.github/workflows/image.yml` (push/PR main, dispatch; `contents: read`; 45 min timeout; disk report; dummy `.env`; `docker compose build`; hygiene checks; `up --wait --wait-timeout 300`; curl `/health` and `/health/ready`; logs on failure; `down` always). actionlint 1.7.12 clean for both workflows. Local reproduction of every run step (build skipped, existing image) in a mktemp copy with a dummy `.env`: PASSED (healthy, `{"status":"ok"}`, `{"status":"ready"}`, image 5.92GB). Negative probes: hygiene with `python:3.14-slim` exits 1 (`No module named torch`); empty corpus makes `up --wait` fail (`unhealthy`), logs printed, `down` runs, 0 containers left. Scratch removed.
- L6 (2026-10-21): Independent verifier (S1-S7): no blockers, all met (S3/S4 counts and cache hit unverified until GitHub runs). Advisory 4 applied: `nvidia-` and `DEEPSEEK` checks now capture command output before grep in both workflows, so a failing `pip list` or `docker history` fails the step instead of passing silently (`bash -e` has no pipefail). Re-checked: actionlint exit 0; hygiene step positive exit 0; missing image makes the nvidia check exit 125 and the history check exit 1. Accepted advisories: duplicate `tests` run on a dev→main PR (push + pull_request); HF cache saves only on job success. Verifier scratch removed.
- L7 (2026-10-21, user): "Igual que los archivos de docker, divide los archivos del workflows en etapas." Added numbered Spanish stage headers (comments only): tests.yml 1-6, image.yml 1-8. Parsed YAML identical to the previous version for both files; actionlint exit 0.
- L8 (2026-10-21, user): "Haz el commit, el push lo haremos despues de configurar lo necesario en github". T2 committed; push deferred until GitHub settings are configured.
