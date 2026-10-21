# Guía visual de carpetas

> **Status:** `Current`
> **Audience:** contributor, maintainer
> **Verified against:** árbol del repositorio y `git ls-files`
> **Last verified:** 2026-10-20
> **Replacement:** N/A

Este documento es el mapa técnico del repositorio. Muestra dónde vive cada tipo de contenido y qué responsabilidad tiene cada carpeta en la implementación actual. La entrada general del proyecto es el [README](../README.md).

```text
proyecto_rag/
├── README.md                         # Entrada canónica del proyecto (único README de navegación).
├── AGENTS.md                         # Instrucciones para agentes de desarrollo.
├── requirements.txt                  # Único manifiesto de dependencias (versiones exactas, Python 3.14).
├── pytest.ini                        # `pythonpath = .` para la suite de diagnóstico.
├── Dockerfile                        # Imagen del backend: PyTorch CPU, modelos fijos y usuario sin privilegios.
├── .dockerignore                     # Lista blanca del contexto de build.
├── compose.yaml                      # Ejecución tipo producción (`docker compose up`).
├── compose.dev.yaml                  # Overlay de desarrollo con recarga (`-f compose.dev.yaml`).
├── docker/                           # Script de descarga de modelos del build.
├── odd/tasks/                        # Bitácoras de tareas de desarrollo (no es documentación de producto).
├── docs/                             # Documentación detallada (ver sección "Documentación").
│
├── pipeline/                         # Procesos offline: normativa fuente → artefactos e índices.
│   ├── ingestion/                    # DOCX → Markdown y extracción de tablas HTML (requiere Pandoc).
│   ├── cleaning/                     # Limpieza y normalización del Markdown extraído.
│   ├── chunking/                     # Parent chunks y child chunks.
│   │   ├── main.py                   # Entrypoint: `python -m pipeline.chunking.main ...`.
│   │   ├── cli.py                    # Subcomandos de chunking (y alias de compatibilidad de tablas).
│   │   ├── config.py                 # Rutas por defecto, constantes y modelo de embeddings.
│   │   ├── io_jsonl.py               # Lectura/escritura JSONL determinística.
│   │   ├── structural_analysis/      # Detección determinística de estructura normativa.
│   │   │   ├── boundaries.py         # Fronteras legales.
│   │   │   ├── metadata_infer.py     # Metadata de fuente y estructura jurídica.
│   │   │   └── patterns.py           # Regex legales.
│   │   └── hierarchical_splitter/    # Construcción parent-child del corpus.
│   │       ├── models.py             # SourceDocument, ParentChunk, ChildChunk y resultados.
│   │       ├── parent_builder.py     # Parent chunks por frontera legal.
│   │       ├── tokenization.py       # Conteo y offsets con AutoTokenizer.
│   │       └── child_splitter/       # Estrategias de child chunking.
│   │           ├── shared.py
│   │           ├── sliding_window.py # Baseline mecánico.
│   │           ├── semantic.py       # Baseline semántico experimental.
│   │           └── regex_constrained_semantic.py # Estrategia canónica.
│   ├── tables/                       # Tablas: referencias, Markdown derivado y documentos JSONL.
│   │   ├── main.py                   # Entrypoint: `python -m pipeline.tables.main ...`.
│   │   ├── table_references.py
│   │   ├── table_markdown.py
│   │   ├── table_documents.py
│   │   └── table_jsonl_to_html.py    # Vista previa HTML opcional (`data/processed/tables_htlm`).
│   ├── vectorization/                # Embeddings e indexación en Chroma.
│   ├── sparse_indexing/              # Construcción del índice BM25.
│   └── tests/                        # Pruebas del pipeline offline.
│
├── agents/                           # Código online (tiempo de respuesta).
│   ├── api/                          # API FastAPI unificada (`agents.api.main:app`) y sus pruebas.
│   ├── consulta_normativa/           # Agente de consulta normativa SG-SST.
│   │   ├── api/                      # Router `/api/v1/query`.
│   │   ├── langchain_rag/            # Implementación actual con LangGraph (incluye `retrieval/`).
│   │   ├── manual_implementation/    # Línea base manual congelada.
│   │   └── tests/
│   └── diagnostico_cumplimiento/     # Agente de diagnóstico: api, catalog, domain, questionnaire, reporting, rules, tests.
│
├── evaluation/                       # Datasets, experimentos, instrumentos y resultados.
│   ├── ares/                         # Configuración de ARES (vacío por ahora).
│   ├── datasets/                     # conjunto_a_gold (calibración) y conjunto_b_optim (optimización).
│   ├── experiments/                  # Scripts y configuraciones de corridas.
│   ├── instruments/                  # Rúbricas, encuestas y protocolos.
│   ├── results/                      # Resultados procesados o anonimizados.
│   └── resultados_usuarios/          # Datos crudos confidenciales (ignorado por git salvo README).
│
└── data/                             # Corpus y artefactos derivados.
    ├── raw/                          # DOCX normativos originales.
    ├── interim/                      # Markdown intermedio y tablas HTML extraídas.
    ├── images/                       # Diagrama del grafo generado por la CLI.
    └── processed/                    # Markdown limpio y artefactos para RAG.
        ├── *.md                      # Markdown limpio por norma.
        ├── chunks/                   # parents.jsonl, estrategias de child chunking y comparison/.
        ├── tables_markdown/          # Tablas convertidas a Markdown.
        ├── tables_htlm/              # Vista previa HTML opcional (nombre intencional).
        ├── table_documents.jsonl     # Documentos de tabla para indexación.
        ├── chroma/                   # Colección Chroma `sg_sst_base_rag`.
        └── bm25/                     # Índice BM25S.
```

## Documentación

```text
docs/
├── getting-started.md       # Instalación y ejecución local de la API.
├── guia-carpetas.md         # Esta guía.
├── mapa-fases-tesis.md      # Fases de la metodología ↔ carpetas.
├── testing.md               # Inventario y ejecución de pruebas.
├── EISI_…_pg1409.pdf        # Fuente metodológica (inmutable).
├── architecture/            # Diseño del pipeline y del RAG (incluye la línea base manual).
├── operations/              # Runbooks (incluye la línea base manual).
├── reference/api.md         # Contrato HTTP de las rutas activas.
├── techniques/              # Técnicas por etapa: retrieval, query_understanding, business_context, validation.
├── experiments/             # Evaluaciones de chunking.
├── plans/                   # Planes vigentes.
├── historical/              # Planes ejecutados y snapshots R1–R3.
└── decisiones/              # Registros de decisión (solo bajo petición explícita).
```

La carpeta indica el **tema**; el **estado** (`Current`, `Baseline`, `Experimental`, `Historical`) está en el bloque de metadatos de cada documento. Así, cuando una técnica se conecta al grafo en una nueva etapa, se actualiza su estado sin mover el archivo. Solo `historical/` se separa físicamente, porque su contenido no cambia.

Puntos de entrada de técnicas: [búsqueda híbrida](techniques/retrieval/hybrid-retrieval.md), [reranking](techniques/retrieval/cross-encoder-reranking.md), [documentos padre](techniques/retrieval/parent-document-retrieval.md), [complemento de tablas](techniques/retrieval/table-complement.md), [expansión de consulta](techniques/query_understanding/query-expansion.md), [contexto empresarial](techniques/business_context/business-context.md), [memoria de largo plazo](techniques/business_context/retrieval-based-long-term-memory.md), [relevance grading](techniques/validation/retrieval-relevance-grading.md). Las demás técnicas de esas carpetas son `Experimental`.

## Reglas prácticas

| Tipo de archivo | Ubicación |
|---|---|
| Código que transforma datos offline | `pipeline/` |
| Lógica de agentes y API HTTP | `agents/` |
| Evaluación, datasets, instrumentos y resultados | `evaluation/` |
| Instalación y ejecución | `docs/getting-started.md` |
| Diseño vigente | `docs/architecture/` |
| Runbooks | `docs/operations/` |
| Contratos HTTP | `docs/reference/` |
| Diseño de técnicas candidatas o activas | `docs/techniques/` |
| Experimentos y resultados técnicos | `docs/experiments/` |
| Planes en curso | `docs/plans/` |
| Planes ejecutados y snapshots | `docs/historical/` |
| Datos fuente, intermedios y derivados | `data/` |

## Artefactos derivados

Los siguientes archivos o carpetas son salidas del pipeline. No deberían editarse manualmente; deben regenerarse con los runbooks activos:

- Corpus Markdown y chunks: [corpus-build.md](operations/corpus-build.md).
- Tablas Markdown y documentos de tabla: [table-processing.md](operations/table-processing.md).
- Chroma y embeddings: [vectorization.md](operations/vectorization.md).
- Índice BM25: [bm25-sparse-retrieval.md](operations/bm25-sparse-retrieval.md).
- Consulta RAG actual: [rag-langgraph.md](operations/rag-langgraph.md).
- Línea base RAG manual: [rag-manual.md](operations/rag-manual.md).

```text
data/processed/chunks/
data/processed/tables_markdown/
data/processed/table_documents.jsonl
data/processed/chroma/
data/processed/bm25/
```

## Límite importante

`data/raw/`, `data/interim/` y `data/processed/` pueden contener datos grandes, derivados o sensibles. Antes de versionar archivos en esas carpetas, confirma si son fuente oficial necesaria, artefacto derivado reproducible o dato confidencial.
