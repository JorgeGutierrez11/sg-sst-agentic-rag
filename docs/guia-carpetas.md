# Guía visual de carpetas

Este documento funciona como mapa de navegación del repositorio. Muestra dónde vive cada tipo de contenido y qué responsabilidad tiene cada carpeta en la implementación actual.

```text
proyecto_rag/
├── README.md                         # Entrada principal del proyecto.
├── requirements.txt                  # Dependencias Python conocidas del pipeline y herramientas asociadas.
├── AGENTS.md                         # Instrucciones locales para agentes de desarrollo.
├── docs/                             # Documentación metodológica, arquitectura, operación y experimentos.
│   ├── guia-carpetas.md              # Esta guía visual de estructura del repositorio.
│   ├── mapa-fases-tesis.md           # Relación entre fases de tesis, entregables y carpetas.
│   ├── EISI_2026-04-09_14-25-36_pg1409.pdf     # Plan de referencia metodológica del proyecto.
│   ├── architecture/                 # Diseño vigente: chunking, tablas, vectorización y RAG.
│   ├── operations/                   # Runbooks ejecutables del corpus, tablas, vectorización y RAG.
│   ├── experiments/                  # Notas y resultados de experimentos.
│   └── decisiones/                   # Planes históricos o de transición; no es la fuente operativa principal.
│
├── pipeline/                         # Procesos offline que transforman normativa fuente en artefactos reutilizables.
│   ├── ingestion/                    # Conversión inicial de DOCX a Markdown y extracción de tablas HTML.
│   ├── cleaning/                     # Limpieza y normalización de Markdown extraído.
│   ├── chunking/                     # Segmentación del corpus en parent chunks y child chunks.
│   │   ├── main.py                   # Entrypoint CLI: `python -m pipeline.chunking.main ...`.
│   │   ├── core/                     # Configuración, CLI y serialización JSONL del chunking.
│   │   │   ├── cli.py                # Subcomandos del pipeline de chunking y tablas.
│   │   │   ├── config.py             # Rutas por defecto, constantes y salidas generadas.
│   │   │   └── io_jsonl.py           # Lectura/escritura JSONL determinística.
│   │   ├── structural_analysis/      # Detección determinística de estructura normativa.
│   │   │   ├── boundaries.py         # Detección de fronteras legales.
│   │   │   ├── metadata_infer.py     # Metadata de fuente y estructura jurídica.
│   │   │   └── patterns.py           # Regex legales usadas por el análisis estructural.
│   │   └── hierarchical_splitter/    # Construcción parent-child del corpus normativo.
│   │       ├── models.py             # Contratos de datos: SourceDocument, ParentChunk, ChildChunk, resultados.
│   │       ├── parent_builder.py     # Construcción de parent chunks por frontera legal.
│   │       ├── tokenization.py       # Conteo y offsets con AutoTokenizer.
│   │       └── child_splitter/       # Estrategias de child chunking.
│   │           ├── shared.py         # Helpers comunes para child chunks.
│   │           ├── sliding_window.py # Baseline mecánico.
│   │           ├── semantic.py       # Baseline semántico experimental.
│   │           └── regex_constrained_semantic.py # Estrategia híbrida recomendada.
│   ├── tables/                       # Procesamiento de tablas extraídas y relación con chunks.
│   │   ├── table_references.py       # Detección, validación y auditoría de placeholders `TABLE_n`.
│   │   ├── table_markdown.py         # Conversión de tablas HTML a Markdown derivado.
│   │   └── table_documents.py        # Documentos JSONL vector-ready para tablas.
│   ├── vectorization/                # Generación de embeddings e indexación en Chroma.
│   └── tests/                        # Pruebas del pipeline offline: chunking, tablas y utilidades.
│
├── agents/                           # Lógica de agentes LLM del sistema.
│   ├── README.md                     # Notas de organización de agentes.
│   ├── shared/                       # Componentes comunes: clientes LLM, retrievers, prompts y utilidades.
│   ├── consulta_normativa/           # Agente de consulta normativa SG-SST.
│   │   ├── manual_implementation/    # Línea base manual congelada de referencia.
│   │   ├── langchain_rag/            # Implementación actual con LangChain/LangGraph.
│   │   ├── src/                      # Módulos compartidos heredados del agente de consulta.
│   │   └── tests/                    # Pruebas del agente de consulta normativa.
│   └── diagnostico_cumplimiento/     # Agente de diagnóstico de cumplimiento SG-SST.
│
├── app/                              # Aplicación web/prototipo que expondrá los agentes al usuario final.
│   ├── backend/                      # API del lado servidor.
│   └── frontend/                     # Interfaz de usuario del prototipo.
│
├── evaluation/                       # Datasets, configuración experimental, instrumentos y resultados.
│   ├── ares/                         # Configuración y utilidades relacionadas con ARES.
│   ├── datasets/                     # Conjuntos de datos para calibración, optimización y evaluación.
│   ├── experiments/                  # Experimentos, comparaciones y scripts de evaluación.
│   ├── instruments/                  # Rúbricas, encuestas, protocolos, consentimiento y criterios.
│   ├── results/                      # Resultados procesados, anonimizados o consolidados.
│   └── resultados_usuarios/          # Datos crudos confidenciales de interacciones con empresas.
│
├── data/                             # Corpus y artefactos derivados del procesamiento.
│   ├── raw/                          # DOCX normativos originales. No se versionan salvo `.gitkeep`.
│   ├── interim/                      # Artefactos intermedios tras ingestión.
│   │   └── tables/                   # Tablas HTML extraídas por documento: `<source_stem>/table_<n>.html`.
│   └── processed/                    # Markdown limpio y artefactos derivados listos para chunking/RAG.
│       ├── *.md                      # Markdown limpio de cada norma procesada.
│       ├── chunks/                   # Parent chunks y child chunks por estrategia.
│       │   ├── parents.jsonl
│       │   ├── sliding_window/chunks.jsonl
│       │   ├── semantic_chunking/chunks.jsonl
│       │   └── regex_constrained_semantic/chunks.jsonl
│       ├── tables_markdown/          # Tablas HTML convertidas a Markdown derivado.
│       ├── table_documents.jsonl     # Documentos de tabla listos para vectorización.
│       └── chroma/                   # Colección Chroma local generada por vectorización.
│
└── scripts/                          # Utilidades puntuales de soporte operativo o migraciones.
```

## Reglas prácticas

| Tipo de archivo | Ubicación |
|---|---|
| Código que transforma datos offline | `pipeline/` |
| Código específico de chunking | `pipeline/chunking/` |
| Código de procesamiento de tablas | `pipeline/tables/` |
| Lógica de agentes LLM | `agents/` |
| API o interfaz de usuario | `app/` |
| Evaluación, datasets, instrumentos y resultados | `evaluation/` |
| Documentación de arquitectura vigente | `docs/architecture/` |
| Runbooks operativos | `docs/operations/` |
| Experimentos y resultados técnicos | `docs/experiments/` |
| Planes históricos o de transición | `docs/decisiones/` |
| Datos fuente, intermedios y derivados | `data/` |

## Artefactos derivados

Los siguientes archivos o carpetas son salidas del pipeline. No deberían editarse manualmente; deben regenerarse con los runbooks activos:

- Corpus Markdown y chunks: `docs/operations/corpus-build.md`.
- Tablas Markdown y documentos de tabla: `docs/operations/table-processing.md`.
- Chroma y embeddings: `docs/operations/vectorization.md`.
- Consulta RAG actual: `docs/operations/rag-langgraph.md`.
- Línea base RAG manual: `docs/operations/rag-manual.md`.

```text
data/processed/chunks/
data/processed/tables_markdown/
data/processed/table_documents.jsonl
data/processed/chroma/
```

## Límite importante

`data/raw/`, `data/interim/` y `data/processed/` pueden contener datos grandes, derivados o sensibles. Antes de versionar archivos en esas carpetas, confirma si son fuente oficial necesaria, artefacto derivado reproducible o dato confidencial.
