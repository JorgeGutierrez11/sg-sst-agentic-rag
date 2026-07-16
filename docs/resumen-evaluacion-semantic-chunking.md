# Evaluación comparativa de child chunks para vector store legal SG-SST

Este documento evalúa los métodos de generación de `child_chunks` regenerados para el corpus normativo SG-SST. La evaluación se enfoca en su aptitud para alimentar un vector store de alto rendimiento orientado a normatividad legal colombiana.

## Decisión actual

El mejor candidato para indexación es:

```text
regex_constrained_semantic
```

Razón: combina el control estructural de reglas legales con cortes semánticos, conserva `100%` de offsets resueltos, elimina outliers mayores a `350` tokens y casi elimina microchunks. `sliding_window` queda como baseline técnico fuerte. `semantic_chunking` puro no se recomienda para indexación final por su alta tasa de offsets no resueltos, chunks huérfanos y outliers de tamaño.

## Marco de evaluación cualitativa

Cada método se califica de `1.0` a `5.0` en cuatro dimensiones:

| Dimensión | Qué mide | Fallo crítico |
|---|---|---|
| Cohesión semántica | Que el chunk contenga una idea jurídica o técnica completa. | Frases truncadas, numerales huérfanos o notas de procedencia aisladas. |
| Densidad informativa | Proporción de contenido útil frente a ruido o fragmentación. | Chunks demasiado cortos sin sustancia o demasiado largos con múltiples temas. |
| Anclaje estructural | Capacidad de conservar referencia legal y contexto jerárquico. | Obligaciones/listas sin artículo, parágrafo, sujeto obligado o contexto normativo. |
| Integridad de formato | Markdown limpio y sintaxis legible. | Palabras pegadas, saltos rotos, pérdida de títulos o caracteres corruptos. |

Los puntajes son una lectura analítica basada en métricas cuantitativas, revisión de extremos y muestras representativas. No sustituyen una evaluación de retrieval con consultas reales.

## Contexto: parent chunks regenerados

Los `parent_chunks` actuales son estructuralmente válidos, pero grandes e irregulares como unidad directa de recuperación.

```text
parents: 201
avg tokens: 375.23
min tokens: 33
max tokens: 2376
p50: 258
p75: 474
p90: 771
p95: 981
```

Validación estructural:

```text
JSONL válido: sí
IDs duplicados: 0
fuentes faltantes: 0
```

Advertencia: hay `4` parents con `hierarchy = {}`. Corresponden a bloques de preámbulo/document header y deberían marcarse explícitamente como `section_type: "preamble"` o equivalente.

Conclusión: los parents funcionan bien como unidades fuente trazables, pero no como unidad principal de retrieval. Los child chunks deben resolver tamaño, densidad y anclaje.

---

## Método 1: `sliding_window`

### Configuración detectada

```text
path: data/processed/chunks/sliding_window/chunks.jsonl
strategy: sliding_window
backend: langchain_recursive_character_text_splitter
split_reason: recursive_token_window
chunk_size: 350
chunk_overlap: 70
```

### Métricas

```text
chunks: 432
parents cubiertos: 201 / 201
IDs duplicados: 0
parent refs faltantes: 0
mismatches texto/offset contra parent: 0

avg tokens: 181.73
min tokens: 21
max tokens: 323
p50: 194.5
p75: 231.25
p90: 252.0
p95: 261.45

<30 tokens: 1 / 432 = 0.23%
<40 tokens: 4 / 432 = 0.93%
<50 tokens: 9 / 432 = 2.08%
>350 tokens: 0
>500 tokens: 0
>650 tokens: 0
unresolved offsets: 0
resolved offsets: 432 / 432 = 100%
```

### Evaluación por dimensión

| Dimensión | Puntaje | Análisis |
|---|---:|---|
| Cohesión semántica | 4.2 | Buena en general, pero los cortes son mecánicos. Puede separar o unir numerales legales sin respetar completamente la unidad normativa. |
| Densidad informativa | 4.8 | Muy buena distribución: casi no hay microchunks y no hay outliers grandes. |
| Anclaje estructural | 4.2 | Los offsets son perfectos y hereda metadata, pero algunos chunks inician en numerales/listas sin repetir encabezado legal explícito dentro del texto. |
| Integridad de formato | 4.9 | Markdown limpio y offsets exactos. Los gaps pequeños observados parecen separadores (`\n\n` o espacios), no corrupción. |

### Hallazgos

- Es el método más estable en tamaño.
- Es excelente como baseline técnico.
- Su principal debilidad no es la integridad, sino la falta de criterio jurídico en el punto exacto de corte.
- Para preguntas legales específicas puede recuperar fragmentos adecuados, pero en listas de obligaciones puede cortar por ventana y no por unidad legal.

### Veredicto

`sliding_window` es apto como baseline fuerte y alternativa segura. No es el candidato principal si el objetivo es maximizar unidad normativa y semántica.

---

## Método 2: `semantic_chunking`

### Configuración detectada

```text
path: data/processed/chunks/semantic_chunking/chunks.jsonl
strategy: semantic_chunking
backend: langchain_semantic_chunker
embedding_model: Qwen/Qwen3-Embedding-0.6B
threshold_type: gradient
threshold_amount: 95
split_reason: semantic_breakpoint
```

### Métricas

```text
chunks: 376
parents cubiertos: 201 / 201
IDs duplicados: 0
parent refs faltantes: 0
mismatches texto/offset contra parent en offsets resueltos: 0

avg tokens: 200.95
min tokens: 6
max tokens: 1581
p50: 135.0
p75: 257.0
p90: 458.0
p95: 617.75

<30 tokens: 43 / 376 = 11.44%
<40 tokens: 60 / 376 = 15.96%
<50 tokens: 76 / 376 = 20.21%
>350 tokens: 56 / 376 = 14.89%
>500 tokens: 33 / 376 = 8.78%
>650 tokens: 17 / 376 = 4.52%
unresolved offsets: 175 / 376 = 46.54%
resolved offsets: 201 / 376 = 53.46%
```

### Evaluación por dimensión

| Dimensión | Puntaje | Análisis |
|---|---:|---|
| Cohesión semántica | 2.4 | Produce varios cortes semánticamente pobres: títulos aislados, fragmentos muy cortos y chunks enormes que mezclan varios asuntos. |
| Densidad informativa | 2.2 | Tiene demasiados chunks menores a 50 tokens y demasiados chunks mayores a 500 tokens. La densidad es inestable. |
| Anclaje estructural | 2.5 | Casi la mitad de los offsets quedan unresolved. Además, algunos chunks empiezan lejos del encabezado legal o en medio de listas. |
| Integridad de formato | 4.7 | El texto no muestra corrupción masiva, pero el problema está en el corte, no tanto en el Markdown. |

### Hallazgos

- El método semántico puro no controla bien los extremos.
- Genera ejemplos críticos como encabezados aislados (`**Artículo 1.`) y chunks de más de `1000` tokens.
- Los offsets no resueltos reducen trazabilidad legal, lo cual es especialmente grave para un sistema normativo.
- Aunque Qwen3 puede capturar relaciones semánticas, el chunker puro no respeta suficiente la estructura documental legal.

### Veredicto

`semantic_chunking` puro no debe usarse como salida final para vector store. Puede servir como componente interno o experimento, pero necesita restricciones estructurales.

---

## Método 3: `regex_constrained_semantic`

### Configuración detectada

```text
path: data/processed/chunks/regex_constrained_semantic/chunks.jsonl
strategy: regex_constrained_semantic
backend: custom_regex_constrained_semantic
embedding_model: Qwen/Qwen3-Embedding-0.6B
threshold_type: gradient
threshold_amount: 95
split_reason: semantic_breakpoint_with_regex_constraints
```

### Métricas

```text
chunks: 361
parents cubiertos: 201 / 201
IDs duplicados: 0
parent refs faltantes: 0
mismatches texto/offset contra parent: 0

avg tokens: 208.91
min tokens: 9
max tokens: 350
p50: 210.0
p75: 291.0
p90: 328.0
p95: 337.0

<30 tokens: 1 / 361 = 0.28%
<40 tokens: 6 / 361 = 1.66%
<50 tokens: 8 / 361 = 2.22%
>350 tokens: 0
>500 tokens: 0
>650 tokens: 0
unresolved offsets: 0
resolved offsets: 361 / 361 = 100%
```

### Evaluación por dimensión

| Dimensión | Puntaje | Análisis |
|---|---:|---|
| Cohesión semántica | 4.7 | Los chunks tienden a preservar unidades legales completas o subunidades razonables. Corrige la mayoría de numerales huérfanos y outliers. |
| Densidad informativa | 4.6 | Casi no hay microchunks y no hay chunks excesivamente largos. El promedio es alto, pero aceptable para normatividad legal porque preserva contexto. |
| Anclaje estructural | 5.0 | Todos los offsets están resueltos y los cortes respetan mejor estructura legal. Es el método más trazable. |
| Integridad de formato | 4.9 | Conserva Markdown limpio, títulos y separación lógica. No se observaron fallos de formato relevantes. |

### Hallazgos

- Elimina completamente los outliers mayores a `350` tokens.
- Elimina offsets unresolved.
- Reduce casi a cero los microchunks.
- Es más grande en promedio que `sliding_window`, pero ese aumento compra más contexto legal y mejor unidad normativa.
- El único caso muy pequeño observado (`**RAFAEL PARDO RUEDA**`, 9 tokens) corresponde a firma o cierre documental; debería filtrarse o marcarse como contenido no indexable.

### Veredicto

`regex_constrained_semantic` es el mejor candidato actual para indexación del corpus normativo SG-SST. Es el único método que equilibra trazabilidad, tamaño máximo controlado, densidad útil y respeto por estructura legal.

---

## Recomendaciones de mejora

### 1. Usar `regex_constrained_semantic` como salida principal

Debe ser la estrategia preferida para construir el vector store.

### 2. Mantener `sliding_window` como baseline de evaluación

Es útil para comparar recall/faithfulness porque tiene excelente estabilidad técnica.

### 3. No indexar `semantic_chunking` puro como corpus final

Debe descartarse como salida final mientras mantenga:

```text
unresolved offsets: 46.54%
>500 tokens: 8.78%
<50 tokens: 20.21%
```

### 4. Filtrar o etiquetar chunks no sustantivos

Aplicar regla para firmas, nombres de ministros, notas de cierre o fragmentos sin valor normativo:

```text
indexable: false
content_type: signature | provenance_note | preamble | normative_text
```

Ejemplo detectado:

```text
**RAFAEL PARDO RUEDA**
```

### 5. Enriquecer anclaje textual opcional

Para chunks que empiezan en numeral o literal, considerar prefijar metadata contextual fuera del texto indexado o en campos separados:

```text
source_name
article
paragraph
numeral
parent_id
```

No conviene duplicar encabezados dentro del texto si eso infla embeddings; mejor conservarlo como metadata filtrable y como contexto de respuesta.

### 6. Evaluar con consultas reales

La decisión final debe validarse con preguntas SG-SST y métricas RAG:

- context relevance
- answer faithfulness
- answer relevance
- capacidad de citar fuente legal exacta

---

## Tabla comparativa final

| Método | Chunks | Avg tokens | Max | <30 | <50 | >350 | >500 | Unresolved | Cohesión | Densidad | Anclaje | Formato | Puntaje global | Veredicto |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `regex_constrained_semantic` | 361 | 208.91 | 350 | 0.28% | 2.22% | 0% | 0% | 0% | 4.7 | 4.6 | 5.0 | 4.9 | 4.8 | Mejor candidato para vector store. |
| `sliding_window` | 432 | 181.73 | 323 | 0.23% | 2.08% | 0% | 0% | 0% | 4.2 | 4.8 | 4.2 | 4.9 | 4.5 | Baseline técnico fuerte. |
| `semantic_chunking` | 376 | 200.95 | 1581 | 11.44% | 20.21% | 14.89% | 8.78% | 46.54% | 2.4 | 2.2 | 2.5 | 4.7 | 3.0 | No recomendado como salida final. |

## Ranking actual

1. `regex_constrained_semantic`
2. `sliding_window`
3. `semantic_chunking`

## Conclusión

Para un vector store legal de SG-SST, la prioridad no es solo reducir tokens. La prioridad es recuperar unidades normativas completas, trazables y sin ruido. Bajo ese criterio, `regex_constrained_semantic` es la mejor salida actual: mantiene offsets perfectos, evita outliers, reduce microchunks y preserva mejor la estructura legal colombiana.
