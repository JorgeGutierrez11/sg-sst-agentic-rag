# Evaluación comparativa de chunks para vector store legal SG-SST

Este documento resume la evaluación actual de `parent_chunks` y `child_chunks` regenerados para el corpus normativo SG-SST. El análisis se enfoca en calidad de datos para alimentar un vector store de alto rendimiento sobre normatividad legal colombiana.

## Decisión actual

La estrategia recomendada para indexación principal es:

```text
regex_constrained_semantic
```

Razón: es la única estrategia de child chunks que combina offsets exactos, máximo controlado de `350` tokens, referencias de tablas correctas, buena cohesión legal y preservación estructural. `sliding_window` queda como baseline técnico fuerte. `semantic_chunking` puro no se recomienda como salida final.

## Dimensiones de evaluación

Cada método se califica de `1.0` a `5.0` en cuatro dimensiones:

| Dimensión | Qué mide | Riesgo crítico |
|---|---|---|
| Cohesión semántica | Que el chunk contenga una idea jurídica o técnica comprensible. | Frases truncadas, numerales huérfanos, notas aisladas. |
| Densidad informativa | Proporción de contenido útil frente a ruido o dispersión. | Chunks muy cortos sin sustancia o muy largos con múltiples temas. |
| Anclaje estructural/legal | Capacidad de conservar contexto normativo y trazabilidad. | Obligaciones/listas sin artículo, parágrafo, sujeto obligado o fuente. |
| Integridad de formato | Markdown limpio y sintaxis legible. | Palabras pegadas, saltos rotos, pérdida de títulos o caracteres corruptos. |

Los puntajes combinan métricas cuantitativas, validación de offsets, revisión de extremos y cumplimiento del plan de referencias de tablas.

---

## Evaluación de parent chunks

Archivo evaluado:

```text
data/processed/chunks/parents.jsonl
```

### Métricas de tamaño

```text
parents: 138
avg tokens: 546.64
min tokens: 69
max tokens: 2376
p50: 426
p75: 654.25
p90: 897.6
p95: 1071.7
```

### Buckets de tamaño

| Bucket | Parents |
|---|---:|
| `<50` | 0 |
| `<80` | 1 |
| `<150` | 3 |
| `<250` | 3 |
| `250-350` | 36 |
| `351-500` | 39 |
| `501-650` | 21 |
| `651-1000` | 24 |
| `>1000` | 11 |

### Integridad estructural

| Validación | Resultado |
|---|---:|
| JSON inválidos | 0 |
| IDs duplicados | 0 |
| Referencias a fuente faltantes | 0 |
| Offsets inválidos | 0 |
| Mismatch texto/offset contra Markdown fuente | 0 |
| Overlaps | 0 |
| Gaps entre parents | 130 |
| Caracteres totales en gaps | 260 |
| Parents con jerarquía vacía | 4 |

Los gaps observados son de `2` caracteres, compatibles con separadores como `\n\n`. No parecen pérdida sustantiva de contenido.

### Estrategias detectadas

| Strategy | Count |
|---|---:|
| `parent_article_boundary` | 130 |
| `parent_document_preamble` | 8 |

| Split reason | Count |
|---|---:|
| `article_boundary` | 130 |
| `document_preamble_before_first_article` | 8 |

### Referencias de tablas en parents

| Validación | Resultado |
|---|---:|
| Parents con placeholder de tabla | 9 |
| Parents con `metadata.chunk.tables` | 9 |
| Referencias totales de tablas | 10 |
| Referencias a HTML faltantes | 0 |
| HTML huérfanos | 0 |
| Metadata con shape incorrecto | 0 |
| Campos de ruta persistidos | 0 |
| Refs de tabla sin placeholder propio | 0 |
| Placeholders sin refs | 0 |

La metadata cumple el plan: solo persiste `placeholder`, `table_index` y `source_stem`. No persiste rutas derivables como `html_path`, `text_path` o `markdown_path`.

### Evaluación cualitativa de parents

| Dimensión | Score | Análisis |
|---|---:|---|
| Cohesión semántica | 4.1 | Conservan unidades legales completas o grupos de artículos. Buenos como fuente, no siempre como unidad fina de retrieval. |
| Densidad informativa | 3.4 | Ya casi no hay parents pequeños, pero ahora hay muchos parents grandes: p75 `654.25`, p95 `1071.7`. |
| Anclaje estructural/legal | 4.6 | Offsets exactos, IDs únicos y buen vínculo a fuente. Quedan `4` preámbulos con `hierarchy = {}`. |
| Integridad de formato | 4.5 | Markdown generalmente limpio; conserva artículos, numerales, parágrafos y placeholders de tabla. |

### Veredicto de parents

Los parents están **aprobados como contenedores legales fuente**, pero **no deben usarse como unidad principal de retrieval**. Su tamaño actual confirma la arquitectura correcta:

```text
parent = contenedor legal trazable
child = unidad optimizada para vector store
```

---

## Child method 1: `sliding_window`

Archivo evaluado:

```text
data/processed/chunks/sliding_window/chunks.jsonl
```

### Métricas de integridad

| Validación | Resultado |
|---|---:|
| Chunks | 417 |
| Parents cubiertos | 138 / 138 |
| Parent refs faltantes | 0 |
| IDs duplicados | 0 |
| Offsets inválidos | 0 |
| Mismatches texto/offset contra parent | 0 |
| Offsets resueltos exactos | 417 / 417 |
| Offsets unresolved | 0 |

### Métricas de tamaño

```text
avg tokens: 190.2
min tokens: 14
max tokens: 323
p50: 205
p75: 236
p90: 256
p95: 263
```

| Bucket crítico | Count |
|---|---:|
| `<30` | 2 |
| `<40` | 3 |
| `<50` | 9 |
| `>350` | 0 |
| `>500` | 0 |
| `>650` | 0 |

### Referencias de tablas

| Validación | Resultado |
|---|---:|
| Chunks con placeholder | 12 |
| Chunks con `metadata.chunk.tables` | 12 |
| Referencias totales | 13 |
| Referencias HTML faltantes | 0 |
| Refs sin placeholder propio | 0 |
| Campos de ruta persistidos | 0 |
| Metadata con shape incorrecto | 0 |

Nota: hay más referencias que en parents porque el overlap de sliding windows puede duplicar placeholders en más de una ventana. Esto es esperable.

### Evaluación cualitativa

| Dimensión | Score | Análisis |
|---|---:|---|
| Cohesión semántica | 3.4 | Corta por ventana, no por unidad jurídica. Puede fragmentar obligaciones o agrupar partes de listas. |
| Densidad informativa | 3.8 | Tamaños muy controlados y casi sin microchunks, aunque el overlap puede duplicar contenido. |
| Anclaje estructural/legal | 4.2 | Offsets perfectos y metadata consistente; el texto no siempre conserva encabezado legal cercano. |
| Integridad de formato | 4.5 | Muy buena integridad técnica. Los cortes son mecánicos, no corruptos. |

### Veredicto

`sliding_window` es **técnicamente sólido** y debe conservarse como baseline. No es el mejor candidato semántico/legal porque prioriza estabilidad de tamaño sobre unidad normativa.

---

## Child method 2: `semantic_chunking`

Archivo evaluado:

```text
data/processed/chunks/semantic_chunking/chunks.jsonl
```

### Configuración detectada

```text
embedding_model: Qwen/Qwen3-Embedding-0.6B
threshold_type: gradient
```

### Métricas de integridad

| Validación | Resultado |
|---|---:|
| Chunks | 282 |
| Parents cubiertos | 138 / 138 |
| Parent refs faltantes | 0 |
| IDs duplicados | 0 |
| Offsets inválidos | 0 |
| Mismatches texto/offset resuelto | 0 |
| Offsets resueltos exactos | 117 / 282 |
| Offsets unresolved | 165 / 282 |

### Métricas de tamaño

```text
avg tokens: 267.96
min tokens: 2
max tokens: 1581
p50: 191.5
p75: 349.25
p90: 588
p95: 786.7
```

| Bucket crítico | Count |
|---|---:|
| `<30` | 20 |
| `<40` | 27 |
| `<50` | 39 |
| `>350` | 70 |
| `>500` | 41 |
| `>650` | 22 |

### Referencias de tablas

| Validación | Resultado |
|---|---:|
| Chunks con placeholder | 9 |
| Chunks con `metadata.chunk.tables` | 9 |
| Referencias totales | 10 |
| Referencias HTML faltantes | 0 |
| Refs sin placeholder propio | 0 |
| Campos de ruta persistidos | 0 |
| Metadata con shape incorrecto | 0 |

### Evaluación cualitativa

| Dimensión | Score | Análisis |
|---|---:|---|
| Cohesión semántica | 3.0 | Algunos cortes son semánticamente útiles, pero hay microchunks y chunks enormes que mezclan varios asuntos. |
| Densidad informativa | 2.8 | Alta variabilidad: chunks de `2` tokens y outliers de `1581` tokens. |
| Anclaje estructural/legal | 3.4 | Las tablas están bien referenciadas, pero `165` offsets unresolved debilitan trazabilidad. |
| Integridad de formato | 2.5 | Hay normalización/compactación que impide resolver offsets en muchos casos. |

### Veredicto

`semantic_chunking` puro **no se recomienda** como estrategia final. Aunque las tablas ya están correctamente asignadas, falla en control de tamaño y trazabilidad exacta.

---

## Child method 3: `regex_constrained_semantic`
Archivo evaluado:

```text
data/processed/chunks/regex_constrained_semantic/chunks.jsonl
```

### Configuración detectada

```text
embedding_model: Qwen/Qwen3-Embedding-0.6B
threshold_type: gradient
```

### Métricas de integridad

| Validación | Resultado |
|---|---:|
| Chunks | 330 |
| Parents cubiertos | 138 / 138 |
| Parent refs faltantes | 0 |
| IDs duplicados | 0 |
| Offsets inválidos | 0 |
| Mismatches texto/offset contra parent | 0 |
| Offsets resueltos exactos | 330 / 330 |
| Offsets unresolved | 0 |

### Métricas de tamaño

```text
avg tokens: 228.57
min tokens: 9
max tokens: 350
p50: 249.5
p75: 305
p90: 331
p95: 338
```

| Bucket crítico | Count |
|---|---:|
| `<30` | 3 |
| `<40` | 7 |
| `<50` | 10 |
| `>350` | 0 |
| `>500` | 0 |
| `>650` | 0 |

### Referencias de tablas

| Validación | Resultado |
|---|---:|
| Chunks con placeholder | 9 |
| Chunks con `metadata.chunk.tables` | 9 |
| Referencias totales | 10 |
| Referencias HTML faltantes | 0 |
| Refs sin placeholder propio | 0 |
| Campos de ruta persistidos | 0 |
| Metadata con shape incorrecto | 0 |

### Evaluación cualitativa

| Dimensión | Score | Análisis |
|---|---:|---|
| Cohesión semántica | 4.4 | Preserva mejor unidades legales y evita gran parte de la fragmentación mecánica. |
| Densidad informativa | 4.3 | Controla máximos y minimiza microchunks. Promedio alto, pero adecuado para contexto legal. |
| Anclaje estructural/legal | 4.6 | Offsets perfectos, tablas correctas y buena relación con parent legal. |
| Integridad de formato | 4.8 | Markdown consistente, placeholders preservados y sin corrupción relevante. |

### Veredicto

`regex_constrained_semantic` es la **mejor estrategia actual** para vector store. Mantiene trazabilidad exacta, controla tamaño máximo y respeta mejor la estructura legal.

---

## Cumplimiento del plan de referencias de tablas

Plan evaluado:

```text
docs/decisiones/plan-referencias-tablas-en-chunks.md
```

| Regla | Estado |
|---|---|
| Metadata mínima: `placeholder`, `table_index`, `source_stem` | Cumple |
| No persistir `html_path`, `text_path`, `markdown_path` | Cumple |
| Parents con tablas solo si contienen placeholder | Cumple |
| Child chunks con tablas solo si su propio texto contiene placeholder | Cumple |
| Referencias a HTML existentes | Cumple |
| HTML huérfanos | 0 |

La asignación de tablas queda correcta tanto en parents como en child chunks.

---

## Tabla comparativa final

| Método | Chunks | Avg | Max | `<30` | `<50` | `>350` | `>500` | Unresolved | Tablas OK | Cohesión | Densidad | Anclaje | Formato | Veredicto |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| `parents` | 138 | 546.64 | 2376 | n/a | 0 | 95 | 56 | 0 | Sí | 4.1 | 3.4 | 4.6 | 4.5 | Contenedor fuente, no retrieval directo. |
| `regex_constrained_semantic` | 330 | 228.57 | 350 | 3 | 10 | 0 | 0 | 0 | Sí | 4.4 | 4.3 | 4.6 | 4.8 | Mejor candidato para vector store. |
| `sliding_window` | 417 | 190.2 | 323 | 2 | 9 | 0 | 0 | 0 | Sí | 3.4 | 3.8 | 4.2 | 4.5 | Baseline técnico fuerte. |
| `semantic_chunking` | 282 | 267.96 | 1581 | 20 | 39 | 70 | 41 | 165 | Sí | 3.0 | 2.8 | 3.4 | 2.5 | No recomendado como salida final. |
