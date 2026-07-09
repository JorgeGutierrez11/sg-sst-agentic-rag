# Plan de implementación: Parent-Child Chunking

Este documento define el plan para reconstruir el módulo de chunking del corpus normativo SG-SST con una arquitectura más clara, moderna y evaluable. El objetivo es comparar dos estrategias base y una estrategia híbrida diseñada para documentos normativos colombianos.

## Decisión técnica

| Área | Decisión |
|---|---|
| Sliding window | Usar `langchain-text-splitters`. |
| Semantic chunking | Usar embeddings con `intfloat/multilingual-e5-base`. |
| Hybrid chunking | Combinar regex legal, semantic chunking y fallback recursivo. |
| Metadata | Extraerla antes del child chunking mediante manifest, regex estructural y offsets calculados. |
| Salidas | Separar resultados por estrategia en `data/processed/chunks/<strategy>/`. |
| Comparación | Generar reportes en `data/processed/chunks/comparison/`. |

## Dependencias por fase

```bash
pip install langchain-text-splitters tiktoken
```

Fase 2 instala y registra solo `langchain-text-splitters` y `tiktoken`. Las dependencias de semantic chunking (`langchain-experimental`, `langchain-huggingface`, `sentence-transformers`) se agregan únicamente cuando se implemente la Fase 3.

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
│   ├── config.py            # Configuración de rutas y defaults
│   ├── cli.py               # CLI de Fase 1
│   └── io_jsonl.py          # Serialización JSONL
├── structural_analysis/     # Feature 1: detección de estructura normativa/metadata
│   ├── __init__.py
│   ├── boundaries.py        # Detección de fronteras legales
│   ├── patterns.py          # Patrones legales regex
│   └── metadata_infer.py    # Inferencia determinística de metadata
└── hierarchical_splitter/   # Feature 2: split jerárquico e ingestión
    ├── __init__.py
    ├── parent_builder.py    # Construcción de parent chunks
    ├── child_splitter.py    # Sliding-window child chunks de Fase 2
    ├── models.py            # Contratos de datos
    └── tokenization.py      # Estimación determinística de tokens
```

El uso de Fase 1 queda centrado en `main.py` con un subcomando explícito:

```bash
python -m pipeline.chunking.main build-parents
```

Fase 2 agrega un segundo subcomando explícito, sin `--strategy` genérico ni abstracciones futuras:

```bash
python -m pipeline.chunking.main build-sliding-window
```

Semantic chunking y regex-constrained semantic siguen siendo adiciones futuras de Fases 3 y 4. Cualquier contrato futuro debe permanecer mínimo y justificado por uso real.

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
      "backend": "langchain_semantic_chunker",
      "embedding_model": "intfloat/multilingual-e5-base",
      "chunk_index": 3,
      "split_reason": "semantic_split_inside_legal_boundary"
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
pipeline/chunking/hierarchical_splitter/child_splitter.py
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

Agregar backend semántico solo cuando se implemente la Fase 3. No mantener contratos, wrappers ni constantes semánticas antes de que exista uso real.

```python
from langchain_huggingface import HuggingFaceEmbeddings

EMBEDDING_MODEL = "intfloat/multilingual-e5-base"


def create_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
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

Implementación futura:

```txt
pipeline/chunking/hierarchical_splitter/child_splitter.py
```

## Metadata específica

```json
{
  "strategy": "semantic_chunking",
  "backend": "langchain_semantic_chunker",
  "embedding_model": "intfloat/multilingual-e5-base",
  "split_reason": "semantic_breakpoint"
}
```

## Resultado esperado

La fase termina cuando se puedan generar chunks por cambios semánticos y comparar su recuperación contra sliding window.

---

# Fase 4: Regex-constrained Semantic Chunking

## Objetivo

Construir la estrategia híbrida propuesta para el corpus normativo SG-SST.

Esta fase no debe partir de regex genéricos. Los patrones deben ajustarse mediante inspección directa de los `.md` limpios del corpus, manteniendo regex simples y legibles en el código.

## Paso 1: inspección directa de Markdown limpio

Revisar directamente los `.md` procesados para identificar patrones como:

- artículos;
- capítulos;
- secciones;
- parágrafos;
- numerales;
- literales;
- tablas;
- encabezados Markdown;
- saltos o formatos irregulares.

No existe un módulo ni comando dedicado para este análisis; la evidencia se obtiene leyendo muestras del corpus limpio y ajustando `structural_analysis/patterns.py` cuando sea necesario.

## Paso 2: regex estructural

Actualizar `structural_analysis/patterns.py` y `structural_analysis/boundaries.py` con patrones basados en evidencia del corpus.

Ejemplos iniciales, sujetos a validación:

```python
ARTICLE_PATTERN = r"(?i)^#+\s*art[ií]culo\s+([\d\.]+)"
PARAGRAPH_PATTERN = r"(?i)^\s*par[aá]grafo"
NUMERAL_PATTERN = r"(?m)^\s*\d+[\.)]\s+"
LITERAL_PATTERN = r"(?m)^\s*[a-z]\)\s+"
```

## Paso 3: estrategia híbrida

Flujo:

```txt
parent text
→ detectar bloques legales con regex
→ si el bloque es pequeño: mantenerlo completo
→ si el bloque es grande: dividirlo con SemanticChunker
→ si aún queda demasiado grande: usar RecursiveCharacterTextSplitter
→ agregar metadata legal y técnica
```

## Salida

```txt
data/processed/chunks/regex_constrained_semantic/chunks.jsonl
```

Implementación futura:

```txt
pipeline/chunking/hierarchical_splitter/child_splitter.py
```

## Metadata específica

```json
{
  "strategy": "regex_constrained_semantic",
  "legal_boundary_detected": true,
  "boundary_type": "article",
  "semantic_backend": "langchain_semantic_chunker",
  "embedding_model": "intfloat/multilingual-e5-base",
  "fallback_splitter": "langchain_recursive_character_text_splitter",
  "split_reason": "semantic_split_inside_legal_boundary"
}
```

## Resultado esperado

La fase termina cuando la estrategia híbrida pueda preservar estructura jurídica y, al mismo tiempo, dividir bloques extensos por coherencia semántica.

---

# Fase 5: Comparación y decisión

## Objetivo

Comparar las tres estrategias con métricas técnicas, normativas y de RAG.

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
| Técnicas | total de chunks, tokens promedio, chunks pequeños, chunks grandes, overlap |
| Normativas | porcentaje con artículo, fuente, parent válido, frontera legal preservada |
| RAG | context relevance, answer faithfulness, answer relevance, citation accuracy |

## Criterio de decisión

La estrategia ganadora no debe elegirse por intuición. Debe seleccionarse con base en evidencia.

Hipótesis inicial:

> `regex_constrained_semantic` debería ofrecer mejor equilibrio entre trazabilidad normativa y relevancia semántica.

---

# Checklist de implementación

- [x] Instalar dependencias de Fase 2 (`langchain-text-splitters`, `tiktoken`).
- [x] Actualizar `requirements.txt` cuando se agreguen dependencias de estrategias.
- [x] Borrar scripts actuales de `pipeline/chunking/` y mantener el raíz limpio.
- [x] Crear estructura nueva por responsabilidad para Fase 1.
- [x] Implementar metadata determinística para parent chunks.
- [x] Ajustar patrones legales mediante inspección directa del Markdown limpio.
- [x] Implementar sliding window con LangChain.
- [ ] Implementar semantic chunking con `intfloat/multilingual-e5-base`.
- [ ] Implementar híbrido con regex + semantic + recursive fallback.
- [ ] Generar salidas por estrategia.
- [ ] Generar reporte comparativo.
- [ ] Revisar manualmente trazabilidad de citas normativas.

# Verificación mínima

```bash
python -m compileall "pipeline/chunking" "pipeline/tests"
python -m unittest discover -s pipeline/tests
python -m pipeline.chunking.main --help
python -m pipeline.chunking.main build-sliding-window --help
python -m pipeline.chunking.main build-parents
```

No se usa un comando genérico `--strategy`: cada fase agrega solo el comando concreto que necesita.
