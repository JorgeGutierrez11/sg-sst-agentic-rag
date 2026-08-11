# Experimento: comparación de estrategias de chunking

La comparación actual normaliza la evidencia disponible sobre tres estrategias de child chunking para el corpus SG-SST. La decisión documentada es usar `regex_constrained_semantic` como salida recomendada para indexación principal, manteniendo `sliding_window` como baseline técnico y `semantic_chunking` como baseline experimental.

## Decisión

| Candidato | Decisión | Motivo principal |
|---|---|---|
| `sliding_window` | Baseline técnico | Tiene offsets exactos y tamaño controlado, pero corta de forma mecánica. |
| `semantic_chunking` | Baseline experimental | Puede producir chunks semánticos útiles, pero el reporte existente muestra alta variabilidad de tamaño y offsets no resueltos. |
| `regex_constrained_semantic` | Estrategia recomendada | Combina señales semánticas con spans exactos, máximo de 350 tokens y mejor trazabilidad legal. |

## Cómo regenerar la comparación implementada

Primero deben existir las salidas de chunking:

```bash
python -m pipeline.chunking.main build-parents
python -m pipeline.chunking.main build-sliding-window
python -m pipeline.chunking.main build-semantic
python -m pipeline.chunking.main build-regex-constrained-semantic
```

Luego se ejecuta el comparador:

```bash
python evaluation/experiments/chunking_comparison.py
```

Por defecto escribe:

```text
data/processed/chunks/comparison/metrics.json
data/processed/chunks/comparison/comparison_report.md
```

También acepta `--output-dir`, `--min-tokens`, `--max-tokens` y múltiples pares `--strategy-output STRATEGY PATH` para comparar archivos alternativos sin cambiar la configuración global.

## Métricas disponibles en código

| Métrica | Qué permite revisar |
|---|---|
| `total_chunks` | Granularidad de la estrategia. |
| `avg_token_count`, `min_token_count`, `max_token_count` | Control de tamaño. |
| `chunks_too_small`, `chunks_too_large` | Riesgo de microchunks o chunks demasiado extensos. |
| `overlap_count` | Duplicación esperada o ruido por ventanas solapadas. |
| `unresolved_offset_count` | Debilidad de trazabilidad contra el texto fuente. |
| `percentage_with_article_metadata` | Cobertura de anclaje jurídico por artículo. |
| `percentage_with_source_metadata` | Cobertura de fuente normativa. |
| `orphan_child_chunks` | Fallas de vínculo parent-child. |
| `unique_parent_count` | Cobertura de parents alcanzados. |

## Evidencia del reporte existente

`docs/resumen-evaluacion-semantic-chunking.md` registra una comparación más rica que incluye métricas cuantitativas, revisión de offsets, referencias de tablas y evaluación cualitativa. En ese reporte:

| Estrategia | Chunks | Máximo tokens | Offsets no resueltos | Veredicto reportado |
|---|---:|---:|---:|---|
| `sliding_window` | 417 | 323 | 0 | Baseline técnico fuerte. |
| `semantic_chunking` | 282 | 1581 | 165 | No recomendado como salida final. |
| `regex_constrained_semantic` | 330 | 350 | 0 | Mejor candidato para vector store. |


Para contrastar la implementación actual con esa evidencia, revisar también `evaluation/experiments/chunking_comparison.py`, la salida regenerable `data/processed/chunks/comparison/metrics.json` y el reporte regenerable `data/processed/chunks/comparison/comparison_report.md`.
