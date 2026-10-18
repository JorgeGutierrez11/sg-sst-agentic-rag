# Mapa: Fase de la metodología → Carpeta del repo

> **Status:** `Current`
> **Audience:** academic-reviewer
> **Verified against:** [EISI_2026-04-09_14-25-36_pg1409.pdf](EISI_2026-04-09_14-25-36_pg1409.pdf), árbol del repositorio
> **Last verified:** 2026-10-18
> **Replacement:** N/A

| Fase metodología            | Carpeta(s)                                                    | Documentación |
|-------------------------------|------------------------------------------------------------------|---|
| Fase 1 — Revisión bibliográfica | (documento de tesis, no código)                                | [PDF metodológico](EISI_2026-04-09_14-25-36_pg1409.pdf) |
| Fase 2 — Corpus normativo      | `pipeline/`, `data/`                                            | [Construcción del corpus](operations/corpus-build.md), [chunking](architecture/chunking.md), [tablas](architecture/tables.md), [vectorización](architecture/vectorization.md), [BM25](architecture/bm25-sparse-retrieval.md), [comparación de chunking](experiments/chunking-strategy-comparison.md) |
| Fase 3 — Sistema de evaluación | `evaluation/ares/`, `evaluation/datasets/` (Conjunto A gold, Conjunto B optimización) | — |
| Fase 4 Bloque A                | `agents/consulta_normativa/`                                    | [Arquitectura de recuperación](architecture/retrieval.md), técnicas en `techniques/`, [snapshots R1–R3](historical/retrieval-snapshots/R1_hybrid_retrieval_implementacion.md) |
| Fase 4 Bloque B                | `agents/diagnostico_cumplimiento/`                               | [Referencia de la API](reference/api.md) |
| Fase 4 Bloque C                | `app/` (andamiaje vacío; sin implementación)                     | — |
| Fase 5 — Evaluación del sistema| `evaluation/experiments/`, `evaluation/instruments/`, `evaluation/results/`, `evaluation/resultados_usuarios/` | — |
| Fase 6 — Análisis y documentación | `evaluation/results/`, `docs/` + documento de tesis          | [README](../README.md) |

Esta tabla existe para que el jurado pueda ubicar cada fase.
La estructura física del repo NO sigue la numeración de fases —
sigue función (pipeline offline / agentes online / evaluación).
Las cinco etapas de la consulta normativa se representan con git tags, no con carpetas duplicadas.
Ver [la guía de carpetas](guia-carpetas.md) para el razonamiento.
