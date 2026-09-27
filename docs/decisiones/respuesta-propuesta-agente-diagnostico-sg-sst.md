# Respuesta técnica a la propuesta del agente de diagnóstico SG-SST

### Alcance y perfil mínimo

El inicio debe solicitar: número de trabajadores, clase de riesgo, actividad económica/CIIU cuando esté disponible, e identidad y versión de la evaluación. La clase de riesgo I debe validarse de forma explícita; no se codificará silenciosamente como valor fijo. Si la clase es distinta de I, contradictoria o no puede validarse, el sistema detiene el cálculo, marca la evaluación fuera de alcance o pendiente de revisión y remite a un profesional SST. No debe adaptar una matriz riesgo I a otro universo.

### Interacción finita y validada

Después del perfil se ejecuta un plan fijo mínimo. Solo se preguntará de forma adaptativa cuando una regla determinística detecte evidencia faltante, inválida o contradictoria. No habrá mínimos arbitrarios de caracteres: cada respuesta tendrá tipo, dominio permitido, obligatoriedad y validación por campo; los errores producirán una aclaración dirigida.

Se permiten como máximo **15 preguntas abiertas por sesión**; las preguntas factuales cortas y respuestas controladas no cuentan. El flujo se detiene al completar el plan, alcanzar el límite, repetir una aclaración sin resolver, detectar contradicción material o requerir juicio profesional. En esos casos conserva el avance y pasa a `INSUFFICIENT_INFORMATION` o revisión humana, sin seguir interrogando.

### Estados y puntuación

| Estado interno | Significado | Política obligatoria |
|---|---|---|
| `COMPLIANT_DECLARED` | La declaración satisface la regla aplicable. | Puntuar únicamente según la matriz aprobada; no equivale a cumplimiento verificado. |
| `NON_COMPLIANT_DECLARED` | La declaración no satisface la regla aplicable. | Aplicar el efecto exacto definido por la matriz y emitir la recomendación curada. |
| `INSUFFICIENT_INFORMATION` | Falta información válida o persiste una contradicción. | Nunca convertirlo en cumplimiento. La matriz debe definir de forma explícita y aprobada su efecto en puntaje, total y reporte. |
| `NOT_APPLICABLE` | Una regla aprobada y un motivo permitido excluyen el requisito. | Registrar regla y motivo; la matriz debe definir de forma explícita y aprobada el tratamiento de peso/denominador. |
| `HUMAN_REVIEW_REQUIRED` | El caso requiere criterio profesional o queda fuera del alcance automatizado. | Bloquear el resultado final hasta revisión. |

No se codificará una regla numérica para `INSUFFICIENT_INFORMATION` o `NOT_APPLICABLE` por inferencia del equipo. La política exacta debe provenir de la fuente aplicable y quedar validada por el experto SST antes de escribir el motor.

### Resultado y formato

Con declaraciones sin documentos ni verificación independiente, el sistema no puede afirmar cumplimiento ni calcular/presentar un resultado oficial de reporte. La salida será una **autoevaluación orientativa basada en declaraciones**, con criterio aplicado, estado interno, cálculo reproducible cuando esté autorizado, fuentes, versiones, limitaciones y pendientes de revisión.

Antes de reproducir un formato, rangos o umbrales, el equipo debe aportar la referencia oficial exacta que los establece. La plantilla final del informe y la matriz requieren aprobación expresa del codirector y del experto SST. El PDF solo se genera después de una compuerta de revisión humana.

### Orden de implementación

1. Validar fuentes y aprobar la matriz/catálogo versionado.
2. Implementar y probar aplicabilidad, estados, puntuación y recomendaciones determinísticas.
3. Definir esquemas tipados, plan de preguntas, límites y casos dorados.
4. Implementar persistencia durable, auditoría, reanudación e idempotencia.
5. Integrar el RAG únicamente como evidencia y explicación.
6. Construir la orquestación LangGraph y las interfaces.
7. Aprobar la plantilla, añadir revisión humana y, al final, generar el PDF.

## Fuentes y validación

- **Verificado en el proyecto:** el runtime actual reutilizable implementa retrieval híbrido Chroma/BM25 con RRF y memoria/checkpoint en proceso; `agents/diagnostico_cumplimiento/` continúa como andamiaje sin dominio implementado.
- **Fuentes oficiales propuestas:** [Resolución 0312 de 2019](https://www.mintrabajo.gov.co/documents/20147/59995826/Resolucion+0312-2019-+Estandares+minimos+del+Sistema+de+la+Seguridad+y+Salud.pdf) y [Circulares generales del Ministerio del Trabajo — referencia propuesta para Circular 0027](https://www.mintrabajo.gov.co/normatividad/circulares-generales). Deben confrontarse con copias oficiales identificadas por fecha, versión e integridad antes de transcribir reglas. El contenido de la Circular 0027 **no fue verificado independientemente en esta revisión** y toda interpretación requiere validación del experto SST.

## Preguntas decisivas para el proponente

1. ¿Cuál es la referencia oficial exacta —acto, fecha, anexo, página y URL directa— que autoriza el formato del informe y cada umbral de puntuación propuesto?
2. ¿Qué fuente y procedimiento verificable determinarán la clase de riesgo y el CIIU de la empresa?

## Arquitectura propuesta

```text
CLI/API → Servicio de evaluación → Plan de preguntas → Motor determinístico
                         │                  │                 │
                         └── Estado durable/auditoría         ├── Matriz y recomendaciones versionadas
                                                            └── Puerto de evidencia → RAG existente
Resultado estructurado → Revisión humana → Compositor → PDF orientativo
```

| Componente | Responsabilidad |
|---|---|
| Matriz y catálogos | Mantener requisitos, aplicabilidad, estados, cálculo, preguntas, motivos y acciones aprobados. |
| Motor determinístico | Evaluar entradas tipadas de forma reproducible, sin LLM ni retrieval. |
| Plan de preguntas | Seleccionar solo faltantes justificables y aplicar límites/paradas. |
| Estado y auditoría | Reanudar por `evaluation_id`/`thread_id`, versionar, migrar y registrar eventos idempotentes. |
| Puerto de evidencia | Obtener citas y trazas del RAG sin influir en la decisión. |
| Orquestador LangGraph | Coordinar pasos y pausas; no contener reglas legales. |
| Revisión y reporte | Aprobar el cierre y renderizar resultados estructurados sin reinterpretarlos. |
