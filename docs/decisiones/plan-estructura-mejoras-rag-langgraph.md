# Plan de estructura para mejoras del RAG LangGraph

Este plan define cómo organizar las futuras técnicas de mejora del RAG normativo dentro de `agents/consulta_normativa/langchain_rag/` y qué refactor mínimo conviene hacer antes de implementarlas.

La intención no es implementar todas las técnicas a la vez. La intención es preparar una estructura clara para experimentar por etapas sin convertir `graph.py` en un archivo monolítico.

## Decisión

Las técnicas de mejora se organizarán por dimensión funcional del pipeline:

1. comprensión de consulta;
2. recuperación;
3. contexto empresarial;
4. validación y control.

`graph.py` debe quedar como orquestador del flujo LangGraph. Las técnicas concretas deben vivir en módulos independientes y ser probables sin ejecutar todo el pipeline.

## Estructura objetivo

```text
agents/consulta_normativa/langchain_rag/
├── main.py
├── graph.py
├── config.py
├── formatting.py
├── models.py
├── prompts.py
│
├── core/
│   ├── state.py
│   ├── routes.py
│   └── instrumentation.py
│
├── query_understanding/
│   ├── query_rewriting.py
│   ├── multi_query.py
│   └── query_expansion.py
│
├── retrieval/
│   ├── dense.py
│   ├── hybrid.py
│   ├── reranking.py
│   └── parent_document.py
│
├── business_context/
│   ├── metadata_filters.py
│   ├── self_query.py
│   └── contextual_rewriting.py
│
└── validation/
    ├── relevance_grading.py
    ├── answerability.py
    └── citation_verification.py
```

## Responsabilidades

| Carpeta | Responsabilidad | Qué no debe contener |
|---|---|---|
| `core/` | Estado común, rutas condicionales e instrumentación transversal. | Técnicas RAG concretas. |
| `query_understanding/` | Transformaciones de consulta antes del retrieval. | Lógica de Chroma o generación final. |
| `retrieval/` | Recuperación, fusión, reranking y resolución parent/child. | Prompts de respuesta o validación de claims. |
| `business_context/` | Uso del perfil empresarial para filtros o reescritura contextual. | Inferencias no verificadas sobre la empresa. |
| `validation/` | Validación de relevancia, suficiencia y citación. | Recuperación inicial o formateo de metadata. |

## Refactor mínimo antes de nuevas técnicas

Antes de implementar mejoras, hacer solo este refactor pequeño:

### 1. Crear `core/state.py`

Mover `RagGraphState` desde `graph.py` a `core/state.py`.

Motivo: el estado crecerá con campos como `retrieval_query`, `generated_queries`, `retrieval_traces`, `relevance_decision`, `answerability_decision`, `company_profile` y `metadata_filters`.

### 2. Crear `core/routes.py`

Mover la ruta condicional actual `evidence_route(...)` desde `graph.py`.

Este módulo concentrará futuras rutas como:

```text
route_by_evidence
route_by_relevance
route_by_answerability
route_by_retry_count
route_by_citation_check
```

### 3. Mantener `graph.py` como orquestador

`graph.py` debe seguir construyendo el `StateGraph`, agregando nodos y conectando rutas. No debe contener la implementación interna de cada técnica.

### 4. No mover todavía

Por ahora no mover:

- `formatting.py`;
- `prompts.py`;
- `models.py`;
- `config.py`;
- `main.py`.

Estos módulos aún tienen responsabilidades claras y no necesitan partirse antes de experimentar.

## Orden de implementación recomendado

1. Refactor mínimo de `core/`.
2. Instrumentación del retrieval.
3. Primera técnica de validación: relevance grading.
4. Primera técnica de comprensión: query rewriting.
5. Primera técnica de recuperación: hybrid retrieval o reranking, según fallos observados.
6. Contexto empresarial mediante filtros determinísticos antes de self-query.
7. Answerability y verificación de citas cuando el retrieval esté más estable.

## Reglas de diseño

- Crear las carpetas sin los scripts, lo importante es tener clara la estructura a usar.
- Evitar una carpeta genérica `utils/`; si algo es transversal, debe vivir en `core/` con nombre específico.
- No mezclar recuperación, generación y validación en el mismo módulo.
- No implementar varias técnicas en un solo experimento si se quiere atribuir mejoras con claridad.

## Criterios de aceptación del refactor

- `graph.py` importa `RagGraphState` desde `core/state.py`.
- `graph.py` importa rutas condicionales desde `core/routes.py`.
- La ejecución actual del RAG no cambia.
- No se modifica el contrato público `LangChainRagResult`.
- No se agregan técnicas nuevas durante este refactor.
- La instrumentación queda preparada, pero no debe alterar todavía la selección de documentos.

## Relación con técnicas candidatas

Este plan complementa `docs/decisiones/tecnicas-candidatas-mejora-rag.md`. Ese documento define qué técnicas evaluar; este documento define dónde vivirán y cuál es el refactor mínimo para integrarlas sin degradar la arquitectura.
