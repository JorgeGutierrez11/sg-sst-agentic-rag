# Plan de migración y organización de la documentación

## Propósito, alcance y no objetivos

**Propósito.** Convertir la documentación del repositorio en una navegación clara, verificable y mantenible, con `README.md` en la raíz como punto de entrada canónico, sin perder evidencia académica ni líneas base técnicas.

**Alcance.** Clasificar el material existente, incluido el inventario de Markdown de la raíz, corregir referencias y documentación desactualizada, consolidar rutas de entrada y proponer una arquitectura de información para documentación de uso, operación, contribución, API y arquitectura. La raíz conservará únicamente `AGENTS.md` y `README.md` como archivos Markdown; los demás `*.md` de la raíz se clasificarán y reubicarán durante la futura migración aprobada.

**No objetivos.** Este plan no implementa movimientos, eliminaciones ni cambios de código; no crea una interfaz frontend ni una plataforma de despliegue en la nube; tampoco reemplaza el PDF metodológico ni altera la evidencia académica.

## Principios de documentación

Se adopta la separación de seis componentes de Soham Kamani para que cada lector encuentre el nivel correcto de detalle:

| Componente | Propósito |
|---|---|
| Descripción breve | Explicar qué resuelve el proyecto, sus límites y el punto de entrada. |
| Inicio rápido | Permitir una primera ejecución local reproducible con prerrequisitos explícitos. |
| Tutoriales y runbooks | Guiar tareas paso a paso: construcción del corpus, índices y operación local. |
| Ejemplos y material de referencia | Mostrar entradas, salidas, contratos y casos de uso sin sustituir los runbooks. |
| Documentación de API | Describir únicamente endpoints y contratos realmente expuestos por el código activo. |
| Documentación de arquitectura | Explicar límites de paquetes, flujos, decisiones vigentes y dependencias operativas. |

- **Divulgación progresiva:** la navegación debe ir de una portada breve a guías por audiencia y, finalmente, a referencias especializadas.
- **Punto de entrada único:** `README.md` en la raíz es la única entrada canónica. Debe ofrecer una descripción concisa, inicio rápido, enlaces activos por audiencia y un enlace a `docs/`; no debe duplicar el contenido detallado de operaciones, arquitectura o referencia.
- **Propiedad por audiencia:** usuarios consultan uso y límites; operadores ejecutan runbooks; contribuidores leen convenciones y pruebas; revisores académicos consultan metodología y evidencia; mantenedores verifican arquitectura, API y estado de cada documento.
- **Código como evidencia operativa:** los documentos de runtime, recuperación y API solo se marcarán `Current` después de reconciliarse con el código activo y CodeGraph.

## Diagnóstico del estado actual

1. La coexistencia de documentación activa, líneas base manuales, experimentos y planes históricos no tiene una taxonomía visible, por lo que puede confundirse material vigente con evidencia de comparación.
2. La documentación de recuperación, runtime y API contiene señales de desfase o planes ya ejecutados; debe validarse contra el cableado ejecutable antes de declararla vigente.
3. `docs/mapa-fases-tesis.md` enlaza `docs/arquitectura.md`, una ruta inexistente, y por tanto rompe el mapa de tesis.
4. No existe una portada de navegación que dirija explícitamente a cada audiencia ni que explique estados, baselines y experimentos.
5. `docs/decisiones/api.md` es un plan de migración ya completado; debe conservarse como material `Historical`, sin moverlo durante esta iniciativa.

## Política de clasificación

Todo documento migrado debe comenzar con el siguiente bloque de metadatos visibles:

```markdown
> **Status:** `Current` | `Baseline` | `Experimental` | `Historical`
> **Audience:** <user | operator | contributor | academic-reviewer | maintainer>
> **Verified against:** <code path, command, CodeGraph query, or methodology source>
> **Last verified:** YYYY-MM-DD
> **Replacement:** <relative link or `N/A`>
```

| Estado | Uso permitido | Regla |
|---|---|---|
| `Current` | Fuente operativa o técnica vigente. | Debe coincidir con código activo, comandos y enlaces comprobados. |
| `Baseline` | Implementación o enfoque de comparación congelado. | Debe indicar explícitamente que no es el flujo recomendado. |
| `Experimental` | Hipótesis, prueba o técnica bajo evaluación. | Debe declarar alcance, evidencia y ausencia de garantía operativa. |
| `Historical` | Planes ejecutados, hitos y trazabilidad. | Se conserva para auditoría y enlaza a su reemplazo cuando exista. |

La etiqueta no borra evidencia: los snapshots académicos R1, R2 y R3, las líneas base y los resultados se archivan o etiquetan. **No se eliminará ningún archivo antes de validar la migración, enlaces y rutas de reemplazo.**

## Inventario y acción propuesta

| Ruta auditada | Estado objetivo | Acción |
|---|---|---|
| `docs/EISI_2026-04-09_14-25-36_pg1409.pdf` | `Historical` (fuente metodológica inmutable) | Conservar sin modificar ni eliminar; enlazar desde la ruta académica. |
| `AGENTS.md` (raíz) | Operativo de repositorio | Conservar en la raíz; no clasificar ni reubicar durante la migración. |
| `README.md` (raíz) | `Current` (entrada canónica) | Conservar en la raíz y actualizar como entrada breve con inicio rápido, rutas por audiencia y enlace a `docs/`, sin duplicar contenido especializado. |
| Cada `*.md` adicional en la raíz | Por clasificar | Inventariar antes de P0, asignar categoría de destino apropiada bajo `docs/`, actualizar enlaces entrantes y salientes, y proponer su reubicación para aprobación explícita. |
| `docs/guia-carpetas.md` | `Current` | Actualizar y consolidar como mapa técnico, sin duplicar la portada. |
| `docs/mapa-fases-tesis.md` | `Current` | Actualizar el enlace roto y enlazar metodología, evidencia y arquitectura vigente. |
| `docs/testing.md` | `Current` | Actualizar comandos, conteos y alcance tras reconciliar con tests existentes. |
| `docs/decisiones/api.md` | `Historical` | Etiquetar y enlazar a la documentación API vigente; no mover en esta fase. |
| `docs/architecture/chunking.md` | `Current` | Verificar y actualizar contra `pipeline/chunking/`. |
| `docs/architecture/tables.md` | `Current` | Verificar y actualizar contra `pipeline/tables/`. |
| `docs/architecture/vectorization.md` | `Current` | Verificar y actualizar contra `pipeline/vectorization/`. |
| `docs/architecture/bm25-sparse-retrieval.md` | `Current` | Verificar y actualizar contra `pipeline/sparse_indexing/`. |
| `docs/architecture/retrieval.md` | `Current` | Consolidar con la arquitectura de recuperación activa, preservando enlaces entrantes. |
| `docs/architecture/retrieval-langgraph.md` | `Current` | Reconciliar con el grafo y recuperación actualmente cableados antes de marcarlo vigente. |
| `docs/architecture/retrieval-manual.md` | `Baseline` | Etiquetar como línea base manual y enlazar a la arquitectura actual. |
| `docs/operations/corpus-build.md` | `Current` | Mantener y verificar comandos de ingestión, limpieza y chunking. |
| `docs/operations/table-processing.md` | `Current` | Mantener y verificar comandos de tablas y salidas. |
| `docs/operations/vectorization.md` | `Current` | Mantener y verificar colección, entradas y efectos sobre datos generados. |
| `docs/operations/bm25-sparse-retrieval.md` | `Current` | Mantener y verificar entradas, salida y comando del índice disperso. |
| `docs/operations/rag-langgraph.md` | `Current` | Reconciliar con runtime y API activos antes de declararlo actual. |
| `docs/operations/rag-manual.md` | `Baseline` | Etiquetar como operación de referencia manual, no como ruta recomendada. |
| `docs/experiments/chunking-strategy-comparison.md` | `Experimental` | Conservar, etiquetar y enlazar al criterio de evaluación. |
| `docs/experiments/resumen-evaluacion-semantic-chunking.md` | `Experimental` | Conservar, etiquetar y enlazar al experimento relacionado. |
| `docs/technical_documentation/retrieval/hybrid-retrieval.md` | `Experimental` | Consolidar como referencia técnica o etiquetar; validar relación con el runtime. |
| `docs/technical_documentation/retrieval/cross-encoder-reranking.md` | `Experimental` | Etiquetar y reconciliar con la ruta activa antes de promover contenido. |
| `docs/technical_documentation/retrieval/parent-document-retrieval.md` | `Experimental` | Etiquetar y reconciliar con la ruta activa antes de promover contenido. |
| `docs/technical_documentation/retrieval/R1_hybrid_retrieval_implementacion.md` | `Historical` | Archivar/etiquetar como snapshot R1; no eliminar. |
| `docs/technical_documentation/retrieval/R2_hybrid_reranking_implementacion.md` | `Historical` | Archivar/etiquetar como snapshot R2; no eliminar. |
| `docs/technical_documentation/retrieval/R3_hybrid_reranking_parent_implementacion.md` | `Historical` | Archivar/etiquetar como snapshot R3; no eliminar. |
| `docs/technical_documentation/query_understanding/query-rewriting.md` | `Experimental` | Etiquetar y validar si está cableado en el runtime. |
| `docs/technical_documentation/query_understanding/query-expansion.md` | `Experimental` | Etiquetar y validar si está cableado en el runtime. |
| `docs/technical_documentation/query_understanding/multi-query-rrf.md` | `Experimental` | Etiquetar y validar si está cableado en el runtime. |
| `docs/technical_documentation/business_context/business_context.md` | `Experimental` | Etiquetar y validar si está cableado en el runtime. |
| `docs/technical_documentation/business_context/contexto_empresarial_tres_tecnicas.md` | `Experimental` | Conservar como comparación y etiquetar. |
| `docs/technical_documentation/business_context/Retrieval-Based Long-Term Memory.md` | `Experimental` | Etiquetar y validar si está cableado en el runtime. |
| `docs/technical_documentation/business_context/Summarization-Based Conversational Memory.md` | `Experimental` | Etiquetar y validar si está cableado en el runtime. |
| `docs/technical_documentation/business_context/full_conversation_memory.md` | `Experimental` | Etiquetar y validar si está cableado en el runtime. |
| `docs/technical_documentation/validation/retrieval-relevance-grading.md` | `Experimental` | Etiquetar y reconciliar con validaciones activas. |
| `docs/technical_documentation/validation/sufficient-context-gate.md` | `Experimental` | Etiquetar y reconciliar con validaciones activas. |
| `docs/technical_documentation/validation/self-refine.md` | `Experimental` | Etiquetar y reconciliar con validaciones activas. |

## Arquitectura de información objetivo

```text
README.md                                  # entrada canónica: descripción, inicio rápido y rutas por audiencia
AGENTS.md                                  # instrucciones operativas del repositorio
docs/                                      # documentación detallada enlazada desde la raíz
├── getting-started.md                     # inicio rápido local y límites
├── guia-carpetas.md                       # mapa técnico del repositorio
├── mapa-fases-tesis.md                    # trazabilidad metodología ↔ repositorio
├── EISI_2026-04-09_14-25-36_pg1409.pdf    # fuente metodológica inmutable
├── architecture/                          # contratos y diseño Current
├── operations/                            # runbooks Current
├── reference/                             # contratos, ejemplos y API verificados
├── experiments/                           # evidencia Experimental
├── baselines/                             # referencias Baseline
├── historical/                            # planes e hitos Historical
└── technical_documentation/               # transición: clasificar antes de mover
```

La estructura es objetivo de migración, no una instrucción de crear carpetas o mover archivos todavía. No se creará `docs/README.md`: la navegación comienza en `README.md` de la raíz y continúa hacia `docs/`. Los enlaces antiguos deberán seguir funcionando mediante archivos puente o enlaces de reemplazo hasta aprobar el corte.

## Fases ordenadas

### P0 — Inventario verificable y entrada de navegación

**Tareas por archivo**

0. Antes de ejecutar P0, generar un inventario verificable de todos los `*.md` en la raíz: retener `AGENTS.md` y `README.md`; clasificar cada archivo adicional en una categoría de destino apropiada bajo `docs/`, identificar enlaces entrantes y salientes, y someter cada reubicación a aprobación explícita.
1. Actualizar `README.md` de la raíz como entrada canónica con descripción concisa, inicio rápido, enlaces activos para las cinco audiencias y enlace a `docs/`, sin duplicar operaciones, arquitectura ni referencia detalladas.
2. Actualizar `docs/guia-carpetas.md` para que describa la entrada de la raíz y las categorías, sin prometer frontend ni despliegue cloud.
3. Actualizar `docs/mapa-fases-tesis.md` y reemplazar su enlace roto por enlaces existentes y verificados.
4. Añadir los metadatos de estado al inventario existente sin mover documentos.

**Criterios de aceptación**

- El `README.md` de la raíz ofrece una ruta identificable para las cinco audiencias y enlace a `docs/`.
- El inventario de la raíz retiene únicamente `AGENTS.md` y `README.md` como Markdown de raíz y documenta clasificación, destino, enlaces afectados y aprobación pendiente de cada otro `*.md`.
- Todos los enlaces internos del `README.md` de raíz y del mapa de tesis resuelven.
- Cada documento clasificado declara estado, audiencia, evidencia de verificación, fecha y reemplazo.

### P1 — Reconciliación de contenido vigente

**Tareas por archivo**

1. Revisar `docs/architecture/retrieval.md`, `docs/architecture/retrieval-langgraph.md` y `docs/operations/rag-langgraph.md` contra los módulos activos de `agents/consulta_normativa/langchain_rag/` y sus dependencias de recuperación.
2. Revisar `docs/testing.md` contra suites y comandos realmente disponibles.
3. Revisar `docs/architecture/{chunking,tables,vectorization,bm25-sparse-retrieval}.md` y `docs/operations/{corpus-build,table-processing,vectorization,bm25-sparse-retrieval}.md` contra los entrypoints del pipeline.
4. Crear la referencia API únicamente desde rutas FastAPI activas; mantener `docs/decisiones/api.md` como plan `Historical` completado.

**Criterios de aceptación**

- Ningún documento de runtime, recuperación o API se marca `Current` sin reconciliación explícita con código y CodeGraph.
- Cada comando documentado se ejecuta o se marca con prerrequisito/limitación verificable.
- Los documentos consolidados conservan sus URL antiguas mediante archivo puente, redirección de enlace o sección de reemplazo.

### P2 — Consolidación segura de baselines, experimentos e historia

**Tareas por archivo**

1. Etiquetar `docs/operations/rag-manual.md` y `docs/architecture/retrieval-manual.md` como `Baseline`.
2. Etiquetar los documentos de `docs/technical_documentation/` y `docs/experiments/` según evidencia comprobada; preservar R1, R2 y R3 como `Historical`.
3. Proponer, revisar y solo después ejecutar movimientos hacia `baselines/`, `experiments/` e `historical/`; para cada reubicación aprobada, usar `git mv` a fin de preservar el historial cuando Git pueda detectarlo.
4. Mantener el PDF metodológico en su ubicación y con enlace estable.

**Criterios de aceptación**

- No se pierde evidencia académica, snapshot R1/R2/R3 ni línea base.
- Todo traslado tiene enlace de reemplazo, verificación de enlaces entrantes y rollback documentado.
- No se elimina ningún archivo como consecuencia de esta fase.

**Seguridad, preservación de enlaces y rollback**

- Migrar en lotes pequeños y comprobar enlaces antes y después de cada lote.
- Inventariar los enlaces entrantes y salientes antes de cada reubicación, actualizar ambos extremos en el mismo cambio aprobado y verificar que no queden enlaces rotos.
- Usar `git mv` para cada movimiento aprobado y revisar la detección de renombrado para preservar el historial de Git.
- Requerir aprobación explícita para cada reubicación individual o lote con rutas enumeradas, incluidos los Markdown adicionales de la raíz.
- Dejar un archivo puente en la ruta anterior o actualizar todos los enlaces entrantes en el mismo cambio aprobado.
- Si falla un enlace, un comando o la reconciliación con código, restaurar el documento a su ruta y estado previos; no borrar artefactos para corregir la inconsistencia.
- No crear registros nuevos bajo `docs/decisiones/` salvo petición explícita.

## Rutas de navegación por audiencia

| Audiencia | Ruta propuesta |
|---|---|
| Usuario | `README.md` (raíz) → descripción breve → `docs/` → límites y ejemplos verificados. |
| Operador local | `README.md` (raíz) → `docs/getting-started.md` → `docs/operations/`. |
| Contribuidor | `README.md` (raíz) → `docs/guia-carpetas.md` → `docs/testing.md` → arquitectura pertinente. |
| Revisor académico | `docs/mapa-fases-tesis.md` → PDF metodológico inmutable → `docs/experiments/` y snapshots R1/R2/R3. |
| Mantenedor | `README.md` (raíz) → `docs/architecture/` → referencia API → runbooks y política de estados. |

## Lista de validación

- [ ] Verificar enlaces Markdown internos, anclas y enlaces de reemplazo desde las rutas antiguas.
- [ ] Antes de P0, inventariar todos los `*.md` de la raíz: conservar `AGENTS.md` y `README.md`; clasificar, enlazar y obtener aprobación para reubicar cada archivo adicional.
- [ ] Confirmar que `README.md` de la raíz contiene descripción concisa, inicio rápido, enlaces activos por audiencia y enlace a `docs/`, sin duplicar contenido detallado.
- [ ] Confirmar la ausencia de propuesta para `docs/README.md`.
- [ ] Ejecutar o validar los comandos documentados con prerrequisitos explícitos y sin alterar datos no relacionados.
- [ ] Reconciliar runtime, recuperación y API con código activo y consultas CodeGraph antes de asignar `Current`.
- [ ] Confirmar que la terminología distingue implementación actual, baseline, experimento e histórico.
- [ ] Revisar que cada documento tenga el bloque de estado, audiencia, evidencia, fecha y reemplazo.
- [ ] Realizar un recorrido por las cinco rutas de audiencia y comprobar que cada una alcanza su objetivo sin asumir frontend ni cloud deployment.
- [ ] Confirmar que el PDF metodológico, la evidencia académica y R1/R2/R3 permanecen preservados.

## Definición de terminado y decisiones que requieren aprobación

La migración estará terminada cuando `README.md` de la raíz funcione como entrada canónica navegable, el mapa de tesis no tenga enlaces rotos, los documentos `Current` estén reconciliados con código, los demás tengan estado y reemplazo explícitos, y todos los enlaces internos y rutas de audiencia estén validados.

Antes de cualquier movimiento, archivo físico o eliminación, se requiere aprobación explícita del usuario para:

1. La estructura final de directorios objetivo y cada lote de rutas a mover.
2. Cada reubicación de Markdown adicional de la raíz, con su categoría de destino y plan de actualización de enlaces.
3. La clasificación final de documentos ambiguos entre `Current` y `Experimental`.
4. La consolidación de documentos que puedan tener lectores o enlaces externos.
5. Cualquier eliminación propuesta después de la validación de migración; la expectativa por defecto es conservar mediante archivo o etiqueta.
6. Cualquier nuevo registro bajo `docs/decisiones/`.
