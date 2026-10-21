# Guía de pruebas automatizadas — SG-SST Agentic RAG

> **Status:** `Current`
> **Audience:** contributor
> **Verified against:** `pipeline/tests/`, `agents/*/tests/`, `pytest.ini` (81 módulos: 17 + 33 + 3 + 28)
> **Last verified:** 2026-10-20
> **Replacement:** N/A

> **Estado del documento:** inventario de pruebas y guía de ejecución. **No certifica que las pruebas estén pasando actualmente.** Los comandos se documentaron a partir de la estructura del repositorio; no se ejecutaron todas las suites durante la elaboración de la guía.

## 1. Propósito y alcance

Esta guía identifica las pruebas automatizadas del proyecto, explica cómo ejecutarlas y delimita qué conclusiones pueden extraerse de sus resultados. El inventario comprende **81 módulos** distribuidos entre el pipeline de procesamiento documental, el agente de consulta normativa, la API unificada y el agente de diagnóstico de cumplimiento.

| Subsistema | Módulos | Framework principal | Alcance |
|---|---:|---|---|
| Pipeline offline del corpus | 17 | `unittest` | Fragmentación, tablas, documentos vectoriales, Chroma, índices BM25 y build unificado |
| Consulta normativa y RAG | 33 | `unittest` | API, grafos, recuperación, prompts, contexto empresarial y memoria |
| API unificada | 3 | `unittest` | Inicialización, endpoints de salud, enrutamiento, ciclo de vida, validación de orígenes CORS y descarga de modelos de la imagen Docker |
| Diagnóstico de cumplimiento | 28 | Principalmente `pytest`; un módulo de API con `unittest` | Catálogos v2.1, cuestionarios, enrutamiento por dependencias, evaluación declarativa y reportes |
| **Total** | **81** | **Mixto** | Pruebas unitarias y de contratos entre componentes |

**Configuración actual:** `pytest.ini` en la raíz declara `pythonpath = .`, de modo que `pytest` resuelve el paquete `agents` aunque `agents/` y `agents/diagnostico_cumplimiento/` no tengan `__init__.py`. La suite de diagnóstico comparte fixtures mediante `agents/diagnostico_cumplimiento/tests/conftest.py`. No existen `pyproject.toml`, `tox.ini` ni `setup.cfg`; las suites de `unittest` siguen usando sus propias utilidades.

## 2. Requisitos previos

1. Utilizar **Python 3.14**, declarado en `.python-version`.
2. Instalar las dependencias de `requirements.txt` en el entorno activo.
3. Ejecutar los comandos desde la **raíz del repositorio**.
4. Mantener disponibles los catálogos JSON del diagnóstico y el fixture `agents/diagnostico_cumplimiento/tests/fixtures/valid_catalog.json`.

Las pruebas focalizadas sustituyen normalmente llamadas a modelos, índices y servicios externos por objetos simulados (*fakes*, *mocks* y *patches*). En principio, no deberían descargar modelos de embeddings o reranking ni abrir los índices Chroma/BM25 de producción.

Las operaciones reales de Chroma necesitan `chromadb`, declarado en `requirements.txt` según el inventario. **Pandoc no es necesario para las pruebas focalizadas**, pero sí para la ingestión real de DOCX y las conversiones correspondientes.

## 3. Ejecución de las pruebas

### 3.1. Comandos documentados en `AGENTS.md`

```bash
# Pipeline de procesamiento del corpus
python -m unittest discover -s pipeline/tests

# Agente de consulta normativa
python -m unittest discover -s agents/consulta_normativa/tests

# Pruebas focalizadas del procesamiento de tablas
python -m unittest \
  pipeline.tests.test_tables_main \
  pipeline.tests.test_table_references \
  pipeline.tests.test_table_markdown \
  pipeline.tests.test_table_documents

# Verificación de compilación de código Python
python -m compileall pipeline agents/consulta_normativa
```

> `compileall` verifica que los archivos puedan compilarse. **No ejecuta aserciones, no comprueba importaciones de dependencias en tiempo de ejecución ni garantiza que la aplicación arranque.**

### 3.2. Comandos adicionales por subsistema

```bash
# API unificada
python -m unittest discover -s agents/api/tests

# Diagnóstico de cumplimiento
python -m pytest agents/diagnostico_cumplimiento/tests
```

La suite del diagnóstico usa funciones y fixtures de `pytest`. Gracias a `pytest.ini`, `pytest agents/diagnostico_cumplimiento/tests` y `python -m pytest agents/diagnostico_cumplimiento/tests` son equivalentes; sin ese archivo, `pytest` a secas falla con `ModuleNotFoundError: No module named 'agents'`. `AGENTS.md` documenta este comando y la configuración de `pytest.ini`. `pytest` también recopila el módulo de API que utiliza `unittest.TestCase`.

Para ejecutar un módulo puntual:

```bash
python -m unittest agents.consulta_normativa.tests.test_langchain_rag_prompts
python -m pytest agents/diagnostico_cumplimiento/tests/test_catalog.py
```

**Atención a los tests omitidos:** `agents/consulta_normativa/tests/test_bm25_retrieval.py` omite condicionalmente una prueba de integración de BM25S si no está instalado `bm25s`. Una suite que finaliza correctamente con ese *skip* **no demuestra** que esa ruta de integración funcione.

## 4. Inventario por subsistema

### 4.1. Pipeline offline del corpus — 17 módulos

**Fragmentación (*chunking*)**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_chunking_phase1.py` | Fragmentos padre, metadatos, límites y CLI |
| `test_chunking_phase2_sliding_window.py` | Ventanas deslizantes, división y solapamiento |
| `test_chunking_phase3_semantic.py` | Fragmentación semántica y estructura de salida |
| `test_chunking_phase4_regex_constrained_semantic.py` | Fragmentación semántica restringida por expresiones regulares y límites estructurales |
| `test_chunking_tokenization.py` | Estimación reproducible de tokens y utilidades de tokenización |

**Procesamiento de tablas**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_tables_main.py` | Enrutamiento de comandos CLI y códigos de salida |
| `test_table_references.py` | Metadatos de marcadores, rutas seguras, referencias faltantes/huérfanas y errores controlados |
| `test_table_markdown.py` | Conversión de tablas HTML a Markdown normalizado |
| `test_table_documents.py` | Construcción de documentos independientes de tablas y metadatos |

**Vectorización e indexación**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_vectorization_documents.py` | Conversión de fragmentos y tablas en documentos vectorizables |
| `test_vectorization_chroma_store.py` | Contratos de colecciones y `upsert` con dependencias simuladas |
| `test_sparse_indexing_ingest.py` | Carga del corpus y coordinación de la indexación BM25 |
| `test_sparse_indexing_bm25_store.py` | Tokenización, creación/guardado del índice y serialización usando simulaciones |
| `test_model_revisions.py` | Revisiones fijadas de los modelos Hugging Face de embeddings y reranker |

**Build unificado del corpus**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_offline_orchestration.py` | Orden de las 10 etapas en staging, fallos por etapa, publicación solo de artefactos gestionados, respaldo y restauración con etapas simuladas |
| `test_offline_corpus.py` | Subcomandos `build`/`validate`, mensajes de progreso, eventos JSON y códigos de salida |
| `test_artifact_validation.py` | Consistencia padre-hijo e identidades/conteos de Chroma y BM25 |

### 4.2. Consulta normativa y RAG — 33 módulos

**API y ejecución**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_api.py` | Esquemas HTTP, respuestas, dependencias y errores |
| `test_cli_memory.py` | CLI LangGraph y checkpoints en memoria por conversación |
| `test_langchain_rag_main.py` | Ensamblaje e invocación del runtime |
| `test_langchain_rag_llm.py` | Configuración/fábrica del LLM sin llamar al proveedor real |

**Grafo y validación**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_langchain_rag_graph.py` | Construcción, rutas y transiciones de estado |
| `test_langchain_rag_formatting.py` | Formateo de evidencias y respuestas |
| `test_sufficient_context_gate.py` | Decisiones sobre suficiencia del contexto |
| `test_retrieval_relevance_grading.py` | Calificación y normalización de relevancia de evidencias |
| `test_self_refine.py` | Refinamiento de respuestas mediante colaboradores simulados |

**Consultas y prompts**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_langchain_rag_prompts.py` | Composición de prompts, contexto y referencias separadas |
| `test_langchain_rag_query_rewrite.py` | Reformulación de preguntas usando el historial |
| `test_langchain_rag_query_expansion.py` | Generación y normalización de consultas expandidas |
| `test_langchain_rag_multi_query.py` | Coordinación de recuperación mediante múltiples consultas |
| `test_langchain_rag_fusion.py` | Fusión por rango recíproco (RRF) y duplicados |

**Recuperación, reranking y tablas**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_bm25_retrieval.py` | Carga y búsqueda dispersa; incluye una verificación opcional con BM25S |
| `test_chroma_retrieval.py` | Adaptadores de recuperación vectorial y formato de documentos |
| `test_hybrid_retrieval.py` | Combinación de resultados densos y dispersos |
| `test_parent_document_retrieval.py` | Expansión de fragmentos hijos a documentos padre |
| `test_langchain_rag_reranking.py` | Orden, puntuaciones y límites del reranker con simulaciones |
| `test_table_complement.py` | Enriquecimiento de evidencias mediante tablas |

**Contexto empresarial y memoria**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_business_history.py` | Registros y presentación del historial empresarial |
| `test_business_history_node.py` | Actualizaciones del historial desde un nodo del grafo |
| `test_business_profile.py` | Modelo y combinación de datos del perfil empresarial |
| `test_business_profile_extractor.py` | Extracción y normalización del perfil |
| `test_business_profile_node.py` | Actualizaciones del perfil desde el grafo |
| `test_business_profile_persistence.py` | Conservación del perfil entre turnos/checkpoints |
| `test_graph_persistence.py` | Checkpoints y aislamiento entre conversaciones |
| `test_retrieval_long_term_memory.py` | Recuperación de información conversacional a largo plazo |
| `test_summarization_memory.py` | Estado y selección de memorias resumidas |
| `test_summarization_update.py` | Decisiones y cambios al actualizar resúmenes |
| `test_full_conversation_memory.py` | Flujo integrado de memoria conversacional con simulaciones |

**Implementación base manual congelada**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_cli.py` | Interfaz CLI de la implementación manual de referencia |
| `test_rag_base.py` | Coordinación RAG y contratos auxiliares de esa referencia |

### 4.3. API unificada — 3 módulos

| Módulo | Comportamiento que verifica |
|---|---|
| `agents/api/tests/test_main.py` | Inicialización de FastAPI, separación entre *liveness* y *readiness*, registro de routers, CORS, ruta raíz, ciclo de vida (*lifespan*) y reutilización de dependencias de consulta/diagnóstico, sin cargar runtimes reales |
| `agents/api/tests/test_config.py` | Lectura y validación de `CORS_ALLOWED_ORIGINS`: lista separada por comas, variable ausente, rechazo de `*` y de orígenes con ruta, `/` final o esquema distinto de `http(s)` |
| `agents/api/tests/test_docker_model_download.py` | Script `docker/download_models.py` del build Docker: lee las revisiones fijas solo desde los dos archivos de configuración, sin importarlos; rechaza constantes ausentes o no textuales, y descarga cada modelo con su revisión mediante una función de descarga simulada, sin acceso a red |

### 4.4. Diagnóstico de cumplimiento — 28 módulos

**API**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_api.py` | Crear, responder y completar diagnósticos; generar PDF; errores por sesiones inexistentes o diagnósticos pendientes; delegación a servicios simulados |

**Dominio, aplicabilidad y catálogos**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_models.py` | Construcción y validación de modelos de dominio |
| `test_catalog.py` | Esquema v2.1 (`AssessmentCatalog`), lectura y errores de catálogos |
| `test_catalog_coverage.py` | Cobertura del paquete normativo seleccionado |
| `test_applicability.py` | Selección del catálogo por perfil (`catalog.selector`) y requisitos del paquete seleccionado |
| `test_requirement_applicability.py` | Decisiones de aplicabilidad por requisito |
| `test_requirement_snapshot.py` | Instantáneas de requisitos y estado de enrutamiento de cada pregunta |

**Respuestas y cuestionario**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_answers.py` | Valores de respuesta y colección |
| `test_answer_collection.py` | Guardado, reemplazo y consulta de respuestas |
| `test_answer_validation.py` | Compatibilidad entre respuestas y preguntas |
| `test_answer_format.py` | Formatos admitidos y normalización |
| `test_interpretation.py` | Modelos de valor/estado interpretado |
| `test_answer_interpreter.py` | Coordinación de interpretación de respuestas |
| `test_boolean_interpreter.py` | Interpretación de valores booleanos |
| `test_text_boolean_interpreter.py` | Reglas de interpretación de texto a booleanos |
| `test_requirement_answer_processor.py` | Procesamiento de respuestas con enrutamiento por `depends_on` (preguntas activas, bloqueadas y omitidas) |
| `test_questionnaire.py` | Secuencia, progreso y finalización del cuestionario |
| `test_questionnaire_findings.py` | Hallazgos derivados de las respuestas |
| `test_affiliation_question_routing.py` | Enrutamiento de preguntas de afiliación (módulo no conectado a la API) |

**Progreso y evaluación declarativa**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_declarative_assessment.py` | Evaluación declarativa de requisitos |
| `test_affiliation_declarative_assessment.py` | Resultados específicos de afiliación (módulo no conectado a la API) |
| `test_declarative_findings.py` | Hallazgos declarativos por requisito, incluidas preguntas omitidas por enrutamiento |
| `test_requirement_progress.py` | Progreso de respuestas por requisito |

**Diagnóstico preliminar e informes**

| Módulo | Comportamiento que verifica |
|---|---|
| `test_preliminary_diagnosis.py` | Coordinación del diagnóstico preliminar con catálogos locales |
| `test_preliminary_diagnosis_applicability.py` | Selección de catálogos y aplicabilidad |
| `test_preliminary_diagnosis_assessments.py` | Agregación de evaluaciones y resúmenes |
| `test_preliminary_diagnosis_routing.py` | Avance entre etapas y finalización |
| `test_orientative_report.py` | Contenido del informe orientativo y límites de generación de PDF |

**Pruebas retiradas (2026-10):** se eliminaron junto con el código que verificaban, porque ese código no era alcanzable desde la API: el motor de reglas de evaluación (`test_evaluation_rule*.py`, `test_evaluation_operator*.py`, `test_rule_execution_gate.py`, `test_condition_evaluation_gate.py`) y el modelo de catálogo por condiciones (`test_condition_answer_summary.py`, `test_condition_progress.py`, `test_condition_evaluation.py`, y las pruebas de los modelos legados en `test_catalog.py`).

## 5. Simulaciones, fixtures y datos de prueba

Las suites aíslan deliberadamente los componentes externos o costosos:

- **Mocks y fakes:** `unittest.mock.patch`, recuperadores, almacenes vectoriales, respuestas LLM y servicios simulados sustituyen dependencias reales.
- **Archivos temporales:** `tempfile.TemporaryDirectory` y `tmp_path` aíslan operaciones con archivos JSON, JSONL, Markdown, HTML, índices y catálogos.
- **FastAPI:** `TestClient` ejecuta rutas con servicios simulados o inicializadores de runtime reemplazados.
- **LangGraph:** los tests de memoria utilizan checkpointers en memoria e identificadores explícitos de conversación.
- **Pipeline:** registros pequeños y archivos temporales reemplazan la reconstrucción del corpus completo.
- **Diagnóstico:** `tests/fixtures/valid_catalog.json` es una **copia congelada** del catálogo productivo `catalog/data/res0312_riesgo_i_1_10_general.json` (esquema 2.1, 7 requisitos). `tests/conftest.py` lo expone mediante los fixtures `catalog` y `catalog_path`. Los catálogos sintéticos se construyen copiando ese JSON y modificándolo, para que siempre cumplan el esquema vigente.

Las pruebas de comportamiento usan la copia congelada y no los catálogos productivos, de modo que editar un catálogo real no rompa pruebas ajenas a ese cambio. Si cambia el esquema del catálogo, hay que regenerar la copia y ajustar las aserciones afectadas. Las funciones que seleccionan el catálogo por perfil empresarial, sin recibir una ruta explícita, sí leen los catálogos productivos.

Fuera del diagnóstico, los fixtures son locales a cada módulo. Cuando un fake registra invocaciones, los tests suelen comprobar tanto el resultado observado como el contrato de colaboración.

## 6. Qué demuestra y qué no demuestra la suite

**Estas pruebas proporcionan evidencia sobre contratos unitarios y de componentes.** No prueban por sí mismas:

- Disponibilidad, latencia, calidad de salida o compatibilidad del proveedor LLM real.
- Calidad semántica de embeddings o del reranker.
- Exactitud, integridad, actualidad o efectividad de recuperación del corpus normativo y sus índices Chroma/BM25.
- Durabilidad y concurrencia de sistemas externos de persistencia.
- Instalación de Pandoc o reconstrucción completa desde DOCX hasta los índices.
- Corrección jurídica, validación por expertos en SST, calibración ARES o calidad de las recomendaciones.
- Comportamiento del navegador más allá de los contratos de API/presentación.
- Integración real con BM25S cuando la prueba condicional se omite.

**Implicación para despliegue:** un pipeline CI exitoso es necesario, pero no suficiente. El arranque con índices reales, las llamadas a modelos, la persistencia, las pruebas de carga y la evaluación normativa requieren verificaciones adicionales.

## 7. Contrato de citas en respuestas normativas

El contrato actual separa las referencias visibles en la respuesta de sus datos completos:

1. **Respuesta generada:** texto legible con citas numéricas integradas, como `[1]`.
2. **Payload de API/UI:** objetos con las referencias completas, devueltos por separado para su presentación.
3. **Pruebas de prompts:** comprueban que el contexto normativo y empresarial estén presentes y que no sea obligatoria una lista final de fuentes dentro del texto generado.

Al modificar prompts, preservar esta separación salvo que se modifique conjuntamente el contrato entre backend y frontend. Los tests deben comprobar la intención semántica del contrato, no exigir la igualdad exacta de cadenas de prompt completas.

## 8. Cómo añadir o modificar pruebas

1. Nombrar archivos `test_<comportamiento>.py` y funciones/métodos `test_<contrato_observable>`.
2. Situarlos en la suite del subsistema correspondiente y usar el framework ya establecido allí.
3. Preferir simulaciones y archivos temporales frente a servicios reales, descarga de modelos, índices productivos o modificaciones globales.
4. Verificar comportamientos públicos y contratos estables: estado/cuerpo HTTP, transición de estado, persistencia, orden, errores o invocaciones.
5. Evitar aserciones sobre detalles internos salvo que formen parte de un contrato explícito de compatibilidad.
6. Usar condiciones de *skip* solo para dependencias genuinamente opcionales y explicar qué ruta queda sin probar.
7. Actualizar este inventario y los comandos de ejecución al añadir módulos o configuraciones compartidas.

En pruebas de prompts, mantener alineadas las referencias numéricas inline `[n]` y las referencias completas devueltas por la API.

## 9. Limitaciones conocidas y trabajo pendiente

| Limitación documentada | Impacto |
|---|---|
| Uso mixto de `unittest` y `pytest`; `pytest.ini` solo configura la resolución de imports | No existe un único comando oficial para ejecutar todas las pruebas |
| `AGENTS.md` omite la suite de diagnóstico y la API unificada | La documentación de ejecución está incompleta |
| Conteo por módulos, no por aserciones | **81 módulos no equivalen a cobertura porcentual** |
| Ausencia de configuración y umbral de cobertura | No hay un criterio cuantitativo documentado para CI |
| Omisión condicional de una prueba BM25S | Una ejecución exitosa puede dejar una integración sin verificar |
| Tests focalizados con servicios y modelos simulados | Pueden aparecer errores al cargar modelos e índices reales |
| Inventario basado en finalidades de módulos | Para diagnosticar un fallo hay que revisar las aserciones y fixtures específicos |

### Recomendaciones para la preparación de CI/CD

Las siguientes son **propuestas adicionales**, no funcionalidades confirmadas del repositorio:

- Formalizar los cuatro comandos por subsistema dentro del workflow de CI.
- Instalar `pytest` y las dependencias requeridas en el job de verificación.
- Hacer visibles los tests omitidos (*skipped*) y decidir cuáles deben bloquear el despliegue.
- Incorporar pruebas de integración separadas para el arranque real de FastAPI con índices y modelos.
- Definir una política de cobertura después de obtener una línea base medible; no inventar un porcentaje sin medición.
- Mantener los controles de calidad normativa y de recuperación fuera de la mera suite unitaria.

## 10. Referencias internas del repositorio

| Ruta | Propósito |
|---|---|
| `AGENTS.md` | Convenciones y comandos actualmente documentados |
| `.python-version` | Versión declarada de Python (3.14) |
| `requirements.txt` | Manifiesto de dependencias Python |
| `pytest.ini` | Configuración de `pytest` (`pythonpath = .`) |
| `pipeline/tests/` | 17 módulos de pruebas del pipeline offline |
| `agents/consulta_normativa/tests/` | 33 módulos de consulta normativa y RAG |
| `agents/api/tests/` | Pruebas de la API unificada y de su configuración HTTP |
| `agents/diagnostico_cumplimiento/tests/` | 28 módulos de diagnóstico, `conftest.py` y fixtures |
| `agents/diagnostico_cumplimiento/catalog/data/` | Catálogos JSON utilizados por el diagnóstico |

---

**Nota de mantenimiento:** actualizar los conteos, rutas y comandos cuando cambie la organización de pruebas. Antes de afirmar que el repositorio está listo para desplegar, registrar los resultados de una ejecución real en un entorno limpio.
