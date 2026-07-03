# Mapa: Fase de la metodología → Carpeta del repo

| Fase metodología            | Carpeta(s)                                                    |
|-------------------------------|------------------------------------------------------------------|
| Fase 1 — Revisión bibliográfica | (documento de tesis, no código)                                |
| Fase 2 — Corpus normativo      | `pipeline/`, `data/`                                            |
| Fase 3 — Sistema de evaluación | `evaluation/ares/`, `evaluation/datasets/`                      |
| Fase 4 Bloque A                | `agents/consulta_normativa/`                                    |
| Fase 4 Bloque B                | `agents/diagnostico_cumplimiento/`                               |
| Fase 4 Bloque C                | `app/`                                                           |
| Fase 5 — Evaluación del sistema| `evaluation/experiments/`, `evaluation/instruments/`, `evaluation/results/`, `evaluation/resultados_usuarios/` |
| Fase 6 — Análisis y documentación | `evaluation/results/`, `docs/` + documento de tesis          |

Esta tabla existe para que el jurado pueda ubicar cada fase.
La estructura física del repo NO sigue la numeración de fases —
sigue función (pipeline offline / agentes online / evaluación).
Ver docs/arquitectura.md para el razonamiento.
