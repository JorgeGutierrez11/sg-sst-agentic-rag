# Plan de migración y organización de la documentación

> **Status:** `Historical`
> **Audience:** maintainer
> **Verified against:** árbol `docs/` resultante, verificación de enlaces internos y `git diff --check`
> **Last verified:** 2026-10-18
> **Replacement:** N/A (plan ejecutado el 2026-10-18; la navegación vigente parte de [`README.md`](../../README.md))

## Propósito, alcance y no objetivos

**Propósito.** Convertir la documentación del repositorio en una navegación clara, verificable y mantenible, con `README.md` en la raíz como único punto de entrada, sin perder evidencia académica ni líneas base técnicas.

**Alcance.** Clasificar todo el Markdown mantenido a mano, reubicar los Markdown de la raíz distintos de `AGENTS.md` y `README.md`, corregir referencias y contenido desactualizado, y crear la referencia de API.

**No objetivos.** No se modifica código, no se crea frontend ni plataforma de despliegue, no se altera el PDF metodológico y no se añaden registros a `docs/decisiones/`.

**Fuera de inventario (deliberadamente).** `data/**/*.md` (corpus generado por el pipeline), `odd/tasks/*.md` (bitácoras de trabajo; sus menciones a rutas antiguas son registro histórico), `.atl/` y `.pytest_cache/` (herramientas).

## Correcciones aplicadas al plan original

| # | Hueco o falla del plan original | Corrección |
|---|---|---|
| 1 | Los Markdown de la raíz quedaban "por clasificar" sin destino. | Destino explícito: `GUIA_EJECUCION_BACKEND.md` → `docs/getting-started.md`; `plan-docker.md` → `docs/plans/plan-docker.md`. |
| 2 | Carpetas por estado (`baselines/`, `experiments/`, `historical/`): el estado de una técnica cambia en cada etapa de la tesis (git tags) y obligaría a mover archivos y romper enlaces. | **Carpeta por tema, estado en metadatos.** Solo `historical/` se separa, porque su contenido es inmutable. Las líneas base quedan junto a su equivalente vigente con estado `Baseline`. |
| 3 | `technical_documentation/` quedaba como carpeta de "transición" indefinida, con nombres con espacios. | Se renombra a `docs/techniques/` con nombres en kebab-case; los snapshots R1–R3 pasan a `docs/historical/retrieval-snapshots/`. |
| 4 | Todas las técnicas se presumían `Experimental` sin mirar el código. | Clasificación por cableado real en `graph.py`: las técnicas conectadas al grafo son `Current`; las no conectadas, `Experimental`. |
| 5 | Archivos puente en rutas antiguas contradicen la regla de "solo dos Markdown en la raíz" y duplican contenido. | Sin archivos puente: se actualizan todos los enlaces entrantes en el mismo cambio. |
| 6 | El inventario omitía `agents/README.md` (desactualizado), los README de `evaluation/`, el propio plan y la referencia entrante desde `AGENTS.md`. | Incluidos en el inventario. |
| 7 | No definía cómo validar enlaces. | Verificación automática de todo enlace Markdown relativo (archivo y ancla de ruta) en los documentos inventariados, más `git diff --check`. |
| 8 | Las rutas por audiencia enlazaban a `docs/` como carpeta, pero no existe índice (ni debe existir `docs/README.md`). | `README.md` enlaza directamente cada documento de destino. |
| 9 | La reubicación exigía aprobación lote por lote. | La solicitud del 2026-10-18 ("Implementar el plan y organizar toda la documentación") aprueba los lotes de este inventario. |
| 10 | No fijaba el idioma de la documentación. | El contenido sigue en español (convención existente); las claves del bloque de metadatos y los valores de estado, en inglés. |

## Política de clasificación

Todo documento inventariado comienza con este bloque:

```markdown
> **Status:** `Current` | `Baseline` | `Experimental` | `Historical`
> **Audience:** <user | operator | contributor | academic-reviewer | maintainer>
> **Verified against:** <ruta de código, comando o fuente metodológica>
> **Last verified:** YYYY-MM-DD
> **Replacement:** <enlace relativo o `N/A`>
```

| Estado | Uso | Regla |
|---|---|---|
| `Current` | Fuente operativa o técnica vigente. | Coincide con el código activo y sus enlaces resuelven. |
| `Baseline` | Implementación congelada de comparación. | Indica que no es el flujo recomendado y enlaza al vigente. |
| `Experimental` | Técnica candidata o experimento no cableado en el runtime. | Declara que no hay garantía operativa. |
| `Historical` | Planes ejecutados y snapshots. | Se conserva para auditoría; enlaza a su reemplazo si existe. |

Ningún archivo se elimina: todo traslado usa `git mv`.

## Arquitectura de información resultante

```text
README.md                    # entrada canónica: descripción, inicio rápido y rutas por audiencia
AGENTS.md                    # instrucciones operativas para agentes
docs/
├── getting-started.md       # instalación y ejecución local de la API (antes GUIA_EJECUCION_BACKEND.md)
├── guia-carpetas.md         # mapa técnico del repositorio
├── mapa-fases-tesis.md      # trazabilidad metodología ↔ repositorio
├── testing.md               # inventario y ejecución de pruebas
├── EISI_…_pg1409.pdf        # fuente metodológica inmutable
├── architecture/            # diseño del pipeline y del RAG (incluye la línea base manual)
├── operations/              # runbooks (incluye la línea base manual)
├── reference/api.md         # contrato HTTP de las rutas activas
├── techniques/              # técnicas por etapa: retrieval, query_understanding, business_context, validation
├── experiments/             # evaluaciones de chunking
├── plans/                   # planes vigentes (plan-docker.md)
├── historical/              # planes ejecutados y snapshots R1–R3
└── decisiones/api.md        # plan de API unificada ejecutado (Historical; no se mueve)
```

## Inventario y acción

| Ruta original | Ruta final | Estado |
|---|---|---|
| `README.md` | igual (reescrito) | `Current` |
| `AGENTS.md` | igual (enlace a la guía actualizado) | sin bloque (instrucciones de agente) |
| `GUIA_EJECUCION_BACKEND.md` | `docs/getting-started.md` | `Current` |
| `plan-docker.md` | `docs/plans/plan-docker.md` | `Current` (plan vigente) |
| `agents/README.md`, `evaluation/*/README.md` | igual (`agents/README.md` corregido) | README de carpeta, sin bloque |
| `docs/guia-carpetas.md`, `docs/mapa-fases-tesis.md`, `docs/testing.md` | igual | `Current` |
| `docs/architecture/{chunking,tables,vectorization,bm25-sparse-retrieval,retrieval,retrieval-langgraph}.md` | igual | `Current` |
| `docs/architecture/retrieval-manual.md`, `docs/operations/rag-manual.md` | igual | `Baseline` |
| `docs/operations/{corpus-build,table-processing,vectorization,bm25-sparse-retrieval,rag-langgraph}.md` | igual | `Current` |
| — | `docs/reference/api.md` (nuevo) | `Current` |
| — | `docs/techniques/retrieval/table-complement.md` (nuevo: técnica cableada sin documentar) | `Current` |
| `docs/experiments/*.md` | igual | `Experimental` |
| `docs/technical_documentation/retrieval/{hybrid-retrieval,cross-encoder-reranking,parent-document-retrieval}.md` | `docs/techniques/retrieval/` | `Current` |
| `docs/technical_documentation/retrieval/R{1,2,3}_*.md` | `docs/historical/retrieval-snapshots/` | `Historical` |
| `docs/technical_documentation/query_understanding/query-expansion.md` | `docs/techniques/query_understanding/` | `Current` |
| `docs/technical_documentation/query_understanding/{query-rewriting,multi-query-rrf}.md` | `docs/techniques/query_understanding/` | `Experimental` |
| `docs/technical_documentation/business_context/business_context.md` | `docs/techniques/business_context/business-context.md` | `Current` |
| `docs/technical_documentation/business_context/Retrieval-Based Long-Term Memory.md` | `docs/techniques/business_context/retrieval-based-long-term-memory.md` | `Current` |
| `docs/technical_documentation/business_context/Summarization-Based Conversational Memory.md` | `docs/techniques/business_context/summarization-based-conversational-memory.md` | `Experimental` |
| `docs/technical_documentation/business_context/full_conversation_memory.md` | `docs/techniques/business_context/full-conversation-memory.md` | `Experimental` |
| `docs/technical_documentation/business_context/contexto_empresarial_tres_tecnicas.md` | `docs/techniques/business_context/contexto-empresarial-tres-tecnicas.md` | `Experimental` (comparación) |
| `docs/technical_documentation/validation/retrieval-relevance-grading.md` | `docs/techniques/validation/` | `Current` |
| `docs/technical_documentation/validation/{sufficient-context-gate,self-refine}.md` | `docs/techniques/validation/` | `Experimental` |
| `docs/decisiones/api.md` | igual | `Historical` |
| `docs/documentation-migration-plan.md` | `docs/historical/documentation-migration-plan.md` | `Historical` |

La clasificación final `Current`/`Experimental` de las técnicas se confirmó contra `agents/consulta_normativa/langchain_rag/graph.py`; ver el registro de cambios en cada documento.

## Rutas de navegación por audiencia

| Audiencia | Ruta |
|---|---|
| Usuario | `README.md` → [`docs/reference/api.md`](../reference/api.md) |
| Operador local | `README.md` → [`docs/getting-started.md`](../getting-started.md) → [`docs/operations/`](../operations/corpus-build.md) |
| Contribuidor | `README.md` → [`docs/guia-carpetas.md`](../guia-carpetas.md) → [`docs/testing.md`](../testing.md) → arquitectura |
| Revisor académico | `README.md` → [`docs/mapa-fases-tesis.md`](../mapa-fases-tesis.md) → PDF → técnicas, experimentos y snapshots |
| Mantenedor | `README.md` → [`docs/architecture/retrieval.md`](../architecture/retrieval.md) → referencia API → planes |

## Lista de validación

- [x] Solo `AGENTS.md` y `README.md` como Markdown en la raíz.
- [x] Ningún `docs/README.md`.
- [x] Todo traslado hecho con `git mv`; ningún archivo eliminado.
- [x] Todos los documentos inventariados con bloque de estado.
- [x] Documentos `Current` de runtime, técnicas, pipeline y API reconciliados con el código (CodeGraph + lectura dirigida).
- [x] Todos los enlaces Markdown relativos de los documentos inventariados resuelven.
- [x] PDF metodológico, snapshots R1–R3 y líneas base preservados.
- [x] `git diff --check` sin errores.
