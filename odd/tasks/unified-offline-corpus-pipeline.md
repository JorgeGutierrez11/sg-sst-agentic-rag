# Unified Offline Corpus Pipeline

Objective: implement the Phase 7 unified offline corpus build and validation workflow. Branch: `dev`. Delivery: work-unit commits on `dev` under the standing commit rules (no push). Test runner: `python -m unittest` and `python -m compileall`.

## Specs

S1. Implement the user request verbatim: "Implementalo sin hacer commits aun."

S2. Implement the command requirement verbatim: "tienen que tener un nombre un poco más claro que se entienda específicamente que estás trabajando en el pipeline offline de ingesta y valiacion de la misma."

S3. Implement the observability requirement verbatim: "se hagan valiaciones por las fases ejemplo se ejecut DOGX diga carga los documentoshecha, limpieza hecha y si falla algo muestre en qué parte del flujo fue que fallo."

S4. Preserve existing pipeline stage CLIs and call their reusable public functions from a thin orchestration layer; do not reimplement DOCX ingestion, cleanup, chunking, table processing, Chroma, or BM25 logic.

S5. Build all offline artifacts in staging, validate them before publication, and restore the previous published corpus if promotion fails. API downtime during promotion is an accepted Phase 7 constraint.

S6. Keep Phase 6 Docker work out of scope and add no dependencies or task runners.

S7. Implement the corrected plan verbatim: "ya con eso claro, implementa el plan" — Tasks 6-8 of `docs/plans/plan-fase-7-pipeline-offline.md` (findings R1-R10).

S8. Tests must never rebuild the real corpus: `build_offline_corpus` takes `project_root` and `operations` without defaults; only the CLI passes the real values.

## Tasks

- T1 | S2-S5 | delegated: one bounded implementation unit across the documented pipeline/test/doc surfaces; status: completed; evidence: `python -m unittest pipeline.tests.test_offline_orchestration pipeline.tests.test_artifact_validation pipeline.tests.test_offline_corpus` passed (9 tests); commit: deferred by S1.
- T2 | S2-S6 | delegated: focused verification and documentation reconciliation; status: partial; evidence: pipeline contracts passed (65 tests) and `python -m compileall pipeline agents` passed; `python -m unittest discover -s agents/consulta_normativa/tests` could not complete because the active environment lacks declared dependencies including `fastapi`, `pydantic`, `langgraph`, `chromadb`, `dotenv`, and `langchain_core`; commit: deferred by S1.
- T3 | S1 | inline: superseded by T4-T6 under the user's later instruction to implement the corrected plan; status: closed.
- T4 | S7-S8 (R1-R4, R8, R9) | inline: managed-entry promotion, backup outside workspace, `BaseException` restore, preflight phase, runtime message restore, `validate` exit 2, required build arguments, `.gitignore`; status: completed; evidence: 16 orchestration tests pass; mutants for whole-root promotion, in-workspace backup, and `Exception`-only restore each fail their test; Risk: item 1.
- T5 | S7 (R5, R6) | inline: CLI output contract and missing tests; status: completed; evidence: 33 focused tests, 163 pipeline tests, 196 consultation tests, 14 API tests pass with `.venv/bin/python`; `compileall` passes; `git status data/` clean.
- T6 | S7 (R7, R10) | inline: Spanish runbooks restored with managed-set, backup, and recovery sections; `plan-docker.md` set to in progress; `docs/testing.md` inventory and `AGENTS.md` entrypoints updated; status: completed.

## Log

- L1 (2026-10-18): Actúa como un Principal Software Engineer & Lead DevOps Specialist con amplia experiencia en arquitectura de software, pipelines de datos y automatización de infraestructura.

Tu objetivo es analizar la arquitectura del pipeline offline de carga de documentos y diseñar un nuevo plan de refactorización para simplificar su ejecución a máximo uno o dos comandos unificados.

---

### Contexto y Decisión Técnica:
Postergaremos temporalmente la Fase 6 de docs/plans/plan-docker.md para priorizar la simplificación operativa del pipeline offline (Fase 7). 

Actualmente, la alimentación del corpus documental requiere ejecutar múltiples comandos en serie de forma manual. Esto genera fricción operativa, riesgo de errores en la secuencia y dificulta la mantenibilidad.

### Objetivo de la Refactorización:
Unificar y automatizar todo el flujo del pipeline offline en **1 o 2 comandos como máximo**. Al ejecutar esta orden, el sistema debe procesar automáticamente los nuevos documentos y reconstruir/actualizar los artefactos e índices del corpus de principio a fin.

### Tareas Requeridas (Fase de Análisis y Diseño):

1. **Auditoría y Análisis de Arquitectura:**
   - Examina los componentes actuales del pipeline offline, las dependencias entre etapas (extracción, chunking, generación de embeddings, indexación BM25/Vectorial) y el estado guardado en memoria/diagramas del sistema.
   - Identifica cuellos de botella, posibles fallos en la ejecución secuencial y estrategias para unificar el proceso sin perder observabilidad.

2. **Propuesta Conceptual y Desafíos Técnicos:**
   - Propón las alternativas técnicas para orquestar la ejecución (ej. script de Python con CLI/Typer, invocación via `make`, o tareas integradas).
   - Lista los aspectos clave a considerar antes de implementar (manejo de errores, idempotencia, reintentos, validación de artefactos y logs).

### Importante:
- Mira egram hay reglas definidas importantes para commits y comentarios en codigo. 
- Seria ideal no tener la necesidad de recrear toda la ejecucion del pipeline, mira si es posible un script que lo que haga sea ejecutar los scripts ya existentes.

- L2 (2026-10-18): Algo importante de los dos comandos es que tienen que tener un nombre un poco más claro que se entienda específicamente que estás trabajando en el pipeline offline de ingesta y valiacion de la misma.
Además, requiero que se hagan valiaciones por las fases ejemplo se ejecut DOGX diga carga los documentoshecha, limpieza hecha y si falla algo muestre en qué parte del flujo fue que fallo.
En base a esto entonces ahora sí dentro de la carpeta @docs/plans/ crea el plan

- L3 (2026-10-18): Implementalo sin hacer commits aun.

- L4 (2026-10-18): Route: delegated because the implementation touches multiple non-trivial code, test, runtime, and operations-document surfaces. The allowed implementation plan is `docs/plans/plan-fase-7-pipeline-offline.md`.
- L5 (2026-10-18): Implemented S2-S6 with `pipeline.offline_corpus` build/validate commands, staged orchestration, read-only artifact validation, backup-and-restore publication, and operator documentation. No commit was made; S1 remains in force. Focused tests and pipeline contracts passed; the consultation suite is blocked by missing declared environment dependencies.
- L6 (2026-10-18): Review found R1-R10; the user requested "Edita el plan existente, en base a lo que hay, las mejoras y correcciones requeridas." Tasks 6-8 were added to the plan.
- L7 (2026-10-18): The user asked whether any test rebuilds the corpus; verified none does. Recommended making `project_root` and `operations` required so tests cannot reach the real corpus by omission.
- L8 (2026-10-18): The user replied "ya con eso claro, implementa el plan"; the safeguard was included as S8. Route: inline (one coupled change across orchestration, CLI, and tests; no writer trigger). An independent verifier runs because T4 names risk item 1.
- L9 (2026-10-18): Independent verifier: no blockers (4 accepted advisories). Commits on `dev`: `cde7323` refactor validation, `90546c1` staged build (risk item 1), `0cab2c4` CLI, then the documentation commit. Pending: manual smoke test with explicit authorization.
