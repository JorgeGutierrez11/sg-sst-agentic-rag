# Plan de implementación: Parent-Child Chunking

Este documento define el estado actual del módulo de chunking del corpus normativo SG-SST con una arquitectura clara, moderna y evaluable. El objetivo operativo actual es comparar `sliding_window` como baseline mecánico contra `regex_constrained_semantic` como estrategia híbrida trazable; `semantic_chunking` puro queda como línea experimental/base, no como candidato principal por sus problemas de offsets no resueltos.

## Decisión técnica

| Área | Decisión |
|---|---|
| Sliding window | Usar `langchain-text-splitters`. |
| Semantic chunking | Mantener `SemanticChunker` como baseline experimental, no como técnica principal de tesis. |
| Regex-constrained semantic | Usar unidades textuales con offsets exactos, embeddings sobre unidades y chunks finales extraídos desde `parent.text`. |
| Modelo/tokenización | Usar `Qwen/Qwen3-Embedding-0.6B` como modelo por defecto y `AutoTokenizer` para conteo/offsets de tokens. |
| Metadata | Extraerla antes del child chunking mediante manifest, regex estructural y offsets calculados. |
| Salidas | Separar resultados por estrategia en `data/processed/chunks/<strategy>/`. |
| Comparación | Generar reportes en `data/processed/chunks/comparison/`. |

## Dependencias por fase

```bash
pip install langchain-text-splitters tiktoken langchain-experimental langchain-huggingface sentence-transformers transformers
```

Fase 2 usa `langchain-text-splitters` y `tiktoken`. Fase 3 usa `langchain-experimental`, `langchain-huggingface` y `sentence-transformers` para semantic chunking con embeddings. Fase 4 agrega dependencia efectiva sobre `transformers` porque el conteo de tokens y los offsets de ventanas se hacen con `AutoTokenizer`.

### PRINCIPIOS DE DISEÑO COMPLEMENTARIOS (CRÍTICO)

Para evitar la sobreingeniería, la fragmentación innecesaria y mantener la legibilidad, aplica estrictamente las siguientes directivas de diseño de software:

1. **Principio YAGNI (You Aren't Gonna Need It):** No crees abstracciones, interfaces, clases auxiliares o envoltorios (wrappers) para casos hipotéticos futuros. Programa exclusivamente para los requerimientos del presente.
2. **Principio KISS (Keep It Simple, Stupid):** Valora la simplicidad por sobre la elegibilidad académica del código. Si una funcionalidad se puede resolver de forma clara, lineal y legible en 15 líneas dentro de un archivo cohesionado, NO la separes en 3 archivos o subcarpetas diferentes.
3. **Cohesión Local sobre Separación Modular Absoluta:** Prefiere agrupar funciones estrechamente relacionadas en el mismo módulo (archivo) en lugar de crear micro-archivos individuales. La fragmentación excesiva introduce una carga cognitiva innecesaria.
4. **Acoplamiento vs. Legibilidad:** No apliques Clean Code de manera dogmática. Si el costo de desacoplar una función implica crear múltiples DTOs y mapeadores redundantes que complican el flujo de lectura (Traceability), opta por un diseño más compacto y acoplado localmente.

## Estructura de Fase 1

La estructura actual usa un layout compacto orientado por feature. El objetivo no es fragmentar por responsabilidad microscópica, sino mantener el flujo de lectura claro: infraestructura local compartida, análisis estructural normativo y splitter jerárquico.

```txt
pipeline/chunking/
├── __init__.py
├── main.py                  # Orquestador principal del pipeline de chunking
├── core/                    # Infraestructura local compartida
│   ├── __init__.py
│   ├── config.py            # Configuración de rutas, defaults y salidas por estrategia
│   ├── cli.py               # CLI con subcomandos explícitos por fase
│   └── io_jsonl.py          # Serialización JSONL
├── structural_analysis/     # Feature 1: detección de estructura normativa/metadata
│   ├── __init__.py
│   ├── boundaries.py        # Detección de fronteras legales
│   ├── patterns.py          # Patrones legales regex
│   └── metadata_infer.py    # Inferencia determinística de metadata
└── hierarchical_splitter/   # Feature 2: split jerárquico e ingestión
    ├── __init__.py
    ├── parent_builder.py       # Construcción de parent chunks
    ├── child_splitter/         # Child chunks por técnica implementada
    │   ├── __init__.py         # API pública y wrappers lazy para dependencias opcionales
    │   ├── shared.py           # Helpers compartidos de child chunks
    │   ├── sliding_window.py   # Baseline mecánico de Fase 2
    │   ├── semantic.py         # SemanticChunker puro de Fase 3
    │   └── regex_constrained_semantic.py # Híbrido trazable de Fase 4
    ├── models.py               # Contratos de datos
    └── tokenization.py         # AutoTokenizer para conteo y offsets de tokens
```

El uso de Fase 1 queda centrado en `main.py` con un subcomando explícito:

```bash
python -m pipeline.chunking.main build-parents
```

Fase 2 agrega un segundo subcomando explícito, sin `--strategy` genérico ni abstracciones futuras:

```bash
python -m pipeline.chunking.main build-sliding-window
```

Fase 3 agrega un tercer subcomando explícito para el baseline semántico puro:

```bash
python -m pipeline.chunking.main build-semantic
```

Fase 4 agrega el subcomando explícito de la estrategia híbrida trazable:

```bash
python -m pipeline.chunking.main build-regex-constrained-semantic
```

No se usa un comando genérico `--strategy`: cada técnica implementada tiene su subcomando concreto para mantener depuración simple.

---

# Fase 1: Bases generales

## Objetivo

Crear la base común del pipeline para que todas las estrategias usen la misma entrada, produzcan la misma salida y puedan compararse con justicia.

## Tareas

1. Borrar los scripts actuales de `pipeline/chunking/` y reconstruirlos con responsabilidades separadas.
2. Crear los modelos base:
   - `ParentChunk`
   - `ChildChunk`
3. Crear la CLI en `core/cli.py`.
4. Crear la orquestación en `main.py`.
5. Crear serialización JSONL en `core/io_jsonl.py`.
6. Crear configuración central en `core/config.py`.
7. Crear extracción determinística de metadata en `structural_analysis/metadata_infer.py`.
8. Definir regex estructural mediante inspección directa del Markdown limpio.

## Metadata

La metadata no debe extraerse dentro de cada estrategia. Debe generarse antes del child chunking.

Flujo:

```txt
Markdown limpio
→ extracción determinística de metadata
→ parent chunks enriquecidos
→ child chunks con metadata heredada + metadata propia
```

Fuentes de metadata:

| Fuente | Metadata |
|---|---|
| Manifest controlado | norma, año, entidad, tipo documental, archivo original, fuente oficial |
| Regex/parser estructural | título, capítulo, sección, artículo, parágrafo, numeral, literal |
| Código del pipeline | `start_char`, `end_char`, `token_count`, estrategia, overlap, razón del corte |

Formato esperado:

```json
{
  "metadata": {
    "inherited": {
      "source_name": "Decreto 1072 de 2015",
      "document_type": "decreto",
      "year": 2015,
      "article": "2.2.4.6.8",
      "legal_source": "official"
    },
    "chunk": {
      "strategy": "regex_constrained_semantic",
      "backend": "custom_regex_constrained_semantic",
      "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
      "chunk_index": 3,
      "offset_status": "resolved",
      "unit_count": 4,
      "unit_types": ["paragraph", "sentence"],
      "size_adjustment": "none",
      "split_reason": "semantic_breakpoint_with_regex_constraints"
    }
  }
}
```

## Resultado esperado

La fase termina cuando el pipeline puede:

- leer documentos Markdown limpios;
- construir parent chunks;
- enriquecerlos con metadata;
- escribir JSONL válido;
- ejecutar `python -m pipeline.chunking.main --help`.

---

# Fase 2: Sliding Window

## Objetivo

Implementar la estrategia base mecánica usando herramientas de LangChain.

## Técnica

Usar:

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
```

Preferencia:

```python
RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=max_tokens,
    chunk_overlap=overlap_tokens,
)
```

## Reglas

- No usar regex legal.
- No usar embeddings.
- No usar semantic chunking.
- Mantener esta estrategia como baseline mecánico.

## Salida

```txt
data/processed/chunks/sliding_window/chunks.jsonl
```

Implementado en Fase 2:

```txt
pipeline/chunking/hierarchical_splitter/child_splitter/sliding_window.py
```

## Metadata específica

```json
{
  "strategy": "sliding_window",
  "backend": "langchain_recursive_character_text_splitter",
  "chunk_size": 350,
  "chunk_overlap": 70,
  "split_reason": "recursive_token_window"
}
```

## Resultado esperado

La fase termina cuando se puedan generar child chunks con tamaño y overlap controlados, preservando `parent_id`, offsets y metadata heredada.

Estado: **implementado** como baseline mecánico con `RecursiveCharacterTextSplitter.from_tiktoken_encoder`, salida en `data/processed/chunks/sliding_window/chunks.jsonl`, validación de `chunk_size`/`chunk_overlap` y errores CLI controlados.

---

# Fase 3: Semantic Chunking

## Objetivo

Implementar semantic chunking real usando embeddings multilingües.

## Backend semántico

El backend semántico se agrega en Fase 3 dentro del paquete `child_splitter/`, sin factory ni framework genérico de estrategias.

```python
from langchain_huggingface import HuggingFaceEmbeddings

EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"


def create_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )
```

Usar `SemanticChunker`:

```python
from langchain_experimental.text_splitter import SemanticChunker
```

## Reglas

- No usar regex legal como restricción.
- No dividir por artículo o parágrafo.
- Esta estrategia debe medir la ventaja de usar embeddings frente a sliding window.

## Salida

```txt
data/processed/chunks/semantic_chunking/chunks.jsonl
```

Implementado en Fase 3:

```txt
pipeline/chunking/hierarchical_splitter/child_splitter/semantic.py
```

## Metadata específica

```json
{
  "strategy": "semantic_chunking",
  "backend": "langchain_semantic_chunker",
  "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
  "split_reason": "semantic_breakpoint"
}
```

## Resultado esperado

La fase termina cuando se puedan generar chunks por cambios semánticos y comparar su recuperación contra sliding window.

Estado: **implementado** con `SemanticChunker` de `langchain-experimental`, embeddings configurables mediante `langchain-huggingface`, modelo por defecto `Qwen/Qwen3-Embedding-0.6B`, salida en `data/processed/chunks/semantic_chunking/chunks.jsonl`, thresholds configurables por CLI y errores controlados para JSONL o dependencias/modelo.

Nota crítica de evaluación: `SemanticChunker` reconstruye texto internamente y puede producir chunks que no son substring exacto de `parent.text`. Por eso `offset_status: unresolved` en esta estrategia debe tratarse como falla de trazabilidad, no como éxito. Esta limitación motivó la Fase 4.

Notas de evaluación y pruebas:

- Las pruebas unitarias monkeypatchean la creación del splitter semántico para evitar descargas pesadas del modelo durante `unittest`.
- El smoke real requiere que las dependencias estén instaladas y que el modelo esté disponible en caché o pueda descargarse sin bloquear el entorno.
- Las métricas comparativas siguen pendientes para Fase 5: número de chunks, distribución de tokens, trazabilidad normativa, context relevance, answer faithfulness, answer relevance y citation accuracy.

---

# Fase 4: Regex-constrained Semantic Chunking

## Objetivo

Construir la estrategia híbrida principal para el corpus normativo SG-SST: una técnica semántica que preserve trazabilidad exacta para citación normativa.

La decisión clave es NO usar `SemanticChunker.create_documents()` para emitir chunks finales. En su lugar, el código detecta unidades textuales con offsets, calcula cortes semánticos sobre esas unidades y emite chunks cortando directamente desde `parent.text`.

## Estrategia implementada

Flujo:

```txt
parent text
→ extraer unidades exactas con regex/texto preservando offsets
→ calcular embeddings por unidad
→ medir distancia semántica entre unidades consecutivas
→ definir breakpoints por percentile/gradient
→ agrupar unidades contiguas
→ ajustar chunks pequeños y grandes por tokens reales de AutoTokenizer
→ emitir cada child chunk como parent.text[start:end]
```

Reglas de trazabilidad:

- todo chunk emitido debe tener `offset_status: resolved`;
- `child.text` debe ser exactamente igual a `parent.text[start:end]`;
- si una unidad queda demasiado grande, el fallback usa offsets del `AutoTokenizer`, no regex token matching;
- los tokens se cuentan con `AutoTokenizer.from_pretrained(DEFAULT_EMBEDDING_MODEL, use_fast=True)` sin special tokens.

## Salida

```txt
data/processed/chunks/regex_constrained_semantic/chunks.jsonl
```

Implementado en Fase 4:

```txt
pipeline/chunking/hierarchical_splitter/child_splitter/regex_constrained_semantic.py
```

## Metadata específica

```json
{
  "strategy": "regex_constrained_semantic",
  "backend": "custom_regex_constrained_semantic",
  "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
  "breakpoint_threshold_type": "gradient",
  "breakpoint_threshold_amount": 95,
  "offset_status": "resolved",
  "unit_count": 4,
  "unit_types": ["paragraph", "sentence"],
  "size_adjustment": "none",
  "split_reason": "semantic_breakpoint_with_regex_constraints"
}
```

## Resultado esperado

La fase termina cuando la estrategia híbrida pueda preservar estructura jurídica y, al mismo tiempo, dividir bloques extensos por coherencia semántica.

Estado: **implementado** con estrategia `regex_constrained_semantic`, salida en `data/processed/chunks/regex_constrained_semantic/chunks.jsonl`, subcomando `build-regex-constrained-semantic`, tests de offsets resueltos, slicing exacto contra `parent.text`, merge de chunks pequeños, split de chunks grandes y errores CLI controlados.

---

# Fase 5: Comparación y decisión

## Objetivo

Comparar las estrategias con métricas técnicas, normativas y de RAG. La comparación principal actual debe priorizar `sliding_window` vs `regex_constrained_semantic`; `semantic_chunking` puro puede conservarse como baseline experimental para demostrar la limitación de trazabilidad.

## Entradas

```txt
data/processed/chunks/sliding_window/chunks.jsonl
data/processed/chunks/semantic_chunking/chunks.jsonl
data/processed/chunks/regex_constrained_semantic/chunks.jsonl
```

## Salidas

```txt
data/processed/chunks/comparison/
├── metrics.json
└── comparison_report.md
```

## Métricas mínimas

| Tipo | Métricas |
|---|---|
| Técnicas | total de chunks, tokens promedio, chunks pequeños, chunks grandes, overlap, offsets no resueltos |
| Normativas | porcentaje con artículo, fuente, parent válido, frontera legal preservada |
| RAG | context relevance, answer faithfulness, answer relevance, citation accuracy |

## Criterio de decisión

La estrategia ganadora no debe elegirse por intuición. Debe seleccionarse con base en evidencia.

Hipótesis inicial:

> `regex_constrained_semantic` debería ofrecer mejor equilibrio entre trazabilidad normativa y relevancia semántica.

Regla de interpretación: `unresolved_offset_count` es una métrica negativa. En SG-SST, los chunks sin offsets confiables reducen capacidad de citación y auditoría.

---

# Checklist de implementación

- [x] Instalar dependencias de Fase 2 (`langchain-text-splitters`, `tiktoken`).
- [x] Actualizar `requirements.txt` cuando se agreguen dependencias de estrategias.
- [x] Borrar scripts actuales de `pipeline/chunking/` y mantener el raíz limpio.
- [x] Crear estructura nueva por responsabilidad para Fase 1.
- [x] Implementar metadata determinística para parent chunks.
- [x] Ajustar patrones legales mediante inspección directa del Markdown limpio.
- [x] Implementar sliding window con LangChain.
- [x] Implementar semantic chunking puro como baseline experimental.
- [x] Implementar híbrido `regex_constrained_semantic` con offsets resueltos.
- [x] Migrar conteo y offsets de tokens a `AutoTokenizer`.
- [ ] Generar salidas por estrategia.
- [ ] Generar reporte comparativo.
- [ ] Revisar manualmente trazabilidad de citas normativas.

# Verificación mínima

```bash
python -m compileall "pipeline/chunking" "pipeline/tests"
python -m unittest discover -s pipeline/tests
python -m pipeline.chunking.main --help
python -m pipeline.chunking.main build-sliding-window --help
python -m pipeline.chunking.main build-semantic --help
python -m pipeline.chunking.main build-regex-constrained-semantic --help
python -m pipeline.chunking.main build-parents
```

No se usa un comando genérico `--strategy`: cada fase agrega solo el comando concreto que necesita.
