# Referencia de la API

> **Status:** `Current`
> **Audience:** user, maintainer
> **Verified against:** `agents/api/main.py`, `agents/consulta_normativa/api/{routes,schemas,service}.py`, `agents/diagnostico_cumplimiento/api/{routes,schemas,service}.py`
> **Last verified:** 2026-10-18
> **Replacement:** N/A

Una sola aplicación FastAPI (`agents.api.main:app`) expone ambos agentes bajo la misma URL base. Este documento describe únicamente las rutas activas. Para levantar el servicio, consulta [getting-started.md](../getting-started.md).

**Convenciones.** Cuerpos y respuestas en JSON salvo el informe PDF. Los errores siguen el formato de FastAPI `{"detail": ...}`; la validación de esquema devuelve `422`. CORS solo admite los orígenes de `CORS_ALLOWED_ORIGINS`. No hay autenticación.

## Salud

| Método y ruta | Respuesta | Códigos |
|---|---|---|
| `GET /health` | `{"status": "ok"}` | `200`. Solo confirma que el proceso HTTP responde (sonda de vida). |
| `GET /health/ready` | `{"status": "ready"}` | `200` cuando ambos servicios se inicializaron; `503` `{"detail": "Service unavailable."}` mientras arranca o si falta uno (sonda de disponibilidad). No consulta índices ni DeepSeek. |

## Consulta normativa

### `POST /api/v1/query`

| Campo de entrada | Tipo | Regla |
|---|---|---|
| `question` | `str` | Obligatorio; se recortan espacios; vacío → `422`. |
| `conversation_id` | `str \| null` | Opcional; si falta se genera un UUID4. Reutilízalo para continuar la conversación. |

Respuesta `200`:

| Campo | Tipo |
|---|---|
| `answer` | `str` |
| `references` | `list[str]` |
| `chunks` | `list[str]` |
| `conversation_id` | `str` |

Errores: `503` `"The normative consultation service is temporarily unavailable."` ante cualquier fallo del servicio; `500` si el servicio no se inicializó.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"¿Qué es el SG-SST?"}'
```

## Diagnóstico de cumplimiento

Flujo: crear → responder preguntas hasta que `next_question` sea `null` → completar → descargar informe. Las sesiones viven en memoria del proceso: se pierden al reiniciar y **se eliminan después de descargar el informe**.

### `POST /api/v1/diagnostics` → `201`

| Campo de entrada | Tipo | Regla |
|---|---|---|
| `worker_count` | `int` | Obligatorio, mayor que 0. |
| `company_name` | `str \| null` | Opcional. |

La clase de riesgo es siempre I; no se acepta como parámetro. Respuesta: `diagnosis_id`, `catalog_id`, `catalog_name`, `progress`, `next_question`. Errores: `400` si no hay catálogo aplicable o el valor es inválido; `503`.

### `POST /api/v1/diagnostics/{diagnosis_id}/answers` → `200`

| Campo de entrada | Tipo | Regla |
|---|---|---|
| `requirement_id` | `str` | Obligatorio; debe coincidir con la pregunta actual. |
| `question_id` | `str` | Obligatorio; debe coincidir con la pregunta actual. |
| `answer` | `bool \| str` | Obligatorio; texto vacío → `422`. |

Respuesta: `diagnosis_id`, `progress`, `next_question`, `interpretation_status`, `clarification_message`. Errores: `404` `"Diagnostic session not found."`; `409` si no hay preguntas pendientes, la respuesta no corresponde a la pregunta actual, ya fue respondida o no pudo interpretarse; `503`.

### `POST /api/v1/diagnostics/{diagnosis_id}/complete` → `200`

Respuesta: `diagnosis_id`, `assessments` (lista de `requirement_id`, `requirement_name`, `applicability_status`, `assessment_status`, `explanation`, `missing_information`), `summary` (`total_requirements`, `complies_as_declared`, `does_not_comply_as_declared`, `insufficient_information`, `not_applicable`) y `scope_note`. Errores: `404`; `409` `"The diagnostic still has pending questions."`; `503`.

### `GET /api/v1/diagnostics/{diagnosis_id}/report` → `200 application/pdf`

Devuelve el PDF con `Content-Disposition: inline; filename="diagnostico_sgsst.pdf"` y `Cache-Control: private, no-store, max-age=0`. Tras una descarga exitosa la sesión se elimina; una segunda solicitud devuelve `404`. Errores: `404`; `409` si quedan preguntas pendientes; `503` `"The diagnostic report is temporarily unavailable."`.

### Modelos anidados

| Modelo | Campos |
|---|---|
| `progress` | `completed_requirements`, `total_requirements`, `current_requirement_number`, `current_requirement_id`, `completed` |
| `next_question` | `requirement_id`, `requirement_name`, `question_id`, `text`, `role`, `question_type`, `requirement_number`, `total_requirements` |

## Historial

El plan que unificó ambas APIs en un solo proceso se conserva en [decisiones/api.md](../decisiones/api.md) (`Historical`).
