# Resumen de evaluación de semantic chunking

Este documento resume las configuraciones de `SemanticChunker` evaluadas para el corpus normativo SG-SST. El objetivo es elegir una configuración base para retrieval que balancee tamaño útil, baja fragmentación, control de chunks grandes y trazabilidad mediante offsets.

## Decisión actual

La mejor configuración cuantitativa evaluada hasta ahora es:

```python
DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_TYPE = "gradient"
DEFAULT_SEMANTIC_BREAKPOINT_THRESHOLD_AMOUNT = 85
```

Razón principal: mantiene buen promedio de tokens, reduce los chunks grandes frente a otras configuraciones y tiene el mejor porcentaje de offsets resueltos/unresolved entre los candidatos fuertes.

Sin embargo, todavía queda un problema estructural: semantic chunking puro deja algunos outliers grandes, especialmente un chunk de `708` tokens en obligaciones del empleador. Para una fase posterior conviene evaluar una regla híbrida: si un chunk semántico supera un máximo definido, partirlo por numerales/listas.

## Criterios usados

| Métrica | Objetivo decente |
|---|---:|
| Promedio de tokens | 90–150 |
| Máximo de tokens | Ideal <=650; tolerable <=700 |
| Chunks >500 tokens | <=3% |
| Chunks <30 tokens | <=15%; tolerable <=20% |
| Offsets unresolved | <=55%; tolerable <=60% |

## Resultados comparados

| Configuración | Total chunks | Avg tokens | Max tokens | <30 tokens | >350 tokens | >500 tokens | Unresolved offsets | Lectura |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `gradient=85` | 463 | 108.86 | 708 | 18.79% | 2.59% | 1.08% | 43.84% | Mejor candidato cuantitativo actual. |
| `gradient=90` | 409 | 123.23 | 708 | 18.09% | 6.11% | 1.96% | 45.48% | Bueno, pero más chunks grandes que `gradient=85`. |
| `gradient=95` | 368 | 136.96 | 973 | 17.12% | 8.15% | 2.72% | 45.65% | Buena trazabilidad, malos outliers. |
| `interquartile=0.85` | 402 | 125.38 | 916 | 16.92% | 5.72% | 2.24% | 53.98% | Decente, pero peor trazabilidad y outliers. |
| `interquartile=0.95` | 380 | 132.63 | 916 | 16.84% | 6.58% | 2.63% | 54.47% | Similar a `0.85`, sin mejora clara. |
| `interquartile=1.5` | 264 | 190.91 | 1228 | 9.47% | 15.15% | 6.06% | 70.08% | Demasiado grueso; no recomendado. |
| `standard_deviation=0.75` | 526 | 95.82 | 672 | 22.2% | No medido | 0.76% | 50.0% | Controla grandes, pero fragmenta demasiado. |
| `percentile=85` | 463 | 108.86 | 672 | 19.0% | No medido | 1.08% | 52.7% | Baseline fuerte previo; buen balance general. |

## Ranking actual

1. `gradient=85`
2. `percentile=85`
3. `gradient=90`
4. `interquartile=0.85`
5. `interquartile=0.95`
6. `gradient=95`
7. `standard_deviation=0.75`
8. `interquartile=1.5`

## Hallazgos importantes

- `interquartile=1.5` genera pocos chunks, pero son demasiado grandes y con mala trazabilidad.
- `interquartile=0.85` y `0.95` son decentes, pero no superan claramente a `gradient=85`.
- `gradient=95` mejora trazabilidad, pero deja outliers grandes de hasta `973` tokens.
- `gradient=90` reduce esos outliers, pero `gradient=85` mejora aún más la proporción de chunks grandes.
- `gradient=85` conserva un problema: el máximo sigue en `708` tokens.
- Los microchunks siguen apareciendo en varias configuraciones, por ejemplo fragmentos como `Parágrafo.`, `3.`, `10.` o encabezados de artículo aislados.

## Recomendación

Usar `gradient=85` como candidato principal para la siguiente etapa de pruebas, pero no tratarlo como solución final cerrada.

Antes de pasar a indexación definitiva, evaluar una mejora híbrida simple:

1. Generar chunks semánticos con `gradient=85`.
2. Detectar chunks mayores a un umbral, por ejemplo `650` tokens.
3. Dividir esos chunks grandes por numerales, literales o listas legales cuando sea posible.
4. Evitar crear microchunks sueltos; fusionar fragmentos menores a `30` tokens con un vecino cercano.

Esta ruta mantiene la calidad semántica general y corrige los dos problemas persistentes: outliers grandes y fragmentos demasiado pequeños.
