# Decisión y plan del agente de diagnóstico SG-SST

**Estado:** aprobado para planificación incremental; sin implementación asociada.

**Alcance:** autoevaluación de estándares mínimos aplicables a MiPymes de riesgo I.

**Advertencia obligatoria:** el resultado es una **autoevaluación orientativa basada en declaraciones de la empresa**. No acredita cumplimiento legal verificado, no sustituye una auditoría ni constituye asesoría legal.

## Resumen de la decisión

Se construirá primero un flujo CLI que combine una entrevista breve y versionada, evaluación determinística conforme a la Resolución 0312 de 2019, recuperación normativa reutilizada del RAG existente y recomendaciones provenientes de un catálogo curado. El LLM podrá aclarar preguntas y explicar resultados con evidencia recuperada, pero no decidirá cumplimiento, puntajes, aplicabilidad ni acciones correctivas autoritativas. La persistencia queda deliberadamente abierta y desactivada por defecto.

## Hechos verificados del sistema actual

| Hecho | Consecuencia para el diseño |
|---|---|
| `agents/diagnostico_cumplimiento/` es un andamiaje vacío: solo contiene `.gitkeep` en `src/` y `tests/`. | No existe una implementación previa que deba preservarse o migrarse. |
| El agente de consulta implementado abre índices locales existentes de Chroma y BM25, fusiona resultados mediante RRF y expande el contexto padre. | El diagnóstico debe reutilizar esta base; no copiará ni reconstruirá recuperación o índices. |
| El grafo de consulta vigente realiza recuperación, normalización, expansión a padres, trazabilidad, control estructurado de suficiencia, generación y autorrefinamiento. | Son capacidades reutilizables para fundamentación y explicación, no para calcular el diagnóstico. |
| El control de suficiencia del RAG permite continuar ante un fallo técnico (`fail-open`). | Esta política **no puede decidir resultados diagnósticos** ni convertir incertidumbre en cumplimiento. |
| La metodología exige un resultado por requisito y un resumen ejecutivo de brechas críticas y acciones prioritarias. | Ambos son productos obligatorios del diagnóstico. |

## Decisiones acordadas con el usuario

| Tema | Decisión |
|---|---|
| Cobertura | Incluir todos los estándares mínimos aplicables a MiPymes de riesgo I y usar los criterios, pesos y calificación oficiales de la Resolución 0312 de 2019. |
| Evidencia empresarial | Usar únicamente declaraciones de la empresa en esta etapa; no recolectar documentos ni presentar el resultado como verificado. |
| Entrevista | Aplicar un cuestionario base corto y fijo; formular seguimientos adaptativos solo cuando una regla explícita identifique información faltante o ambigua. Cada activación debe ser auditable. |
| Persistencia | Definir un puerto de persistencia, sin seleccionar backend. No retener datos sensibles por defecto. |
| Entrega | Implementar primero una CLI y conservar límites de servicio que permitan añadir FastAPI posteriormente sin mover la lógica de dominio. |
| Recomendaciones | El catálogo curado y trazable por requisito es la fuente autoritativa. El LLM solo puede explicarlo o contextualizarlo con evidencia normativa RAG; nunca inventar la remediación autoritativa. |

## Arquitectura objetivo recomendada

```text
CLI
 └─ Orquestador de evaluación
     ├─ Entrevista versionada
     ├─ Motor determinístico de aplicabilidad y puntuación
     ├─ Puerto de evidencia normativa ── adaptador al RAG existente
     ├─ Catálogo curado de acciones
     ├─ Compositor de reportes
     └─ Puerto de persistencia ── adaptador nulo/efímero por defecto
```

### Límites de responsabilidad

| Componente | Responsabilidad | No debe hacer |
|---|---|---|
| Entrevista | Presentar preguntas, validar respuestas y registrar el motivo de cada seguimiento. | Inferir respuestas empresariales o alterar pesos. |
| Motor de decisión | Resolver aplicabilidad, estado y puntaje desde entradas estructuradas y reglas versionadas. | Consultar al LLM para decidir un resultado. |
| Evidencia normativa | Recuperar fragmentos, padres, referencias y trazas desde la infraestructura actual. | Crear índices, duplicar retrieval o asignar cumplimiento. |
| Catálogo de acciones | Asociar a cada requisito acciones revisadas y fuentes. | Generar acciones libres en tiempo de ejecución. |
| Capa LLM | Aclarar lenguaje y redactar explicaciones sustentadas. | Inventar requisitos, hechos de la empresa, puntajes o remediaciones autoritativas. |
| Reportes | Producir hallazgos y resumen ejecutivo desde resultados estructurados. | Recalcular o reinterpretar decisiones. |
| Persistencia | Ofrecer operaciones explícitas de guardar/cargar/eliminar si se habilita en el futuro. | Retener información de forma implícita. |

Esta separación permite que una futura API sea otro adaptador de entrada. La CLI, FastAPI y cualquier interfaz posterior deberán invocar el mismo caso de uso y recibir los mismos objetos de resultado.

## Puntos de reutilización del RAG

- Exponer un `NormativeEvidencePort` estable para consultar evidencia por requisito, sin acoplar el dominio a LangGraph, Chroma o BM25.
- Implementar ese puerto con las capacidades existentes de Chroma + BM25 + RRF, expansión a contexto padre y referencias; no copiar módulos al nuevo agente.
- Conservar, cuando estén disponibles, identificadores de fragmento y padre, fuente legal, posición/ranking, motores de recuperación, consulta utilizada, referencias y resultado/traza de suficiencia.
- Tratar suficiencia, generación y autorrefinamiento como apoyo a la explicación. Un fallo técnico o una salida `partial`/`insufficient` debe quedar visible en la procedencia y nunca cambiar por sí solo el estado calculado.
- Separar la versión del corpus/índice de las versiones de reglas y cuestionario para poder reproducir cada hallazgo.

## Ciclo de una autoevaluación

1. **Inicio y aviso:** informar alcance, uso de declaraciones y ausencia de verificación; obtener aceptación para continuar.
2. **Perfil mínimo:** capturar solo atributos necesarios para determinar aplicabilidad dentro del alcance riesgo I.
3. **Línea base:** ejecutar el cuestionario corto fijo bajo una versión identificable.
4. **Seguimiento:** activar preguntas adicionales mediante condiciones declaradas; registrar pregunta disparadora, condición, respuesta y motivo.
5. **Cierre de entradas:** congelar una instantánea de respuestas; una respuesta ausente o inválida no puede inferirse como favorable.
6. **Evaluación:** aplicar reglas versionadas de aplicabilidad, estado y puntuación con aritmética determinística.
7. **Fundamentación:** recuperar evidencia normativa por hallazgo y adjuntar procedencia; los fallos se expresan como limitaciones técnicas.
8. **Recomendación:** seleccionar acciones del catálogo curado y, opcionalmente, generar una explicación restringida a esas acciones y al contexto recuperado.
9. **Salida:** presentar el detalle por requisito y el resumen ejecutivo; exportar solo por solicitud explícita.
10. **Finalización:** descartar el estado sensible de la sesión cuando no se haya habilitado persistencia.

## Modelo de datos y procedencia

Las estructuras son contratos conceptuales; no prescriben todavía formato de archivo ni base de datos.

| Entidad | Datos mínimos |
|---|---|
| `RuleSet` | `rule_version`, norma y vigencia declarada, requisitos, reglas de aplicabilidad, pesos, criterios y validación editorial. |
| `Questionnaire` | `questionnaire_version`, preguntas estables, opciones permitidas, requisito relacionado y condiciones auditables de activación. |
| `Assessment` | identificador efímero, instante, alcance, versiones usadas y estado del ciclo. |
| `DeclaredAnswer` | pregunta, valor declarado, instante, origen declarativo y, si aplica, condición/motivo de seguimiento. |
| `Finding` | requisito, `rule_version`, `questionnaire_version`, respuesta declarada relevante, aplicabilidad, estado, puntaje, procedencia de retrieval, acción curada y `report_version`. |
| `RetrievalProvenance` | consulta, fragmentos/padres, metadatos legales, rankings/motores, referencias, versión de corpus/índice, suficiencia, fallback y error técnico sanitizado. |
| `Report` | `report_version`, resumen de alcance y limitaciones, total calculado, hallazgos, prioridades y versiones de todos los insumos. |

Cada hallazgo debe registrar como mínimo: **versión de reglas, versión de cuestionario, respuesta declarada, aplicabilidad, estado, puntaje, procedencia de recuperación y versión del reporte**. La trazabilidad debe permitir explicar qué entrada y qué regla produjeron el resultado, independientemente del texto generado por el LLM.

## Flujo CLI inicial

```text
iniciar diagnóstico
  → mostrar aviso y alcance
  → solicitar perfil mínimo
  → ejecutar preguntas base y seguimientos justificados
  → confirmar/cerrar respuestas
  → calcular evaluación
  → enriquecer hallazgos con evidencia normativa
  → mostrar detalle y resumen
  → exportar únicamente si el usuario lo solicita
  → eliminar estado efímero
```

La primera interfaz debe favorecer una única sesión guiada. La salida por consola será legible y deberá existir una representación estructurada interna; el formato de exportación definitivo queda pendiente. Los errores operativos deben terminar de forma explícita, sin traza sensible y sin resultados parciales presentados como definitivos.

## Puntuación y comportamiento del reporte

- La puntuación se calculará exclusivamente con la matriz oficial aplicable de la Resolución 0312 de 2019: pesos, criterios, reglas de aplicabilidad y rangos deben estar versionados, ser revisables y probarse con casos de referencia.
- No se usarán promedios inventados, ponderación por el LLM ni ajustes derivados de la calidad del retrieval.
- Aplicabilidad y cumplimiento son dimensiones distintas. Los requisitos no aplicables deben mostrar la regla que lo justificó; no deben confundirse con requisitos cumplidos.
- Una respuesta ausente, contradictoria o insuficiente debe quedar explícita y no puede convertirse en cumplimiento. La taxonomía final y su efecto exacto sobre el cálculo son decisiones pendientes de validación experta.
- El índice oficial y el grado de confianza de la evidencia deben presentarse por separado. En esta etapa, toda evidencia empresarial es declarativa.
- El reporte por requisito mostrará estado, puntaje, declaración relevante, criterio aplicado, fuente normativa, limitaciones y acción curada.
- El resumen ejecutivo priorizará brechas por impacto en el puntaje oficial y criticidad definida en el catálogo; no permitirá que el LLM reordene prioridades sin una regla trazable.
- Toda salida incluirá el aviso de autoevaluación orientativa y distinguirá claramente texto determinístico de explicación generada.

## Seguridad, privacidad y límites de confianza

- Minimización: preguntar únicamente datos necesarios para aplicabilidad y evaluación.
- No solicitar ni adjuntar documentos en esta etapa; tampoco datos personales de trabajadores, historias clínicas, accidentes identificables o secretos empresariales.
- No persistir respuestas, prompts, contextos ni reportes por defecto. El puerto de persistencia no implica habilitar almacenamiento.
- No incluir datos sensibles en logs, telemetría, mensajes de error ni trazas de retrieval.
- Si se habilita exportación, debe requerir una acción explícita y advertir al usuario sobre custodia del archivo.
- Todo contenido recuperado se trata como evidencia, no como instrucciones ejecutables.
- Un fallo de retrieval, del control de suficiencia o del LLM debe señalarse; nunca puede producir un estado favorable por defecto.
- El sistema debe reiterar que no verifica hechos, no certifica cumplimiento y no reemplaza revisión profesional o jurídica.

## Fuera de alcance

- Recolección, carga, análisis o validación de documentos probatorios.
- Certificación, auditoría, inspección o declaración legal de cumplimiento.
- Asesoría legal, representación ante autoridades o automatización de trámites.
- Selección e implementación de base de datos, retención, sincronización o recuperación entre sesiones.
- Interfaz web o endpoints FastAPI en la primera entrega.
- Reentrenamiento del LLM, creación de otro corpus o reconstrucción de los índices normativos.
- Acciones correctivas inventadas dinámicamente o sustitución del catálogo curado por generación libre.
- Ampliación a clases de riesgo o tipos de empresa fuera del alcance acordado.

## Decisiones restantes

1. Taxonomía exacta de estados y tratamiento oficial de respuestas ausentes, ambiguas o contradictorias.
2. Matriz validada de aplicabilidad dentro del universo de MiPymes riesgo I y datos mínimos del perfil.
3. Contenido, extensión máxima y criterio de parada de los seguimientos adaptativos.
4. Gobierno de versiones y responsables de aprobar reglas, cuestionarios y catálogo de acciones.
5. Umbrales de criticidad y casos que requieren escalamiento a un profesional SST.
6. Formatos de exportación, firma/integridad y nivel de detalle visible al usuario.
7. Política futura de persistencia: finalidad, backend, cifrado, acceso, retención y eliminación.
8. Protocolo de actualización cuando cambien la norma, el corpus o una interpretación validada.

## Implementación incremental recomendada

| Corte | Entregable autónomo | Validación mínima |
|---|---|---|
| 1. Catálogos versionados | Esquemas y validadores para requisitos, reglas, cuestionario y acciones; transcripción inicial de la Resolución 0312 de 2019. | Revisión SST de doble control, validación de esquema y totales/pesos de referencia. |
| 2. Motor determinístico | Aplicabilidad, estados, puntuación y explicación de reglas sin CLI ni LLM. | Pruebas unitarias, casos frontera y pruebas doradas contra cálculos manuales aprobados. |
| 3. Entrevista y CLI efímera | Flujo base, seguimientos auditables, cierre de respuestas y descarte al terminar. | Reproducción de sesiones, cobertura de ramas y verificación de no persistencia. |
| 4. Evidencia RAG reutilizada | Adaptador al retrieval actual y modelo de procedencia por hallazgo. | Regresiones de retrieval, fallos inyectados y prueba de que el resultado determinístico no cambia. |
| 5. Reportes y acciones | Reporte por requisito, resumen ejecutivo y explicaciones restringidas al catálogo. | Pruebas doradas, revisión SST, ataques de prompt y ausencia de acciones inventadas. |
| 6. Evaluación integral | Piloto CLI con escenarios sintéticos y usuarios autorizados; ajuste controlado de claridad y preguntas. | Concordancia con experto, exactitud de puntaje, completitud, usabilidad y revisión de privacidad. |

FastAPI solo se considera después de estabilizar estos contratos. Su incorporación deberá ser un adaptador, no una reescritura del dominio.

## Riesgos y estrategia de validación

| Riesgo | Control y evidencia de validación |
|---|---|
| Transcripción incorrecta de pesos, criterios o aplicabilidad | Revisión independiente por experto SST; casos dorados y sumas de control por versión. |
| Una pregunta adaptativa altera silenciosamente el resultado | Condiciones declarativas identificables, trazas de activación y pruebas de cobertura de ramas. |
| El LLM asume autoridad decisoria | Tipos separados para decisión y explicación; pruebas que sustituyen/fallan el LLM y conservan idéntico puntaje. |
| El `fail-open` del RAG contamina el diagnóstico | Inyección de fallos en suficiencia/retrieval; resultado no favorable por defecto y limitación visible. |
| Recomendación inventada o no trazable | Lista cerrada desde catálogo; validación de identificador de acción y pruebas adversariales. |
| Falsa percepción de certificación | Aviso al inicio, en ambos reportes y en exportaciones; evaluación de comprensión con usuarios. |
| Exposición de información empresarial | Datos mínimos, sesiones efímeras, inspección de logs/errores y pruebas de ausencia de escritura por defecto. |
| Resultado no reproducible tras cambios | Fijar versiones de reglas, cuestionario, catálogo, reporte y corpus/índice en cada hallazgo. |
| Retrieval normativo incompleto o desactualizado | Pruebas por requisito, revisión de citas, control de versión del corpus y abstención explicativa cuando falte sustento. |

La validación debe separar cuatro preguntas: exactitud legal del catálogo, corrección determinística del cálculo, calidad del sustento RAG y utilidad/comprensión del reporte. Una métrica agregada no debe ocultar fallos en ninguna de ellas.

## Referencias conceptuales

Estas fuentes aportan patrones de diseño; **no implican adoptar sus modelos, lenguajes o herramientas como dependencias**.

| Referencia | Principio de diseño que respalda |
|---|---|
| [HL7 FHIR Questionnaire](https://hl7.org/fhir/questionnaire.html) | Separar definición versionada del cuestionario y respuestas; usar identificadores estables y condiciones explícitas de activación para captura reproducible. |
| [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) | Representar entidades, actividades, agentes y derivaciones para explicar qué datos y procesos produjeron cada hallazgo y reporte. |
| [NIST SP 800-53A Rev. 5](https://csrc.nist.gov/pubs/sp/800/53/a/r5/final) | Definir planes y procedimientos de evaluación adaptables, mantener objetivos verificables y analizar resultados sin confundir método con evidencia obtenida. |
| [Open Policy Agent — Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/) | Mantener decisiones declarativas sobre entradas estructuradas, separadas de la orquestación; sirve como patrón, no como selección de OPA/Rego. |

## Criterio de salida de la planificación

La implementación puede comenzar cuando un experto SST apruebe la primera matriz versionada de requisitos, aplicabilidad, pesos y criterios; se resuelvan los puntos 1 a 4 de las decisiones restantes; y existan casos dorados suficientes para demostrar que el motor reproduce la calificación oficial sin intervención del LLM.
