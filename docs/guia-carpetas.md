# Guía visual de carpetas

Este documento funciona como mapa de navegación del repositorio. La estructura muestra dónde debe vivir cada tipo de contenido y qué responsabilidad tiene cada carpeta.

```text
proyecto_rag/
├── README.md            # Entrada principal del proyecto: objetivo, instalación, uso y enlaces clave.
├── .gitignore           # Archivos y carpetas que no deben versionarse: entornos, cachés, datos sensibles y artefactos generados.
├── docs/                             # Documentación arquitectónica, metodológica y decisiones de diseño.
│   ├── guia-carpetas.md              # Esta guía visual: qué va en cada carpeta del repositorio.
│   ├── mapa-fases-tesis.md           # Relación entre fases de tesis, entregables y carpetas del proyecto.
│   ├── reporte-falla-delegacion.md   # Registro de fallas, bloqueos o hallazgos relevantes durante el proceso de trabajo.
│   └── decisiones/                   # ADRs y decisiones importantes: arquitectura, metodología, tradeoffs y justificaciones.
│
├── pipeline/                         # Procesos offline que transforman normativa fuente en artefactos reutilizables.
│   ├── ingestion/                    # Descarga, conversión y carga inicial de fuentes normativas oficiales.
│   ├── cleaning/                     # Limpieza, normalización y corrección de texto extraído desde documentos fuente.
│   ├── chunking/                     # Segmentación del corpus en fragmentos aptos para recuperación y citación.
│   ├── tables/                       # Procesamiento especializado de tablas normativas.
│   │   ├── extraction/               # Extracción estructurada de tablas desde PDFs, documentos o fuentes oficiales.
│   │   ├── summarization/            # Resúmenes o reinterpretaciones controladas de tablas para facilitar recuperación.
│   │   └── linkage/                  # Vinculación entre tablas, artículos, chunks y referencias relacionadas.
│   ├── indexing/                     # Generación de embeddings, índices vectoriales y artefactos de recuperación.
│   └── tests/                        # Pruebas del pipeline offline: extracción, limpieza, chunking, tablas e indexación.
│
├── agents/                           # Lógica de los agentes LLM del sistema.
│   ├── shared/                       # Componentes comunes: prompts base, clientes LLM, retrievers, adaptadores y utilidades.
│   ├── consulta_normativa/           # Agente para responder consultas y explicar obligaciones normativas.
│   │   ├── src/                      # Código fuente del agente de consulta normativa.
│   │   │   ├── comprension_consulta  # Detección de intención, reformulación o clasificación de preguntas del usuario.
│   │   │   ├── recuperacion/         # Recuperación del contexto normativo relevante para responder.
│   │   │   ├── contexto_empresarial  # Incorporación de información de la empresa al proceso de respuesta.
│   │   │   └── validacion_respuesta  # Verificación de fidelidad, consistencia y control de la respuesta final.
│   │   └── tests/                    # Pruebas del agente de consulta normativa.
│   └── diagnostico_cumplimiento/     # Agente para levantamiento de información y análisis de brechas de cumplimiento.
│       ├── src/                      # Lógica conversacional y de análisis del agente de diagnóstico.
│       └── tests/                    # Pruebas del agente de diagnóstico de cumplimiento.
│
├── app/                              # Aplicación web que expone los agentes al usuario final.
│   ├── backend/                      # API y orquestación del lado servidor para exponer ambos agentes.
│   │   ├── src/                      # Código fuente del backend: rutas, servicios, controladores e integración con agentes.
│   │   └── tests/                    # Pruebas del backend.
│   └── frontend/                     # Interfaz de usuario del prototipo web.
│       └── src/                      # Código fuente del frontend: vistas, componentes, estado y comunicación con backend.
│
├── evaluation/                       # Datasets, configuración experimental, instrumentos y resultados de evaluación.
│   ├── ares/                         # Configuración, calibración y utilidades relacionadas con ARES.
│   ├── datasets/                     # Conjuntos de datos usados para calibración, optimización y evaluación.
│   │   ├── conjunto_a_gold/          # Tripletas o ejemplos anotados manualmente para calibrar ARES.
│   │   └── conjunto_b_optim/         # Casos usados para comparar variantes del sistema durante desarrollo.
│   ├── experiments/                  # Configuraciones de corridas experimentales por etapa y técnica candidata.
│   ├── instruments/                  # Instrumentos usados para evaluar el sistema.
│   │   ├── expert_rubrics/           # Rúbricas y formatos de validación del experto SST.
│   │   ├── user_surveys/             # Encuestas Likert y formularios usados con empresas participantes.
│   │   └── protocols/                # Protocolos de sesión, guías operativas, consentimiento y criterios de aplicación.
│   ├── results/                      # Resultados organizados, anonimizados o consolidados de la evaluación.
│   │   ├── ares_runs/                # Salidas de ARES: métricas, tablas comparativas e intervalos de confianza.
│   │   ├── expert_validation/        # Observaciones, calificaciones y consolidado del experto SST.
│   │   ├── user_study/               # Resultados agregados o anonimizados del estudio con usuarios.
│   │   └── integrated_reports/       # Reportes finales que integran evidencia automática, experta y de usuarios.
│   └── resultados_usuarios/          # Datos crudos y confidenciales de interacciones con empresas reales.
│
├── data/                             # Corpus y artefactos derivados del procesamiento.
│   ├── raw/                          # Archivos normativos originales descargados desde fuentes oficiales.
│   ├── interim/                      # Versiones intermedias tras extracción y limpieza; aún no listas como artefacto final.
│   │   └── tables/                   # Representaciones intermedias de tablas normativas.
│   └── processed/                    # Artefactos finales listos para recuperación o consumo por agentes.
│       ├── chunks/                   # Chunks finales del corpus con metadatos necesarios para recuperación.
│       └── table_store/              # Artefactos finales derivados de tablas para consulta estructurada o enlace semántico.
│
└── scripts/                          # Utilidades puntuales de soporte operativo, migraciones o automatizaciones auxiliares.
```

## Regla práctica

Si un archivo transforma datos, debe ir en `pipeline/`. Si responde o razona con un LLM, debe ir en `agents/`. Si expone el sistema al usuario, debe ir en `app/`. Si guarda evidencia de evaluación, debe ir en `evaluation/`. Si es documentación o decisión, debe ir en `docs/`.
